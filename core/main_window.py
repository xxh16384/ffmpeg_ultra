import os,tempfile
import re
from PySide6.QtWidgets import (QMainWindow, QFileDialog, QMessageBox, QProgressDialog, QMenu)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QCloseEvent, QIcon, QAction
from PySide6.QtCore import Qt

from core.utils import get_ext_path, get_mapped_bitrate, get_reverse_mapped_slider_val,read_yaml_config
from core.worker import FFmpegWorker
from core.engine import get_video_duration, probe_video_info,build_ffmpeg_args,check_single_encoder
from ui.ui_main_window import Ui_MainWindow
import ui.resources_rc
import urllib.request
from core.__version__ import __title__, __version__
from PySide6.QtWidgets import QLineEdit, QFormLayout

class FFmpegGUI(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        # ==========================================
        # 1. 魔法启动：一行代码加载所有生成的界面元素
        # ==========================================
        self.setupUi(self)
        self.setWindowTitle(f"{__title__} {__version__}")
        
        self.setWindowIcon(QIcon(":/icons/icon.ico"))
        self.setAcceptDrops(True)

        # 动态植入附加参数输入框
        self.txt_extra_args = QLineEdit(self.tab_video)
        self.txt_extra_args.setPlaceholderText("例如: -preset p4 -tune hq (可选)")
        self.layout_video.insertRow(5, "附加/特性参数:", self.txt_extra_args)

        # 动态植入重新探测按钮
        from PySide6.QtWidgets import QPushButton
        self.btn_reprobe = QPushButton("重新扫描显卡硬件 🔄", self.tab_video)
        self.btn_reprobe.setToolTip("忽略本地缓存，强制重新点火测试当前环境物理显卡驱动的能力。")
        self.btn_reprobe.clicked.connect(self.reprobe_hardware_encoders)
        self.layout_video.insertRow(1, "", self.btn_reprobe)

        # 动态植入预估大小标签
        from PySide6.QtWidgets import QLabel
        self.lbl_estimated_size = QLabel("预计生成大小: 未知 (未加载视频)")
        self.lbl_estimated_size.setStyleSheet("color: #ffa500; font-weight: bold;")
        self.layout_video.insertRow(7, "体积预估:", self.lbl_estimated_size)

        # ==========================================
        # 2. 保留原有的核心初始化逻辑：硬件自检与动态预设
        # ==========================================
        self.available_v_encoders = self.probe_hardware_encoders()
        self.load_dynamic_presets()

        # 给 UI 中空白的下拉菜单动态塞入数据
        self.cb_v_encoder.addItems(self.available_v_encoders)
        self.combo_preset.addItems(list(self.preset_configs.keys()))
        self.toggle_custom_tab(self.combo_preset.currentText())
        
        # === 从外部 YAML 统一加载并注入所有悬浮提示 ===
        self.load_tooltips()

        # ==========================================
        # 4. 逐字保留：原有的所有事件绑定逻辑
        # ==========================================
        # 预设联动与模式切换
        self.combo_preset.currentTextChanged.connect(self.toggle_custom_tab)
        self.cb_v_rc.currentTextChanged.connect(self.update_slider_range)
        self.sld_v_value.valueChanged.connect(self.update_slider_label)
        self.cb_format.currentTextChanged.connect(self.change_output_extension)
        
        # 按钮绑定
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_stop.clicked.connect(self.stop_encoding)
        self.btn_start.clicked.connect(self.start_encoding)
        self.btn_input.clicked.connect(self.select_input_file)
        self.btn_output.clicked.connect(self.select_output_file)
        
        # Initialize Queue Tracking
        self.task_queue = []  # List of dicts: {'input': str, 'output': str, 'ui_state': dict, 'status': str}
        self.current_task_idx = 0
        self.is_queue_running = False

        # Init Queue UI Table (Setup headers correctly)
        self.table_queue.setColumnCount(3)
        self.table_queue.setHorizontalHeaderLabels(["源视频", "目标格式", "状态"])

        # Buttons logic
        self.btn_add_queue.clicked.connect(self.add_to_queue)
        self.btn_update_queue.clicked.connect(self.update_queue_item)
        self.btn_reset_queue.clicked.connect(self.reset_queue_item)
        self.btn_start_queue.clicked.connect(self.start_queue)
        self.btn_clear_queue.clicked.connect(self.clear_queue)
        
        
        # Table Selection & Context Menu Logic
        self.table_queue.itemSelectionChanged.connect(self.load_queue_item_to_ui)
        self.table_queue.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_queue.customContextMenuRequested.connect(self.show_queue_context_menu)

        # 初始化：手动触发一次范围设定（默认 CQP）
        self.update_slider_range("cqp")
        self.toggle_custom_tab(list(self.preset_configs.keys())[0])

        # === 绑定交互状态比对防呆逻辑 ===
        self.connect_ui_change_signals()
        self.check_queue_selection_state()

    def connect_ui_change_signals(self):
        self.cb_v_encoder.currentTextChanged.connect(self.check_queue_selection_state)
        self.cb_v_fps.currentTextChanged.connect(self.check_queue_selection_state)
        self.cb_v_res.currentTextChanged.connect(self.check_queue_selection_state)
        self.cb_v_rc.currentTextChanged.connect(self.check_queue_selection_state)
        self.sld_v_value.valueChanged.connect(self.check_queue_selection_state)
        self.cb_a_encoder.currentTextChanged.connect(self.check_queue_selection_state)
        self.cb_a_bitrate.currentTextChanged.connect(self.check_queue_selection_state)
        self.cb_a_sample.currentTextChanged.connect(self.check_queue_selection_state)
        self.txt_extra_args.textChanged.connect(self.check_queue_selection_state)
        self.txt_input.textChanged.connect(self.check_queue_selection_state)
        
    def check_queue_selection_state(self, *args):
        # 顺手更新一次预计大小
        self.update_estimated_size()
        
        has_items = len(self.task_queue) > 0
        self.btn_clear_queue.setEnabled(has_items)
        self.btn_start_queue.setEnabled(has_items and not getattr(self, 'is_queue_running', False))
        
        selected_ranges = self.table_queue.selectedRanges()
        if not selected_ranges:
            self.btn_update_queue.setEnabled(False)
            self.btn_reset_queue.setEnabled(False)
            return
            
        self.btn_reset_queue.setEnabled(True)
        
        rows = []
        for r in selected_ranges:
            rows.extend(range(r.topRow(), r.bottomRow() + 1))
            
        if not rows:
            self.btn_update_queue.setEnabled(False)
            return
            
        first_row = rows[0]
        if first_row < 0 or first_row >= len(self.task_queue):
            return
            
        task = self.task_queue[first_row]
        current_state = self.get_current_ui_state()
        
        is_modified = False
        for k, v in current_state.items():
            if str(task["ui_state"].get(k)) != str(v):
                is_modified = True
                break
                
        if len(rows) == 1:
            if self.txt_input.text().strip() != task["input"]:
                is_modified = True
                
        self.btn_update_queue.setEnabled(is_modified)

    def update_estimated_size(self):
        if hasattr(self, 'lbl_estimated_size'):
            input_path = self.txt_input.text().strip()
            if not input_path or not os.path.isfile(input_path):
                self.lbl_estimated_size.setText("预计生成大小: 未知 (未加载视频)")
                return
                
            if not hasattr(self, '_duration_cache'):
                self._duration_cache = {}
                
            if input_path not in self._duration_cache:
                try:
                    from core.engine import get_video_duration
                    self._duration_cache[input_path] = get_video_duration(input_path)
                except:
                    self._duration_cache[input_path] = 0
                    
            total_seconds = self._duration_cache[input_path]
            if total_seconds <= 0:
                self.lbl_estimated_size.setText("预计生成大小: 未知 (无法读取时长)")
                return
                
            ui_state = self.get_current_ui_state()
            rc = ui_state["rc"]
            
            audio_kbps = 0
            if "copy" not in ui_state["a_enc"] and "剥离静音" not in ui_state["a_enc"]:
                abit_str = ui_state["a_bit"].replace("k", "").strip()
                if abit_str.isdigit():
                    audio_kbps = int(abit_str)
                    
            video_kbps = 0
            if rc in ["vbr", "cbr"]:
                video_kbps = ui_state["vbr_cbr_val"]
            else:
                self.lbl_estimated_size.setText("预计生成大小: 未知 (CQP/CRF质量模式无法预估体积)")
                return
                
            total_kbps = video_kbps + audio_kbps
            size_mb = (total_kbps * 1000 / 8) * total_seconds / (1024 * 1024)
            self.lbl_estimated_size.setText(f"预估生成大小: 约 {size_mb:.1f} MB (仅供参考)")

    def dragEnterEvent(self, event):
        """物理事件 1：当有文件被拖入窗口领空时触发"""
        # 嗅探拖入的是不是本地物理文件（过滤掉纯文本等无效拖拽）
        if event.mimeData().hasUrls():
            event.accept() # 允许降落
        else:
            event.ignore() # 拒绝降落，鼠标会变成红色的禁止符号

    def dropEvent(self, event):
        """物理事件 2：当鼠标在窗口内松开，文件真实落地时触发"""
        urls = event.mimeData().urls()
        if not urls:
            return

        for url in urls:
            input_path = url.toLocalFile()
            if os.path.isfile(input_path):
                # 自动路径大脑：解析目录与文件名，生成默认输出路径
                directory, filename = os.path.split(input_path)
                name, ext = os.path.splitext(filename)
                
                if hasattr(self, 'cb_format'):
                    target_ext = self.cb_format.currentText()
                    if not target_ext.startswith('.'):
                        target_ext = f".{target_ext}"
                else:
                    target_ext = ext
                    
                output_path = os.path.join(directory, f"{name}_output{target_ext}")
                
                # Setup UI visual for text fields using the last file
                self.txt_input.setText(input_path)
                self.txt_output.setText(output_path)
                
                # Push straight to queue
                self.add_task_to_table(input_path, output_path, self.get_current_ui_state())
                
        self.lbl_status.setText(f"状态: 成功添加 {len(urls)} 个任务到队列！")
        self.txt_input.clear()
        self.txt_output.clear()

    def update_slider_range(self, mode):
        """根据选择的 RC 模式，动态调整滑块的最小值、最大值和当前值"""
        # 暂时静音信号，防止在切范围时触发多余的 label 更新导致报错
        self.sld_v_value.blockSignals(True)
        
        if mode == "cqp":
            # CQP 保持线性，0-51 越小画质越好
            self.sld_v_value.setRange(0, 51)
            self.sld_v_value.setSingleStep(1)
            self.sld_v_value.setValue(32) 
        else:
            # CBR/VBR 模式：物理滑块变成 0-100 的进度条
            self.sld_v_value.setRange(0, 100)
            self.sld_v_value.setSingleStep(1)
            # 默认给个 54 左右的位置，因为 54^3 映射出来刚好大概是 5000kbps 左右
            self.sld_v_value.setValue(56) 
            
        self.sld_v_value.blockSignals(False)
        self.update_slider_label()    
        
    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择要压制的视频", "", "视频文件 (*.mp4 *.mkv *.avi *.mov *.flv);;所有文件 (*.*)"
        )
        if file_path:
            self.txt_input.setText(file_path)
            # 自动路径大脑：解析目录与文件名，生成默认输出路径
            directory, filename = os.path.split(file_path)
            name, ext = os.path.splitext(filename)
            
            target_ext = self.cb_format.currentText()
            if not target_ext.startswith('.'):
                target_ext = f".{target_ext}"
                
            output_path = os.path.join(directory, f"{name}_output{target_ext}")
            self.txt_output.setText(output_path)

    def select_output_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存压制后的视频", self.txt_output.text(), 
            f"当前格式 (*{self.cb_format.currentText()});;所有文件 (*.*)"
        )
        if file_path:
            self.txt_output.setText(file_path)

    def update_slider_label(self):
        """实时更新滑块旁边的文字显示"""
        mode = self.cb_v_rc.currentText()
        if mode == "cqp":
            val = self.sld_v_value.value()
            self.lbl_v_val_display.setText(str(val))
        else:
            # VBR/CBR 模式下，文字显示的是经过数学映射后的真实码率
            val = get_mapped_bitrate(self.sld_v_value.value())
            if val >= 1000:
                self.lbl_v_val_display.setText(f"{val/1000:.1f} Mbps")
            else:
                self.lbl_v_val_display.setText(f"{val} kbps")
    
    def probe_hardware_encoders(self):
        """全能探针：无情地测试一大波编码器，看看系统里哪些是真正可用的硬件加速点火器"""
        print("正在进行全硬件引擎点火自检...")
        
        # ====== 新增：检查是否已有持久化结果以极速启动 ======
        report_path = "hardware_report.txt"
        if os.path.exists(report_path):
            try:
                with open(report_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(r"可用编码器列表:\s*(\[.*?\])", content)
                    if match:
                        import ast
                        cached_encoders = ast.literal_eval(match.group(1))
                        # 确保 copy 在列表里（旧版可能没存 copy）
                        if "copy" not in cached_encoders:
                            cached_encoders.append("copy")
                        print(f"🚀 [秒开] 已从 {report_path} 读取可用编码器: {cached_encoders}")
                        return cached_encoders
            except Exception as e:
                print(f"⚠️ 解析缓存报告失败，回退到全面扫描: {e}")

        test_encoders = [
            "av1_nvenc", "hevc_nvenc", "h264_nvenc", # NVIDIA
            "av1_amf", "hevc_amf", "h264_amf",       # AMD
            "av1_qsv", "hevc_qsv", "h264_qsv",       # Intel
            "libsvtav1", "libaom-av1", "librav1e",   # AV1 CPU 编队
            "libx265", "libvpx-vp9", "libx264"       # 主流软压
        ]
        
        available = []
        
        # UI 逻辑：弹窗与进度条控制
        progress = QProgressDialog("首次运行/缓存丢失，正在初始化硬件探针...\n此过程约需10秒，只需一次。", "跳过", 0, len(test_encoders), self)
        progress.resize(400, 100)
        progress.setWindowTitle("引擎自检")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        for i, enc in enumerate(test_encoders):
            progress.setLabelText(f"正在测试 {enc} 引擎...")
            progress.setValue(i)
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents() 
            if progress.wasCanceled(): break

            # ✨ 核心剥离点：UI 不再亲自调用子进程，而是呼叫底层的独立点火器！
            is_success, err_msg = check_single_encoder(enc)
            
            if is_success:
                available.append(enc)
                print(f"✅ 探测成功: {enc}")
            else:
                if "超时或异常" in err_msg: # 处理 Exception
                    print(f"⚠️ {enc} 探测超时或异常: {err_msg}")
                else:
                    print(f"❌ {enc} 失败原因摘要: {err_msg}")
                
        progress.setValue(len(test_encoders)) 
        
        # 写入报告
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"可用编码器列表: {available}\n")
            f.write(f"FFmpeg 路径: {get_ext_path('ffmpeg.exe')}\n")
            
        available.append("copy") 
        return available

    def reprobe_hardware_encoders(self):
        """完全重新探测硬件配置"""
        report_path = "hardware_report.txt"
        if os.path.exists(report_path):
            try:
                os.remove(report_path)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法删除旧的点火缓存报告: {e}")
                return
                
        # 直接调用探针，界面会挂起重新跑
        self.available_v_encoders = self.probe_hardware_encoders()
        
        # 将重扫获得的数据重新装入原 UI 组件
        current_enc = self.cb_v_encoder.currentText()
        self.cb_v_encoder.blockSignals(True)
        self.cb_v_encoder.clear()
        self.cb_v_encoder.addItems(self.available_v_encoders)
        if current_enc in self.available_v_encoders:
            self.cb_v_encoder.setCurrentText(current_enc)
        self.cb_v_encoder.blockSignals(False)
        
        QMessageBox.information(self, "硬件扫描完毕", "重新点火测试成功，支持列表已彻底刷新！")
    
    def load_dynamic_presets(self):
        self.preset_configs = {}
        
        # 1. 极其清爽的单行读取逻辑！
        data = read_yaml_config("presets.yaml")
        raw_presets = data.get("presets", [])
        #print(f"📄 预设文件解析结果: {raw_presets}") # 调试输出，看看我们到底读到了什么
        
        if raw_presets:
            print(f"📄 成功加载外部预设配置，共读取到 {len(raw_presets)} 个预设。")

        # ==========================================
        # 2. 逐字保留：原有的核心匹配与注入逻辑
        # ==========================================
        for p in raw_presets:
            matched_encoder = next((enc for enc in self.available_v_encoders if p["requires"] in enc), None)
            
            if matched_encoder:
                config = p["ui_state"].copy()
                config["v_enc"] = matched_encoder # 动态塞入可用的硬件编码器
                if config["rc"] == "cqp": 
                    config["cqp_val"] = config.get("val", 32)
                self.preset_configs[p["name"]] = config

        # 永远在列表最后保留“自定义”选项
        self.preset_configs["⚙️ 自定义参数..."] = {}
        
    def load_tooltips(self):
        # 1. 单行读取！
        tips = read_yaml_config("tooltips.yaml")
        
        if tips:
            print("💬 成功加载外部悬浮科普提示库。")
            # 2. 从 YAML 字典中提取对应板块并注入 UI
            if "encoder_tips" in tips:
                self.set_combo_tooltips(self.cb_v_encoder, tips["encoder_tips"])
            if "preset_tips" in tips:
                self.set_combo_tooltips(self.combo_preset, tips["preset_tips"])
            if "rc_tips" in tips:
                self.set_combo_tooltips(self.cb_v_rc, tips["rc_tips"])
            if "format_tips" in tips:
                self.set_combo_tooltips(self.cb_format, tips["format_tips"])
            if "fps_tips" in tips:
                self.set_combo_tooltips(self.cb_v_fps, tips["fps_tips"])
            if "res_tips" in tips:
                self.set_combo_tooltips(self.cb_v_res, tips["res_tips"])
            if "audio_enc_tips" in tips:
                self.set_combo_tooltips(self.cb_a_encoder, tips["audio_enc_tips"])
            if "audio_bit_tips" in tips:
                self.set_combo_tooltips(self.cb_a_bitrate, tips["audio_bit_tips"])
            if "audio_sample_tips" in tips:
                self.set_combo_tooltips(self.cb_a_sample, tips["audio_sample_tips"])

    def toggle_custom_tab(self, text):
        try:
            #print(f"\n🔄 收到预设切换请求: {text}")
            if "自定义" in text:
                self.tab_custom.setVisible(True)
            else:
                self.tab_custom.setVisible(False)
                
            if text not in self.preset_configs or not self.preset_configs[text]:
                #print("⚠️ 该选项为自定义或空预设，跳过自动拨动。")
                return
                
            cfg = self.preset_configs[text]
            #print(f"✅ 提取到预设配置: {cfg}")

            # 暂时屏蔽信号
            self.cb_v_encoder.blockSignals(True)
            self.cb_v_fps.blockSignals(True)
            self.cb_v_res.blockSignals(True)
            self.cb_v_rc.blockSignals(True)
            self.sld_v_value.blockSignals(True)
            self.cb_a_encoder.blockSignals(True)
            self.cb_a_bitrate.blockSignals(True)
            self.cb_a_sample.blockSignals(True)

            #print("👉 正在拨动视频基础参数...")
            self.cb_v_encoder.setCurrentText(cfg["v_enc"])
            self.cb_v_fps.setCurrentText(cfg["fps"])
            self.cb_v_res.setCurrentText(cfg["res"])

            # 恢复附加参数
            self.txt_extra_args.setText(cfg.get("extra_args", ""))
            
            #print("👉 正在拨动码率控制模式...")
            self.cb_v_rc.setCurrentText(cfg["rc"])
            self.cb_v_rc.blockSignals(False)
            self.update_slider_range(cfg["rc"]) 
            
            #print("👉 正在计算并拨动滑块...")
            self.sld_v_value.blockSignals(True) 
            if cfg["rc"] == "cqp":
                self.sld_v_value.setValue(cfg["val"])
            else:
                slider_pos = get_reverse_mapped_slider_val(cfg["val"])
                self.sld_v_value.setValue(slider_pos)
                
            #print("👉 正在拨动音频参数...")
            self.cb_a_encoder.setCurrentText(cfg["a_enc"])
            self.cb_a_bitrate.setCurrentText(cfg["a_bit"])
            self.cb_a_sample.setCurrentText(cfg["a_sample"])

            #print("✅ 拨动完成，正在恢复信号！")
            self.cb_v_encoder.blockSignals(False)
            self.cb_v_fps.blockSignals(False)
            self.cb_v_res.blockSignals(False)
            self.sld_v_value.blockSignals(False)
            self.cb_a_encoder.blockSignals(False)
            self.cb_a_bitrate.blockSignals(False)
            self.cb_a_sample.blockSignals(False)
            
            self.update_slider_label()
            #print("🎉 UI 预设状态同步完美结束！\n")

        except Exception as e:
            import traceback
            print(f"\n💥💥 切换预设时发生致命错误: {e}")
            traceback.print_exc()
            print("💥💥 上面的报错就是导致参数没变的罪魁祸首！\n")
    
    def change_output_extension(self, new_ext):
        # 拿到当前输入框里的完整路径
        current_path = self.txt_output.text().strip()
        
        # 如果路径是空的（也就是用户还没导入视频），那就什么都不做
        if not current_path:
            return
            
        import os
        # 神奇的 os.path.splitext：直接把路径劈成“无后缀的纯路径”和“旧后缀”两半
        base_path, old_ext = os.path.splitext(current_path)
        
        # 重新拼接上刚刚选中的新后缀，并塞回输入框
        new_path = base_path + new_ext
        self.txt_output.setText(new_path)
    
    def get_current_ui_state(self):
        """
        数据打包专员：负责把当前 UI 界面上的状态打包成字典，送给底层引擎
        """
        return {
            "v_enc": self.cb_v_encoder.currentText(),
            "fps": self.cb_v_fps.currentText(),
            "res": self.cb_v_res.currentText(),
            "rc": self.cb_v_rc.currentText(),
            "cqp_val": self.sld_v_value.value(),
            "vbr_cbr_val": get_mapped_bitrate(self.sld_v_value.value()),
            "a_enc": self.cb_a_encoder.currentText(),
            "a_bit": self.cb_a_bitrate.currentText(),
            "a_sample": self.cb_a_sample.currentText(),
            "extra_args": self.txt_extra_args.text().strip()
        }
    
    def start_encoding_task(self, idx):
        # Starts a specific task from the queue
        if idx >= len(self.task_queue):
            QMessageBox.information(self, "完成", "队列中所有任务已压制完毕！")
            self.is_queue_running = False
            self.btn_start_queue.setEnabled(True)
            self.btn_start.setEnabled(True)
            return

        task = self.task_queue[idx]
        if task["status"] != "等待中" and task["status"] != "Pending":
            # Skip already finished or running tasks
            self.current_task_idx += 1
            self.start_encoding_task(self.current_task_idx)
            return

        input_path = task["input"]
        output_path = task["output"]
        ui_config = task["ui_state"]

        self.table_queue.setItem(idx, 2, self.create_table_item("压制中 🚀"))
        task["status"] = "Encoding"
        
        # UI updates for current task
        self.txt_input.setText(input_path)
        self.txt_output.setText(output_path)
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_start.setText("⏳ 压制中...")
        self.lbl_status.setText(f"状态: 队列第 {idx+1} 个任务...")

        self.total_seconds = get_video_duration(input_path)
        
        self.enable_preview = self.chk_preview.isChecked()
        
        # ====== 新增内存管道路由 ======
        self.preview_port = 0 # Worker会随机分配
        
        if self.enable_preview:
            # 开启TCP服务器线程接收MJPEG视频流
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', 0))
            sock.listen(1)
            self.preview_port = sock.getsockname()[1]
            self.preview_sock = sock
            
            # 启动独立线程专门接收Socket流
            from PySide6.QtCore import QThread, Signal
            class PreviewReceiver(QThread):
                frame_received = Signal(bytes)
                
                def __init__(self, s):
                    super().__init__()
                    self.server_sock = s
                    self.is_running = True
                    
                def run(self):
                    self.server_sock.settimeout(2.0)
                    try:
                        conn, addr = self.server_sock.accept()
                        conn.settimeout(1.0)
                        
                        buffer = bytearray()
                        while self.is_running:
                            try:
                                data = conn.recv(16384)
                                if not data:
                                    break
                                buffer.extend(data)
                                
                                # 持续解析 MJPEG 边界 (FF D8 ... FF D9)
                                while True:
                                    start_idx = buffer.find(b'\xff\xd8')
                                    if start_idx == -1:
                                        # 没头，清空无用前导数据
                                        buffer.clear()
                                        break
                                        
                                    end_idx = buffer.find(b'\xff\xd9', start_idx + 2)
                                    if end_idx == -1:
                                        # 不完整，等下一次接收
                                        break
                                        
                                    # 提取出一帧完整图像
                                    frame_data = buffer[start_idx:end_idx+2]
                                    self.frame_received.emit(bytes(frame_data))
                                    
                                    # 丢弃已被提取的数据，保留剩余未处理的部分
                                    buffer = buffer[end_idx+2:]
                                    
                            except socket.timeout:
                                continue
                            except Exception:
                                break
                                
                        conn.close()
                    except socket.timeout:
                        pass # FFmpeg没连上
                    except Exception as e:
                        print(f"预览管道异常: {e}")
                    finally:
                        self.server_sock.close()
                        
                def stop(self):
                    self.is_running = False
                    try:
                        # 尝试唤起阻塞的 accept
                        dummy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        dummy.connect(('127.0.0.1', self.server_sock.getsockname()[1]))
                        dummy.close()
                    except: pass
                    
            self.preview_receiver = PreviewReceiver(sock)
            self.preview_receiver.frame_received.connect(self.update_preview_frame)
            self.lbl_preview.setText("正在建立本地TCP内存管道...")
            self.preview_receiver.start()
            
        dynamic_args = build_ffmpeg_args(ui_config)
        
        self.worker = FFmpegWorker(input_file=input_path, output_file=output_path, enable_preview=self.enable_preview, preview_port=self.preview_port, encode_args=dynamic_args)
        self.worker.log_signal.connect(self.print_log)
        self.worker.error_signal.connect(self.handle_worker_error)
        self.worker.finished_signal.connect(self.encoding_finished)
        self.worker.start()

    def handle_worker_error(self, err_msg):
        # 抛出弹窗，并更新状态
        QMessageBox.critical(self, "压制失败", err_msg)
        self.lbl_status.setText("状态: 压制失败 ❌")
        
        # 将队列状态标红
        if self.current_task_idx < len(self.task_queue):
            self.task_queue[self.current_task_idx]["status"] = "Error"
            self.table_queue.setItem(self.current_task_idx, 2, self.create_table_item("错误 ❌"))
            
        self.encoding_finished()

    def start_encoding(self):
        input_path = self.txt_input.text().strip()
        output_path = self.txt_output.text().strip()

        # 如果输入框有独立的视频路径，直接添加入列（防止没加就点了开始报错）
        if input_path and output_path and "批量" not in input_path:
            self.add_to_queue()
            # 加完后请空，防止第二次点击又重复加
            self.txt_input.clear()
            self.txt_output.clear()
            
        self.start_queue()

    def add_to_queue(self):
        input_path = self.txt_input.text().strip()
        output_path = self.txt_output.text().strip()

        if not input_path or not output_path:
            QMessageBox.warning(self, "警告", "请先选择需要压制的视频以添加到队列！")
            return
            
        self.add_task_to_table(input_path, output_path, self.get_current_ui_state())
        
    def add_task_to_table(self, input_path, output_path, ui_state):
        from PySide6.QtWidgets import QTableWidgetItem
        try:
            # 打开一条只读把手从而触发系统锁定文件的防删保护
            file_handle = open(input_path, 'rb')
        except Exception as e:
            QMessageBox.warning(self, "错误", f"无法锁定并加载源文件:\n{e}")
            return
            
        task = {
            "input": input_path,
            "output": output_path,
            "ui_state": ui_state,
            "status": "等待中",
            "file_handle": file_handle # 持有句柄
        }
        self.task_queue.append(task)
        
        row = self.table_queue.rowCount()
        self.table_queue.insertRow(row)
        
        filename = os.path.basename(input_path)
        ext = os.path.splitext(output_path)[1]
        
        self.table_queue.setItem(row, 0, self.create_table_item(filename))
        self.table_queue.setItem(row, 1, self.create_table_item(f"{ui_state['v_enc']} {ext}"))
        self.table_queue.setItem(row, 2, self.create_table_item("等待中"))
        
        self.check_queue_selection_state()
        
    def create_table_item(self, text):
        from PySide6.QtWidgets import QTableWidgetItem
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() ^ Qt.ItemIsEditable)  # Read-only
        return item

    def start_queue(self):
        if len(self.task_queue) == 0:
            QMessageBox.warning(self, "警告", "任务队列为空！请先添加任务。")
            return
        
        if self.is_queue_running:
            return
            
        self.is_queue_running = True
        self.btn_start_queue.setEnabled(False)
        self.btn_start.setEnabled(False)
        
        self._run_next_pending_task()
        
    def _run_next_pending_task(self):
        # Find first pending task from the very beginning
        found = False
        for i, t in enumerate(self.task_queue):
            if t["status"] == "等待中" or t["status"] == "Pending":
                self.current_task_idx = i
                found = True
                break
                
        if found:
            self.start_encoding_task(self.current_task_idx)
        else:
            self.is_queue_running = False
            self.btn_start_queue.setEnabled(True)
            self.btn_start.setEnabled(True)
            self.lbl_status.setText("状态: 队列中所有任务均已处理完毕！")
            QMessageBox.information(self, "提示", "所有排队的任务皆已处理完毕。")
            
    def load_queue_item_to_ui(self):
        selected_ranges = self.table_queue.selectedRanges()
        if not selected_ranges:
            self.check_queue_selection_state()
            return
            
        rows = []
        for r in selected_ranges:
            rows.extend(range(r.topRow(), r.bottomRow() + 1))
            
        if not rows:
            return
            
        # If multiple tasks are selected, we just load the first one's config to UI but keep paths empty
        first_row = rows[0]
        if first_row < 0 or first_row >= len(self.task_queue):
            return
            
        task = self.task_queue[first_row]
        
        # Restore basic paths only if a single item is selected
        if len(rows) == 1:
            self.txt_input.setText(task["input"])
            self.txt_output.setText(task["output"])
        else:
            self.txt_input.setText(f"已选中 {len(rows)} 个任务 (批量修改模式)")
            self.txt_output.setText("")
        
        # Restore format target box
        ext = os.path.splitext(task["output"])[1]
        for i in range(self.cb_format.count()):
            if self.cb_format.itemText(i) == ext:
                self.cb_format.setCurrentIndex(i)
                break
                
        # Block signals temporarily to avoid redundant processing
        # Use custom tab trick to restore config since it mimics preset parsing
        cfg = task["ui_state"]
        
        self.cb_v_encoder.blockSignals(True)
        self.cb_v_fps.blockSignals(True)
        self.cb_v_res.blockSignals(True)
        self.cb_v_rc.blockSignals(True)
        self.sld_v_value.blockSignals(True)
        self.cb_a_encoder.blockSignals(True)
        self.cb_a_bitrate.blockSignals(True)
        self.cb_a_sample.blockSignals(True)

        self.cb_v_encoder.setCurrentText(cfg.get("v_enc", "copy"))
        self.cb_v_fps.setCurrentText(cfg.get("fps", "保持源"))
        self.cb_v_res.setCurrentText(cfg.get("res", "保持源"))
        self.txt_extra_args.setText(cfg.get("extra_args", ""))
        
        self.cb_v_rc.setCurrentText(cfg.get("rc", "cqp"))
        self.cb_v_rc.blockSignals(False)
        self.update_slider_range(cfg.get("rc", "cqp")) 
        
        self.sld_v_value.blockSignals(True) 
        if cfg.get("rc", "cqp") == "cqp":
            self.sld_v_value.setValue(cfg.get("cqp_val", 32))
        else:
            slider_pos = get_reverse_mapped_slider_val(cfg.get("vbr_cbr_val", 5000))
            self.sld_v_value.setValue(slider_pos)
            
        self.cb_a_encoder.setCurrentText(cfg.get("a_enc", "aac"))
        self.cb_a_bitrate.setCurrentText(cfg.get("a_bit", "320k"))
        self.cb_a_sample.setCurrentText(cfg.get("a_sample", "保持源"))

        self.cb_v_encoder.blockSignals(False)
        self.cb_v_fps.blockSignals(False)
        self.cb_v_res.blockSignals(False)
        self.sld_v_value.blockSignals(False)
        self.cb_a_encoder.blockSignals(False)
        self.cb_a_bitrate.blockSignals(False)
        self.cb_a_sample.blockSignals(False)
        
        self.update_slider_label()
        
        self.check_queue_selection_state()

    def update_queue_item(self):
        selected_ranges = self.table_queue.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "警告", "请先在列表中选中要修改的任务！")
            return
            
        rows = []
        for r in selected_ranges:
            rows.extend(range(r.topRow(), r.bottomRow() + 1))
            
        ui_state = self.get_current_ui_state()
        target_ext = self.cb_format.currentText()
        if not target_ext.startswith('.'):
            target_ext = f".{target_ext}"
            
        updated_count = 0
            
        for row in rows:
            if row < 0 or row >= len(self.task_queue):
                continue
                
            task = self.task_queue[row]
            
            if task["status"] == "Encoding" or task["status"] == "压制中 🚀":
                continue # Skip running tasks
                
            task["ui_state"] = ui_state
            
            # If it is a single item update, we also update the input/output paths from text boxes
            if len(rows) == 1:
                input_path = self.txt_input.text().strip()
                output_path = self.txt_output.text().strip()
                if input_path and output_path and "批量" not in input_path:
                    task["input"] = input_path
                    task["output"] = output_path
            else:
                # For batch updating, apply the new target extension to the old output path if needed
                old_out = task["output"]
                base_path, _ = os.path.splitext(old_out)
                task["output"] = base_path + target_ext
                
            filename = os.path.basename(task["input"])
            ext = os.path.splitext(task["output"])[1]
            
            self.table_queue.setItem(row, 0, self.create_table_item(filename))
            self.table_queue.setItem(row, 1, self.create_table_item(f"{ui_state['v_enc']} {ext}"))
            updated_count += 1
            
        if updated_count > 0:
            QMessageBox.information(self, "成功", f"成功更新了 {updated_count} 个任务配置！")
        else:
            QMessageBox.warning(self, "跳过", "未更新任何任务 (可能选中的任务正在压制中)。")
            
        self.check_queue_selection_state()
        
    def reset_queue_item(self):
        selected_ranges = self.table_queue.selectedRanges()
        if not selected_ranges:
            QMessageBox.warning(self, "警告", "请先在列表中选中要重置状态的任务！")
            return
            
        rows = []
        for r in selected_ranges:
            rows.extend(range(r.topRow(), r.bottomRow() + 1))
            
        for row in rows:
            if row < 0 or row >= len(self.task_queue):
                continue
                
            task = self.task_queue[row]
            
            if task["status"] == "Encoding" or task["status"] == "压制中 🚀":
                continue
                
            task["status"] = "等待中"
            self.table_queue.setItem(row, 2, self.create_table_item("等待中"))
            
        self.check_queue_selection_state()
            
    def clear_task_handle(self, task):
        # 关闭文件句柄以解除文件锁定
        if "file_handle" in task and task["file_handle"]:
            try:
                task["file_handle"].close()
                task["file_handle"] = None
            except: pass

    def delete_queue_item(self):
        selected_ranges = self.table_queue.selectedRanges()
        if not selected_ranges:
            return
            
        rows = []
        for r in selected_ranges:
            rows.extend(range(r.topRow(), r.bottomRow() + 1))
            
        rows.sort(reverse=True) # Delete from bottom to top to preserve indices
        
        for row in rows:
            if row < 0 or row >= len(self.task_queue):
                continue
                
            task = self.task_queue[row]
            if task["status"] == "Encoding" or task["status"] == "压制中 🚀":
                QMessageBox.warning(self, "警告", f"第 {row + 1} 行任务正在压制中，无法删除！")
                continue
                
            self.clear_task_handle(task)
            self.task_queue.pop(row)
            self.table_queue.removeRow(row)
            # Adjust current_task_idx if necessary when deleting items prior to current
            if row < self.current_task_idx:
                self.current_task_idx -= 1
                
        self.check_queue_selection_state()
                
    def show_queue_context_menu(self, pos):
        menu = QMenu(self)
        
        action_update = QAction("🔄 保存修改到选中项", self)
        action_update.triggered.connect(self.update_queue_item)
        menu.addAction(action_update)
        
        action_reset = QAction("↺ 重置状态", self)
        action_reset.triggered.connect(self.reset_queue_item)
        menu.addAction(action_reset)
        
        menu.addSeparator()
        
        action_delete = QAction("❌ 删除任务", self)
        action_delete.triggered.connect(self.delete_queue_item)
        menu.addAction(action_delete)
        
        menu.exec_(self.table_queue.mapToGlobal(pos))
            
    def clear_queue(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            QMessageBox.warning(self, "警告", "正在压制中，无法清空队列！")
            return
            
        for task in self.task_queue:
            self.clear_task_handle(task)
            
        self.task_queue.clear()
        self.table_queue.setRowCount(0)
        self.current_task_idx = 0
        
        self.check_queue_selection_state()
        
    def toggle_pause(self):
        if self.btn_pause.text() == "⏸ 暂停":
            self.worker.pause()
            self.btn_pause.setText("▶ 恢复")
            self.lbl_status.setText("状态: 已暂停 (显卡已挂起)")
        else:
            self.worker.resume()
            self.btn_pause.setText("⏸ 暂停")
            self.lbl_status.setText("状态: 正在狂飙压制中...")
            
    def stop_encoding(self):
        # Stop global queue progression
        self.is_queue_running = False
        self.btn_start_queue.setEnabled(True)
        
        # 只要触发停止按钮，只管杀后台，后续的 UI 更新全部交给信号自然触发
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()

    def print_log(self, text):
        #print(text) #调试时直接往控制台输出
        # ====== 基于 -progress 的解析逻辑 ======
        if text.startswith("out_time="):
            time_str = text.split("=")[1].strip()
            if time_str and time_str != "N/A":
                # time_str 是 00:00:00.000000 的形式
                try:
                    h, m, s = time_str.split(':')
                    current_seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    percent = int((current_seconds / self.total_seconds) * 100)
                    percent = max(0, min(100, percent))
                    self.progress_bar.setValue(percent)
                    # 缓存给下面显示用
                    self._last_time_str = time_str[:11] 
                except: pass
                
        elif text.startswith("speed="):
            speed_text = text.split("=")[1].strip()
            # 从缓存里拿时间
            t = getattr(self, '_last_time_str', '--')
            s = getattr(self, '_last_size_str', '--')
            self.lbl_status.setText(f"状态: 狂飙压制中... | 速度: {speed_text} | 当前进度: {t} | 当前文件大小：{s}")
            
        elif text.startswith("total_size="):
            size_bytes_str = text.split("=")[1].strip()
            if size_bytes_str and size_bytes_str.isdigit():
                size_bytes = int(size_bytes_str)
                if size_bytes >= 1024 * 1024 * 1024:
                    storage_text = f"{size_bytes / (1024 * 1024 * 1024):.2f} GiB"
                elif size_bytes >= 1024 * 1024:
                    storage_text = f"{size_bytes / (1024 * 1024):.2f} MiB"
                else:
                    storage_text = f"{size_bytes / 1024:.2f} KiB"
                self._last_size_str = storage_text
                
        # 兼容 FFmpeg 一些普通的日志行直接显示在UI下方，比如一些警告。但不用太过频繁。
        
    def update_preview_frame(self, data):
        """直接接收子线程传来的 JPEG 二进制流，无需读写文件"""
        try:
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled_pixmap = pixmap.scaled(
                    self.lbl_preview.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.lbl_preview.setPixmap(scaled_pixmap)
        except Exception:
            pass

    def encoding_finished(self):
        # 1. 恢复所有按钮的基础状态
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🚀 开始") # === 新增：将按钮文字彻底恢复初始状态 ===
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setText("⏸ 暂停")
        
        # 2. 停止接收线程
        if hasattr(self, 'preview_receiver'):
            self.preview_receiver.stop()

        # 3. 核心分流：判断到底是正常跑完，还是被中途干掉的？
        if getattr(self.worker, 'is_cancelled', False):
            # 被强行中止的 UI 逻辑
            # 但是注意如果是因为 error 而调用过来的，上面可能已经设了状态
            if "错误" not in self.lbl_status.text() and "失败" not in self.lbl_status.text():
                self.lbl_status.setText("状态: 压制已强制中止 🚫")
                
            if self.enable_preview:
                self.lbl_preview.clear()
                self.lbl_preview.setText("当前画面获取结束")
            print("====== 压制已被用户或异常中止！======")
            
            # Update Queue Status
            if self.current_task_idx < len(self.task_queue):
                # 只有在还没改状态时才改
                if self.task_queue[self.current_task_idx]["status"] not in ["Error", "错误 ❌"]:
                    self.task_queue[self.current_task_idx]["status"] = "Cancelled"
                    self.table_queue.setItem(self.current_task_idx, 2, self.create_table_item("已取消 🚫"))
                
            self.is_queue_running = False
            self.btn_start_queue.setEnabled(True)

        else:
            # 正常顺利完成的 UI 逻辑
            self.lbl_status.setText("状态: 压制完成！ ✅")
            self.progress_bar.setValue(100) # 只有正常完成才强行拉满进度条
            if self.enable_preview:
                self.lbl_preview.clear()
                self.lbl_preview.setText("压制已完成\n(画面预览结束)")
            print("====== 压制彻底结束！======")
            
            # Update Queue Status
            if self.current_task_idx < len(self.task_queue):
                self.task_queue[self.current_task_idx]["status"] = "Completed"
                self.table_queue.setItem(self.current_task_idx, 2, self.create_table_item("完成 ✅"))
                self.clear_task_handle(self.task_queue[self.current_task_idx])
                
            # Auto-start next task if in queue mode
            if self.is_queue_running:
                self._run_next_pending_task()
    
    def select_input_file(self):
        # 呼出 Windows 原生文件选择框，限制只能选常见视频格式
        file_path, _ = QFileDialog.getOpenFileName(self, "选择原视频", "", "视频文件 (*.mp4 *.mkv *.mov *.avi *.mkv);;所有文件 (*.*)")
        if file_path:
            # 把选中的路径填入输入框
            self.txt_input.setText(file_path)
            
            # 比如输入是 D:/video.mp4，输出自动变成 D:/video_output.mp4
            default_out = file_path.rsplit('.', 1)[0] + "_output.mp4"
            self.txt_output.setText(default_out)
        
        if file_path:
            # 换上一套极客专用的荧光青色、等宽字体样式
            self.lbl_preview.setStyleSheet("background-color: #0b0c10; color: #45a3ad; border-radius: 8px; font-weight: bold; font-family: Consolas, monospace; font-size: 16px;")
            self.lbl_preview.setText("正在扫描视频底层数据...")
            
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents() # 强制刷新 UI，让文字瞬间亮起
            
            # 呼叫探针，把拿到情报贴在屏幕上
            info_text = probe_video_info(file_path)
            self.lbl_preview.setText(info_text)

    def select_output_file(self):
        # 呼出 Windows 原生保存框
        file_path, _ = QFileDialog.getSaveFileName(self, "设置导出路径", self.txt_output.text(), "视频文件 (*.mp4)")
        if file_path:
            self.txt_output.setText(file_path)

    def closeEvent(self, event: QCloseEvent):
        if hasattr(self, 'worker') and self.worker.isRunning():
            reply = QMessageBox.question(self, '确认退出', "压制尚未完成，确定要强行退出并放弃任务吗？",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.worker.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

    def set_combo_tooltips(self, combo, tooltips_dict):
        """
        为 QComboBox 的每个选项设置悬浮说明
        :param combo: 目标下拉菜单对象
        :param tooltips_dict: 格式为 {"选项名": "说明文字"} 的字典
        """
        model = combo.model() # 获取下拉菜单背后的数据模型
        for i in range(combo.count()):
            text = combo.itemText(i)
            if text in tooltips_dict:
                # 核心：将说明文字注入到该选项的 ToolTip 角色中
                model.setData(model.index(i, 0), tooltips_dict[text], Qt.ToolTipRole)
    