import sys,os,tempfile
import subprocess
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QMessageBox,QProgressDialog)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QCloseEvent
from PySide6.QtCore import Qt

from core.utils import get_ext_path, get_app_dir, init_config_files
from core.worker import FFmpegWorker
from core.engine import get_video_duration, probe_video_info
from ui.ui_main_window import Ui_MainWindow

class FFmpegGUI(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        # ==========================================
        # 1. 魔法启动：一行代码加载所有生成的界面元素
        # ==========================================
        self.setupUi(self)

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
        
        # 初始化：手动触发一次范围设定（默认 CQP）
        self.update_slider_range("cqp")
        
    
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
    
    def get_mapped_bitrate(self, slider_val):
        """将 0-100 的滑块值进行非线性(三次幂)映射到 50-30000 kbps"""
        min_kbps = 50
        max_kbps = 30000
        # 使用三次幂函数：滑块在前半段数字变化极慢，后半段变化极快
        ratio = slider_val / 100.0
        mapped_val = min_kbps + (max_kbps - min_kbps) * (ratio ** 3)
        # 把计算结果规整一下，向下取整到最接近的 10，让 UI 看起来更整洁
        return int(round(mapped_val / 10) * 10)
    
    def get_reverse_mapped_slider_val(self, target_kbps):
        """将真实的码率 (如 5000 kbps) 逆向推导回 0-100 的滑块物理刻度"""
        min_kbps = 50
        max_kbps = 30000
        if target_kbps <= min_kbps: return 0
        if target_kbps >= max_kbps: return 100
        # 逆向公式：开三次方根
        ratio = ((target_kbps - min_kbps) / (max_kbps - min_kbps)) ** (1/3.0)
        return int(round(ratio * 100))
    
    def update_slider_label(self):
        """实时更新滑块旁边的文字显示"""
        mode = self.cb_v_rc.currentText()
        if mode == "cqp":
            val = self.sld_v_value.value()
            self.lbl_v_val_display.setText(str(val))
        else:
            # VBR/CBR 模式下，文字显示的是经过数学映射后的真实码率
            val = self.get_mapped_bitrate(self.sld_v_value.value())
            if val >= 1000:
                self.lbl_v_val_display.setText(f"{val/1000:.1f} Mbps")
            else:
                self.lbl_v_val_display.setText(f"{val} kbps")
    
    def probe_hardware_encoders(self):
        print("正在进行全硬件引擎点火自检...")
        test_encoders = [
            "av1_nvenc", "hevc_nvenc", "h264_nvenc", # NVIDIA 提前（因为你是 N 卡用户）
            "av1_amf", "hevc_amf", "h264_amf",       # AMD
            "av1_qsv", "hevc_qsv", "h264_qsv",       # Intel
            "libsvtav1", "libx265", "libx264"        # CPU
        ]
        
        available = []
        CREATE_NO_WINDOW = 0x08000000
        
        progress = QProgressDialog("正在初始化硬件探针...", "跳过", 0, len(test_encoders), self)
        progress.setWindowTitle("引擎自检")
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        for i, enc in enumerate(test_encoders):
            progress.setLabelText(f"正在测试 {enc} 引擎...")
            progress.setValue(i)
            QApplication.processEvents() 
            if progress.wasCanceled(): break

            # === NVIDIA 兼容性补丁指令 ===
            cmd = [
                get_ext_path("ffmpeg.exe"), "-y", 
                "-f", "lavfi", "-i", "color=c=black:s=320x240", # 增大分辨率，避开对齐限制
                "-vframes", "1", 
                "-c:v", enc, 
                "-pix_fmt", "yuv420p", # ！！！核心：强制指定 NVENC 最喜欢的 yuv420p 格式
                "-f", "null", "-"
            ]
            
            try:
                # === 核心改进：超时增加到 5 秒，给 N 卡 CUDA 初始化留足时间 ===
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    encoding='utf-8', 
                    creationflags=CREATE_NO_WINDOW, 
                    timeout=5 
                )
                
                if result.returncode == 0:
                    available.append(enc)
                    print(f"✅ 探测成功: {enc}")
                else:
                    # 即使失败，我们也要看一眼为什么失败 (特别是 N 卡)
                    print(f"❌ {enc} 失败原因摘要: {result.stderr[-100:]}")
            except Exception as e:
                print(f"⚠️ {enc} 探测超时或异常: {e}")
                
        progress.setValue(len(test_encoders)) 
        # 生成硬件自检报告，方便你在别人电脑上排查
        with open("hardware_report.txt", "w", encoding="utf-8") as f:
            f.write(f"可用编码器列表: {available}\n")
            f.write(f"FFmpeg 路径: {get_ext_path('ffmpeg.exe')}\n")
        available.append("copy") 
        return available
    
    def load_dynamic_presets(self):
        import yaml # 局部引入，保持顶部整洁
        
        self.preset_configs = {}
        raw_presets = []

        # 1. 动态定位 config/presets.yaml 的绝对路径
        yaml_path = os.path.join(get_app_dir(), "config", "presets.yaml")

        # 2. 安全读取 YAML 文件
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                raw_presets = data.get("presets", [])
            print(f"📄 成功加载外部预设配置，共读取到 {len(raw_presets)} 个预设。")
        except FileNotFoundError:
            print(f"⚠️ 找不到配置文件: {yaml_path}，请检查 config 目录！")
        except Exception as e:
            print(f"💥 读取 presets.yaml 发生语法错误: {e}")

        # ==========================================
        # 3. 逐字保留：原汁原味的核心匹配与注入逻辑
        # ==========================================
        for p in raw_presets:
            matched_encoder = next((enc for enc in self.available_v_encoders if p["requires"] in enc), None)
            
            if matched_encoder:
                config = p["ui_state"].copy()
                config["v_enc"] = matched_encoder # 动态塞入可用的硬件编码器
                self.preset_configs[p["name"]] = config

        # 永远在列表最后保留“自定义”选项
        self.preset_configs["⚙️ 自定义参数..."] = {}
        
    def load_tooltips(self):
        import yaml
        import os
        
        yaml_path = os.path.join(get_app_dir(), "config", "tooltips.yaml")
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                tips = yaml.safe_load(f)
            
            # 从 YAML 字典中提取对应板块并注入 UI
            if "encoder_tips" in tips:
                self.set_combo_tooltips(self.cb_v_encoder, tips["encoder_tips"])
            if "preset_tips" in tips:
                self.set_combo_tooltips(self.combo_preset, tips["preset_tips"])
            if "rc_tips" in tips:
                self.set_combo_tooltips(self.cb_v_rc, tips["rc_tips"])
                
            print("💬 成功加载外部悬浮科普提示库。")
        except FileNotFoundError:
            print(f"⚠️ 找不到提示文案库: {yaml_path}")
        except Exception as e:
            print(f"💥 读取 tooltips.yaml 失败: {e}")

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
            
            #print("👉 正在拨动码率控制模式...")
            self.cb_v_rc.setCurrentText(cfg["rc"])
            self.cb_v_rc.blockSignals(False)
            self.update_slider_range(cfg["rc"]) 
            
            #print("👉 正在计算并拨动滑块...")
            self.sld_v_value.blockSignals(True) 
            if cfg["rc"] == "cqp":
                self.sld_v_value.setValue(cfg["val"])
            else:
                slider_pos = self.get_reverse_mapped_slider_val(cfg["val"])
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
    
    def build_ffmpeg_args(self):
        # ✨ 核心修复 3：彻底删除了最前面的 if 拦截器！
        # 现在的唯一真理来源就是 UI 面板！
        args = []
        v_enc = self.cb_v_encoder.currentText()
        is_nvenc = "nvenc" in v_enc
        is_amf = "amf" in v_enc
        is_qsv = "qsv" in v_enc
        is_cpu = "lib" in v_enc

        # --- 视频编码部分 ---
        if v_enc == "copy":
            args.extend(["-c:v", "copy"])
        else:
            args.extend(["-c:v", v_enc])
            
            # NVIDIA / AMD 硬件 H264 的护城河 (修复暴毙问题)
            if v_enc in ["h264_nvenc", "h264_amf"]:
                args.extend(["-pix_fmt", "yuv420p", "-profile:v", "high"])
            
            # 帧率处理
            fps = self.cb_v_fps.currentText()
            if fps != "保持源": 
                args.extend(["-r", fps])
            
            # 分辨率处理
            res = self.cb_v_res.currentText()
            if res == "1080p": args.extend(["-vf", "scale=-1:1080"])
            elif res == "720p": args.extend(["-vf", "scale=-1:720"])
            elif res == "2160p": args.extend(["-vf", "scale=-1:2160"])
            elif res == "1440p": args.extend(["-vf", "scale=-1:1440"])
                
            # --- 码率控制适配 (接入最新非线性滑块逻辑) ---
            rc_mode = self.cb_v_rc.currentText()
            
            if rc_mode == "cqp":
                val = str(self.sld_v_value.value()) # CQP 保持线性，直接拿原值
                if is_nvenc:
                    # NVENC 真正的“恒定画质”最佳实践
                    args.extend(["-rc", "vbr", "-cq", val, "-b:v", "0"])
                elif is_amf:
                    args.extend(["-rc", "cqp", "-qp_i", val, "-qp_p", val])
                elif is_qsv:
                    args.extend(["-global_quality", val])
                else:
                    args.extend(["-crf", val])
                    
            elif rc_mode == "vbr":
                val_int = self.get_mapped_bitrate(self.sld_v_value.value()) # VBR 拿非线性映射后的真实码率
                val = f"{val_int}k"
                if is_nvenc:
                    args.extend(["-rc", "vbr", "-b:v", val, "-maxrate:v", val, "-bufsize:v", val])
                elif is_amf:
                    args.extend(["-rc", "vbr_peak", "-b:v", val])
                else:
                    args.extend(["-b:v", val])
                    
            elif rc_mode == "cbr":
                val_int = self.get_mapped_bitrate(self.sld_v_value.value()) # CBR 拿非线性映射后的真实码率
                val = f"{val_int}k"
                if is_nvenc:
                    args.extend(["-rc", "cbr", "-b:v", val, "-maxrate:v", val, "-bufsize:v", val])
                elif is_amf:
                    args.extend(["-rc", "cbr", "-b:v", val])
                else:
                    args.extend(["-b:v", val, "-maxrate:v", val, "-bufsize:v", val])

        # --- 音频部分 ---
        a_enc = self.cb_a_encoder.currentText()
        if "剥离静音" in a_enc: 
            args.extend(["-an"])
        elif a_enc == "copy": 
            args.extend(["-c:a", "copy"])
        else:
            args.extend(["-c:a", a_enc])
            ab = self.cb_a_bitrate.currentText()
            args.extend(["-b:a", ab])
            ar = self.cb_a_sample.currentText()
            if ar != "保持源": 
                args.extend(["-ar", ar])

        return args
    
    def start_encoding(self):
        # 1. 动态获取界面上输入框里的路径
        input_path = self.txt_input.text().strip()
        output_path = self.txt_output.text().strip()

        # 简单拦截：如果没选文件就点开始，弹窗警告并打断
        if not input_path or not output_path:
            QMessageBox.warning(self, "警告", "请先选择需要压制的视频！")
            return

        # 2. 锁定按钮，防止重复点击，激活暂停和停止按钮
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.btn_start.setText("⏳ 压制中...")
        self.lbl_status.setText("状态: 连接编码器...")

        # 3. 在开启多线程前，用探针瞬间读取真实时长并保存为实例属性
        self.total_seconds = get_video_duration(input_path)
        print(f"探针成功获取视频总时长: {self.total_seconds} 秒")

        # 4. === 找回失踪的预览开关逻辑与路径生成 ===
        self.enable_preview = self.chk_preview.isChecked()
        self.preview_temp_dir = tempfile.gettempdir() 
        self.preview_path = os.path.join(self.preview_temp_dir, "ffmpeg_preview_temp.jpg")

        # 如果上次的残留图片还在，先清理掉避免画面穿越
        if os.path.exists(self.preview_path):
            try:
                os.remove(self.preview_path)
            except:
                pass

        # 启动前台监视器定时器
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.update_preview)
        if self.enable_preview:
            self.lbl_preview.setText("正在连接画面源...")
            self.preview_timer.start(1000) 

        # 5. 呼叫翻译官，把当前界面的选择翻译成参数列表
        dynamic_args = self.build_ffmpeg_args()
        print(f"生成的压制参数: {dynamic_args}") 

        # 6. 创建并启动后台大心脏 (传入动态获取的路径、开关状态和翻译好的参数)
        self.worker = FFmpegWorker(input_path, output_path, self.enable_preview, self.preview_path, dynamic_args)
        self.worker.log_signal.connect(self.print_log)
        self.worker.finished_signal.connect(self.encoding_finished)
        self.worker.start()
        
    def toggle_pause(self):
        if self.btn_pause.text() == "⏸ 暂停":
            self.worker.pause()
            self.btn_pause.setText("▶ 恢复")
            self.lbl_status.setText("状态: 已暂停 (显卡已挂起)")
            if hasattr(self, 'preview_timer'): self.preview_timer.stop()
        else:
            self.worker.resume()
            self.btn_pause.setText("⏸ 暂停")
            self.lbl_status.setText("状态: 正在狂飙压制中...")
            if hasattr(self, 'preview_timer'): self.preview_timer.start(1000)
            
    def stop_encoding(self):
        # 只要触发停止按钮，只管杀后台，后续的 UI 更新全部交给信号自然触发
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.stop()

    def print_log(self, text):
        #print(text) #调试时直接往控制台输出
        # 1. 使用正则表达式狙击“当前时间”和“压制速度”
        # 匹配格式如 time=01:14:58.85
        time_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", text)
        # 匹配格式如 speed=12.9x
        speed_match = re.search(r"speed=\s*([\d\.]+)x", text)
        storage_match = re.search(r"size=\s*([\d\.]+)KiB", text)

        if time_match:
            time_str = time_match.group(1)
            
            # 2. 将 01:14:58.85 换算成纯秒数
            h, m, s = time_str.split(':')
            current_seconds = int(h) * 3600 + int(m) * 60 + float(s)

            # 3 & 4. === 修改：使用探针读取到的真实时长来计算百分比 ===
            percent = int((current_seconds / self.total_seconds) * 100)
            
            # 限制在 0-100 之间，防止浮点微小误差导致进度条溢出报错
            percent = max(0, min(100, percent))
            self.progress_bar.setValue(percent)
            
            # 格式化储存大小显示
            if storage_match:
                size_kib = float(storage_match.group(1))
                if size_kib >= 1000 * 1000:
                    storage_text = f"{size_kib / (1000 * 1000):.2f} GiB"
                elif size_kib >= 1000:
                    storage_text = f"{size_kib / 1000:.2f} MiB"
                else:
                    storage_text = f"{size_kib:.2f} KiB"

            # 5. 更新状态栏面板
            speed_text = speed_match.group(1) if speed_match else "--"
            self.lbl_status.setText(f"状态: 狂飙压制中... | 速度: {speed_text}x | 当前进度: {time_str} | 当前文件大小：{storage_text}")
        
    def update_preview(self):
        if not os.path.exists(self.preview_path):
            return

        try:
            # 1. 瞬间将硬盘文件的所有字节吸入 Python 内存
            with open(self.preview_path, 'rb') as f:
                data = f.read()
            
            # 2. 基础过滤：如果图片连 1KB 都没有，说明 FFmpeg 刚清空文件，直接跳过
            if len(data) < 1024:
                return

            # 3. 严格校验内存数据：必须以 FF D8 开头 (SOF)，且以 FF D9 结尾 (EOF)
            if not (data.startswith(b'\xff\xd8') and data.endswith(b'\xff\xd9')):
                return

            # 4. 核心魔法：切断硬盘联系！直接让 Qt 从刚才吸入的内存字节 (data) 里读取画面
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                scaled_pixmap = pixmap.scaled(
                    self.lbl_preview.size(), 
                    Qt.KeepAspectRatio, 
                    Qt.SmoothTransformation
                )
                self.lbl_preview.setPixmap(scaled_pixmap)

        except Exception:
            # 兜底：如果这 1 毫秒刚好碰到系统级的文件死锁，直接静默放过，等下一秒
            pass

    def encoding_finished(self):
        # 1. 恢复所有按钮的基础状态
        self.btn_start.setEnabled(True)
        self.btn_start.setText("🚀 开始") # === 新增：将按钮文字彻底恢复初始状态 ===
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.btn_pause.setText("⏸ 暂停")
        
        # 2. 停止可能还在刷新的监视器定时器
        if hasattr(self, 'preview_timer') and self.preview_timer.isActive():
            self.preview_timer.stop()

        # 3. 核心分流：判断到底是正常跑完，还是被中途干掉的？
        if getattr(self.worker, 'is_cancelled', False):
            # 被强行中止的 UI 逻辑
            self.lbl_status.setText("状态: 压制已强制中止 🚫")
            if self.enable_preview:
                self.lbl_preview.clear()
                self.lbl_preview.setText("任务已取消\n(画面预览结束)")
            print("====== 压制已被用户中止！======")
        else:
            # 正常顺利完成的 UI 逻辑
            self.lbl_status.setText("状态: 压制完成！ ✅")
            self.progress_bar.setValue(100) # 只有正常完成才强行拉满进度条
            if self.enable_preview:
                self.lbl_preview.clear()
                self.lbl_preview.setText("压制已完成\n(画面预览结束)")
            print("====== 压制彻底结束！======")
    
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
    

if __name__ == "__main__":
    init_config_files()
    app = QApplication(sys.argv)
    window = FFmpegGUI()
    window.show()
    sys.exit(app.exec())