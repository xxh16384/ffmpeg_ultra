import sys,os,tempfile
import subprocess,psutil
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QPushButton, QLabel, QLineEdit, 
                               QCheckBox, QProgressBar, QFileDialog, QMessageBox,QComboBox,
                               QTabWidget, QFormLayout, QProgressDialog,QSlider)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QCloseEvent
from PySide6.QtCore import Qt


def get_ext_path(executable_name):
    """
    终极寻路雷达：判断当前是开发环境还是单文件 exe 环境
    """
    if hasattr(sys, '_MEIPASS'):
        # 如果是被打包成了单文件 exe，去系统偷偷解压的临时目录里找
        return os.path.join(sys._MEIPASS, executable_name)
    else:
        # 如果是你在 VSCode/PyCharm 里直接运行，就在当前脚本所在目录找
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), executable_name)


class FFmpegWorker(QThread):
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, input_file, output_file, enable_preview, preview_path, encode_args): # === 新增 encode_args ===
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.enable_preview = enable_preview  
        self.preview_path = preview_path      
        self.encode_args = encode_args # === 保存传进来的动态参数 ===
        self.process = None 
        self.is_cancelled = False 

    def run(self):
        cmd = [get_ext_path("ffmpeg.exe"), "-y", "-i", self.input_file]
        cmd.extend(self.encode_args)
        cmd.append(self.output_file)

        if self.enable_preview:
            cmd.extend(["-vf", "fps=1", "-update", "1", self.preview_path])

        # === 新增：终极防沉默崩溃安全网 ===
        try:
            CREATE_NO_WINDOW = 0x08000000
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, encoding='utf-8', errors='ignore', creationflags=CREATE_NO_WINDOW
            )

            for line in self.process.stdout:
                self.log_signal.emit(line.strip())

            self.process.wait()
            if self.process.returncode != 0 and not self.is_cancelled:
                self.log_signal.emit("❌ FFmpeg 发生致命错误，请检查参数或视频格式！")
                return
            
            self.finished_signal.emit()
            
        except Exception as e:
            # 如果线程崩溃，强制调出底层追溯日志
            import traceback
            error_msg = traceback.format_exc()
            print(f"\n【💥后台致命崩溃报告】:\n{error_msg}\n")
            
            # 把遗言发给前台状态栏，防止界面卡死
            self.log_signal.emit(f"线程启动崩溃，详见控制台！错误: {e}")
            self.is_cancelled = True
            self.finished_signal.emit()

    def stop(self):
        """强制结束进程"""
        self.is_cancelled = True # === 新增：在强杀前，先打上取消标记 ===
        if self.process:
            try:
                p = psutil.Process(self.process.pid)
                for child in p.children(recursive=True):
                    child.kill()
                p.kill()
            except Exception:
                pass # 防止刚好进程自己结束时的底层报错

    def pause(self):
        """挂起进程 (路线 A)"""
        if self.process:
            psutil.Process(self.process.pid).suspend()

    def resume(self):
        """恢复进程 (路线 A)"""
        if self.process:
            psutil.Process(self.process.pid).resume()

class FFmpegGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        # 窗口基础设置
        self.setWindowTitle("xxh视频压制工具 v1.0")
        self.resize(850, 500) # 初始窗口大小
        # === 新增：在绘制界面前，先进行硬件自检 ===
        self.available_v_encoders = self.probe_hardware_encoders()
        # === 新增 2. 核心：根据自检结果，动态生成可用的标准化预设 ===
        self.load_dynamic_presets()

        # 核心 Widget 和 布局 (左右分栏布局)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget) 

        # ==================== 左侧控制区 ====================
        left_panel = QVBoxLayout()
        
        # 区域一：文件调度区
        left_panel.addWidget(QLabel("<b>📁 区域一：文件调度</b>"))
        self.btn_input = QPushButton("选择原视频")
        self.txt_input = QLineEdit()
        self.txt_input.setPlaceholderText("等待导入...")
        
        self.btn_output = QPushButton("设置导出路径")
        
        # === 新增：导出路径与格式下拉菜单的横向编队 ===
        output_layout = QHBoxLayout()
        self.txt_output = QLineEdit()
        self.txt_output.setPlaceholderText("等待设置...")
        
        self.cb_format = QComboBox()
        self.cb_format.addItems([".mp4", ".mkv", ".mov", ".flv", ".avi"])
        self.cb_format.setFixedWidth(75) # 固定宽度，小巧精致
        self.cb_format.setStyleSheet("font-weight: bold;") # 加粗显得更硬核
        
        # 把输入框和下拉菜单塞进同一行
        output_layout.addWidget(self.txt_output)
        output_layout.addWidget(self.cb_format)

        left_panel.addWidget(self.btn_input)
        left_panel.addWidget(self.txt_input)
        left_panel.addWidget(self.btn_output)
        left_panel.addLayout(output_layout) # 把组装好的横向布局放进左侧面板
        left_panel.addSpacing(20) # 留白增加呼吸感

        # === 区域二：压制策略 (全新重构的预设与折叠选项卡) ===
        left_panel.addWidget(QLabel("<b>⚙️ 区域二：压制策略</b>"))
        
        # === 修改 3. 预设下拉菜单：直接读取动态生成的键值名 ===
        self.combo_preset = QComboBox()
        # 把字典里的所有预设名字提取出来变成列表
        self.combo_preset.addItems(list(self.preset_configs.keys()))
        left_panel.addWidget(self.combo_preset)
        
        # 绑定下拉菜单切换事件，用来控制下方折叠面板的显示/隐藏
        self.combo_preset.currentTextChanged.connect(self.toggle_custom_tab)

        # 2. 全局画面预览开关 (保留原有设定)
        self.chk_preview = QCheckBox("开启实时画面预览")
        left_panel.addWidget(self.chk_preview)

        # 3. 高级自定义面板 (QTabWidget 选项卡流派)
        self.tab_custom = QTabWidget()
        self.tab_custom.setVisible(False) # 默认隐藏，保持界面清爽

        # --- 视频设置 Tab ---
        tab_video = QWidget()
        layout_video = QFormLayout(tab_video) # 使用表单布局，让参数对齐更规整
        self.cb_v_encoder = QComboBox();self.cb_v_encoder.addItems(self.available_v_encoders)
        self.cb_v_fps = QComboBox(); self.cb_v_fps.addItems(["保持源", "24", "30", "60"])
        self.cb_v_res = QComboBox(); self.cb_v_res.addItems(["保持源", "720p", "1080p","1440p","2160p"])
        
        # 1. 码率/质量控制模式
        self.cb_v_rc = QComboBox()
        self.cb_v_rc.addItems(["cqp", "vbr", "cbr"])
        # 2. 修改：创建滑块布局（滑块 + 数值实时预览）
        val_layout = QHBoxLayout()
        self.sld_v_value = QSlider(Qt.Horizontal)
        self.lbl_v_val_display = QLabel("32") # 初始显示 CQP 的默认值
        self.lbl_v_val_display.setFixedWidth(60)
        self.lbl_v_val_display.setStyleSheet("font-weight: bold; color: #225555;")
        val_layout.addWidget(self.sld_v_value)
        val_layout.addWidget(self.lbl_v_val_display)

        # 3. 绑定事件：模式切换时改滑块范围，滑块拖动时改显示数字
        self.cb_v_rc.currentTextChanged.connect(self.update_slider_range)
        self.sld_v_value.valueChanged.connect(self.update_slider_label)
        
        # 4. 初始化：手动触发一次范围设定（默认 CQP）
        self.update_slider_range("cqp")
        
        layout_video.addRow("编码器:", self.cb_v_encoder)
        layout_video.addRow("帧率(FPS):", self.cb_v_fps)
        layout_video.addRow("分辨率:", self.cb_v_res)
        layout_video.addRow("码率控制:", self.cb_v_rc)
        layout_video.addRow("参数数值:", val_layout)
        self.tab_custom.addTab(tab_video, "视频设置")
        
        # 编码器科普说明书
        encoder_tips = {
            # NVIDIA 阵营 (NVENC)
            "av1_nvenc": "【NVIDIA 40系+ 专享】目前最先进的硬件AV1编码器，极高压缩比，画质优秀。",
            "hevc_nvenc": "【NVIDIA 硬件加速】H.265编码。平衡了画质与文件体积，适合压制高清收藏。 ",
            "h264_nvenc": "【NVIDIA 硬件加速】H.264编码。兼容性之王，压制速度极快，适合快速出片。",
            
            # AMD 阵营 (AMF)
            "av1_amf": "【AMD 7000系+ 专享】AMD 硬件AV1方案。适合新一代显卡用户追求高效压缩。",
            "hevc_amf": "【AMD 硬件加速】HEVC编码。AMD核显或独显用户压制高码率视频的首选。",
            "h264_amf": "【AMD 硬件加速】H.264编码。极致的编码速度，适合对兼容性要求高的普通视频。",
            
            # Intel 阵营 (QSV)
            "av1_qsv": "【Intel Arc/新酷睿专享】Intel QSV 硬件AV1编码。效率极高，多媒体性能强劲。",
            "hevc_qsv": "【Intel 硬件加速】HEVC编码。Intel核显用户压制高画质视频的低功耗方案。",
            "h264_qsv": "【Intel 硬件加速】H.264编码。广泛应用于流媒体，性能稳定且兼容性好。",
            
            # CPU 软压阵营 (Software)
            "libsvtav1": "【纯 CPU 软压】由 Intel/Netflix 开发。虽然压制极慢，但同体积下画质是目前的神话。",
            "libx265": "【纯 CPU 软压】HEVC 标准压制。适合电影、纪录片深度压制，追求极致画质细节。",
            "libx264": "【纯 CPU 软压】最稳、最慢、最清晰的H.264方案。不依赖显卡，不挑驱动。",
            
            # 特殊模式
            "copy": "【流复制模式】不进行任何重新编码。仅更换封装容器，速度取决于磁盘，画质0损失。"
        }
        self.set_combo_tooltips(self.cb_v_encoder, encoder_tips)
        preset_tips = {
            "会议录屏极致瘦身 (AV1, 30帧, CQP)": "采用最新的 AV1 编码，适合录制幻灯片，文件体积缩小 50% 以上。",
            "高画质收藏版 (HEVC/H.265, VBR)": "兼顾画质与兼容性，适合存储 1080p/4K 电影，支持硬件加速。",
            "老设备高兼容版 (H.264, CBR)": "最传统的格式，几乎能在任何破旧的播放器或电视上流畅运行。",
            "⚙️ 自定义参数...": "进入极客模式，手动微调每一项硬核压制参数。"
        }
        self.set_combo_tooltips(self.combo_preset, preset_tips)
        rc_tips = {
            "cqp": (
                "<b>[ 质量恒定模式 ]</b><br>"
                "固定每一帧的压缩倍率。不限制码率，只保证画面清晰度。<br>"
                "<b>数值意义：</b>0 为无损（文件巨大），51 为极模糊。<br>"
                "<b>建议范围：</b>18 - 28。数值越小，画质越好，体积越大。"
            ),
            "vbr": (
                "<b>[ 动态码率模式 ]</b><br>"
                "根据画面复杂度分配码率。复杂画面多给点，静止画面少给点。<br>"
                "<b>数值意义：</b>设置的是‘目标平均码率’。<br>"
                "<b>适用场景：</b>本地收藏、视频发布。是兼顾体积与画质的最佳平衡方案。"
            ),
            "cbr": (
                "<b>[ 固定码率模式 ]</b><br>"
                "全程保持恒定的传输速率，不顾画面复杂度，强行填充码率。<br>"
                "<b>数值意义：</b>设置的是‘固定传输速率’。<br>"
                "<b>适用场景：</b>直播推流、老式硬件播放。缺点是简单画面浪费空间，复杂画面可能模糊。"
            )
        }
        self.set_combo_tooltips(self.cb_v_rc, rc_tips)

        # --- 音频设置 Tab ---
        tab_audio = QWidget()
        layout_audio = QFormLayout(tab_audio)
        self.cb_a_encoder = QComboBox(); self.cb_a_encoder.addItems(["aac", "mp3", "copy", "an (剥离静音)"])
        self.cb_a_bitrate = QComboBox(); self.cb_a_bitrate.addItems(["320k", "192k", "128k"])
        self.cb_a_sample = QComboBox(); self.cb_a_sample.addItems(["保持源", "44100", "48000"])
        
        layout_audio.addRow("编码器:", self.cb_a_encoder)
        layout_audio.addRow("码率:", self.cb_a_bitrate)
        layout_audio.addRow("采样率:", self.cb_a_sample)
        self.tab_custom.addTab(tab_audio, "音频设置")

        left_panel.addWidget(self.tab_custom)
        left_panel.addStretch() # 把底部的按钮顶下去
        # ====================================================
        
        # 开始按钮 (加大加粗)
        self.btn_start = QPushButton("🚀 开始压制")
        self.btn_start.setMinimumHeight(45)
        self.btn_start.setStyleSheet("font-weight: bold; font-size: 14px;")
        left_panel.addWidget(self.btn_start)

        # ==================== 右侧监控区 ====================
        right_panel = QVBoxLayout()

        # 区域三：实时监控屏
        right_panel.addWidget(QLabel("<b>📺 区域三：实时监控屏</b>"))
        self.lbl_preview = QLabel("画面预览区\n(等待压制开始...)")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        # 用深色背景模拟监视器质感
        self.lbl_preview.setStyleSheet("background-color: #1e1e1e; color: #888888; border-radius: 8px; font-size: 16px;")
        self.lbl_preview.setMinimumSize(480, 270) # 维持 16:9 比例
        right_panel.addWidget(self.lbl_preview)
        right_panel.addSpacing(10)

        # 区域四：进度与日志仪表盘
        right_panel.addWidget(QLabel("<b>📊 区域四：运行状态</b>"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        right_panel.addWidget(self.progress_bar)
        
        self.lbl_status = QLabel("状态: 闲置 | 速度: -- | 剩余时间: --")
        self.lbl_status.setStyleSheet("color: #666666;")
        right_panel.addWidget(self.lbl_status)

        # 将左右面板按比例加入主窗口 (左1 : 右2)
        main_layout.addLayout(left_panel, 1) 
        main_layout.addLayout(right_panel, 2) 
        
        # 按钮横向排版
        btn_layout = QHBoxLayout()
        self.btn_pause = QPushButton("⏸ 暂停")
        self.btn_stop = QPushButton("⏹ 停止")
        
        self.btn_pause.setEnabled(False) # 初始不可用
        self.btn_stop.setEnabled(False)  # 初始不可用
        
        btn_layout.addWidget(self.btn_pause)
        btn_layout.addWidget(self.btn_stop)
        left_panel.addLayout(btn_layout)

        # 绑定点击事件
        self.btn_pause.clicked.connect(self.toggle_pause)
        self.btn_stop.clicked.connect(self.stop_encoding)
        
        # 绑定按钮的点击事件
        self.btn_start.clicked.connect(self.start_encoding)
        self.btn_input.clicked.connect(self.select_input_file)   # 新增：绑定导入按钮
        self.btn_output.clicked.connect(self.select_output_file) # 新增：绑定导出按钮
        # 绑定格式下拉菜单的切换事件
        self.cb_format.currentTextChanged.connect(self.change_output_extension)
    
    def update_slider_range(self, mode):
        """根据选择的 RC 模式，动态调整滑块的最小值、最大值和当前值"""
        if mode == "cqp":
            # CQP 范围：0 (无损) 到 51 (极差)，越小画质越好
            self.sld_v_value.setRange(0, 51)
            self.sld_v_value.setValue(32) # 给个主流默认值
        else:
            # CBR/VBR 范围：200k 到 30000k (单位：k)
            # 我们让滑块的 1 个刻度代表 100k
            self.sld_v_value.setRange(200, 30000)
            self.sld_v_value.setSingleStep(100)
            self.sld_v_value.setValue(5000) # 默认 5Mbps
        
        self.update_slider_label()

    def update_slider_label(self):
        """实时更新滑块旁边的文字显示"""
        val = self.sld_v_value.value()
        mode = self.cb_v_rc.currentText()
        if mode == "cqp":
            self.lbl_v_val_display.setText(str(val))
        else:
            # VBR/CBR 显示带单位的码率
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
        # 这个字典用来保存最终能够在界面上显示的可用预设，以及它们对应的最终参数
        self.preset_configs = {}

        # =====================================================================
        # ⬇️ 以后自己加预设，只需要在这里按格式添加即可！ ⬇️
        # requires: 只要探针探测到的真实编码器名字里包含这个词，该预设就会被激活
        # {encoder}: 占位符，代码会自动把它替换成你电脑里真正能用的那个加速器
        # =====================================================================
        raw_presets = [
            {
                "name": "会议录屏极致瘦身 (AV1, 30帧, CQP)",
                "requires": "av1",  
                "args": ["-r", "30", "-c:v", "{encoder}", "-rc", "cqp", "-qp_i", "32", "-qp_p", "32", "-c:a", "aac", "-b:a", "128k"]
            },
            {
                "name": "高画质收藏版 (HEVC/H.265, VBR)",
                "requires": "hevc", 
                "args": ["-c:v", "{encoder}", "-rc", "vbr", "-b:v", "5000k", "-c:a", "aac", "-b:a", "320k"]
            },
            {
                "name": "老设备高兼容版 (H.264, CBR)",
                "requires": "264",  # 兼容 h264 或 264
                "args": ["-c:v", "{encoder}", "-rc", "cbr", "-b:v", "2000k", "-c:a", "aac", "-b:a", "192k"]
            }
        ]

        # 核心匹配逻辑：让预设去寻找对应的真实硬件
        for p in raw_presets:
            # 在探针给出的清单中，寻找第一个包含 requires 关键词的编码器
            # （因为探针里硬件加速排在前面，所以它会优先匹配到 amf/nvenc/qsv）
            matched_encoder = next((enc for enc in self.available_v_encoders if p["requires"] in enc), None)
            
            if matched_encoder:
                # 如果找到了硬件，就把参数模板里的 {encoder} 替换成真实的硬件名字
                final_args = [arg.replace("{encoder}", matched_encoder) for arg in p["args"]]
                # 存入最终可用的字典中
                self.preset_configs[p["name"]] = final_args

        # 永远在列表最后保留“自定义”选项
        self.preset_configs["⚙️ 自定义参数..."] = []
        
    
    def probe_video_info(self, file_path):
        import json # 局部引入，保持顶部代码整洁
        import subprocess
        
        # 呼叫 ffprobe，要求它以规整的 JSON 格式吐出所有底层流信息
        cmd = [
            get_ext_path("ffprobe.exe"), "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", file_path
        ]
        
        try:
            CREATE_NO_WINDOW = 0x08000000
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=CREATE_NO_WINDOW)
            data = json.loads(result.stdout)
            
            # 提取视频流 (排除音频和字幕流)
            video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
            if not video_stream:
                return "❌ 未能识别到有效的视频流"

            codec = video_stream.get('codec_name', 'UNKNOWN').upper()
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            
            # 精确帧率计算 (ffprobe 输出的通常是 60000/1001 这种除法格式)
            fps_str = video_stream.get('r_frame_rate', '0/0')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = round(int(num) / int(den), 2) if int(den) != 0 else 0
            else:
                fps = float(fps_str)
                
            # 整体码率提取 (转换为更易读的 Mbps)
            bitrate_bps = data.get('format', {}).get('bit_rate') or video_stream.get('bit_rate')
            if bitrate_bps:
                bitrate_display = f"{round(int(bitrate_bps) / 1000000, 2)} Mbps"
            else:
                bitrate_display = "动态/未知"

            # 组装极客风格的终端面板文本
            return (
                f"=== 源视频信息 ===\n\n"
                f"[ 编码 ] {codec}\n"
                f"[ 分辨率 ] {width} x {height}\n"
                f"[ 帧率 ] {fps} FPS\n"
                f"[ 码率 ] {bitrate_display}"
            )
            
        except Exception as e:
            return f"❌ 探针读取失败: {e}"
    
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
        preset = self.combo_preset.currentText()
        
        # 1. 预设逻辑：直接从动态生成的配置字典中获取参数
        if preset != "⚙️ 自定义参数...":
            return self.preset_configs.get(preset, []).copy()

        # 2. 自定义参数逻辑：深度适配厂商差异并接入滑块数值
        args = []
        v_enc = self.cb_v_encoder.currentText()
        is_nvenc = "nvenc" in v_enc
        is_amf = "amf" in v_enc

        # --- 视频编码部分 ---
        if v_enc == "copy":
            args.extend(["-c:v", "copy"])
        else:
            args.extend(["-c:v", v_enc])
            
            # 帧率处理
            fps = self.cb_v_fps.currentText()
            if fps != "保持源": 
                args.extend(["-r", fps])
            
            # 分辨率处理 (保持 scale 滤镜逻辑)
            res = self.cb_v_res.currentText()
            if res == "1080p": args.extend(["-vf", "scale=-1:1080"])
            elif res == "720p": args.extend(["-vf", "scale=-1:720"])
            elif res == "2160p": args.extend(["-vf", "scale=-1:2160"])
            elif res == "1440p": args.extend(["-vf", "scale=-1:1440"])
                
            # --- 码率控制适配 (接入滑块逻辑) ---
            rc_mode = self.cb_v_rc.currentText()
            # 从滑块直接获取整数值，避免了手动输入的格式错误
            val_int = self.sld_v_value.value() 
            
            if rc_mode == "cqp":
                val = str(val_int)
                if is_nvenc:
                    # NVIDIA 专用：必须用 constqp 和 -qp，它不识别 AMD 的参数名
                    args.extend(["-rc", "constqp", "-qp", val])
                elif is_amf:
                    # AMD 专用：使用 cqp 模式并同步设置 i/p 帧质量
                    args.extend(["-rc", "cqp", "-qp_i", val, "-qp_p", val])
                else:
                    # 其它编码器 (如 CPU 软解) 的通用 CQP 参数
                    args.extend(["-cqp", val])
                    
            elif rc_mode == "vbr":
                # 滑块数值在 VBR 模式下代表 kbps，自动补齐 'k' 单位
                val = f"{val_int}k"
                if is_nvenc:
                    # NVIDIA 开启 VBR 时，建议同时限制 maxrate 以保证码率控制的严谨性
                    args.extend(["-rc", "vbr", "-b:v", val, "-maxrate:v", val, "-bufsize:v", val])
                else:
                    args.extend(["-rc", "vbr", "-b:v", val])
                    
            elif rc_mode == "cbr":
                val = f"{val_int}k"
                # CBR 模式通常在硬件编码器中支持较好
                args.extend(["-rc", "cbr", "-b:v", val])

        # --- 音频部分 (保留已确认的逻辑) ---
        a_enc = self.cb_a_encoder.currentText()
        if "剥离静音" in a_enc: 
            args.extend(["-an"])
        elif a_enc == "copy": 
            args.extend(["-c:a", "copy"])
        else:
            args.extend(["-c:a", a_enc])
            # 音频码率处理
            ab = self.cb_a_bitrate.currentText()
            args.extend(["-b:a", ab])
            # 采样率处理
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
        self.total_seconds = self.get_video_duration(input_path)
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
        # 1. 使用正则表达式狙击“当前时间”和“压制速度”
        # 匹配格式如 time=01:14:58.85
        time_match = re.search(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", text)
        # 匹配格式如 speed=12.9x
        speed_match = re.search(r"speed=\s*([\d\.]+)x", text)

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

            # 5. 更新状态栏面板
            speed_text = speed_match.group(1) if speed_match else "--"
            self.lbl_status.setText(f"状态: 狂飙压制中... | 速度: {speed_text}x | 当前进度: {time_str}")
        
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
        
    def get_video_duration(self, file_path):
        # 组装探针命令：只输出格式的时长，去掉所有多余的包装文本
        cmd = [
            "ffprobe", "-v", "error", 
            "-show_entries", "format=duration", 
            "-of", "default=noprint_wrappers=1:nokey=1", 
            file_path
        ]
        # 同样使用隐形窗口参数，防止弹出黑框
        CREATE_NO_WINDOW = 0x08000000
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=CREATE_NO_WINDOW)
            return float(result.stdout.strip())
        except Exception as e:
            print(f"探针读取失败: {e}")
            return 1  # 遇到极端错误时返回1，防止后续进度条计算时出现“除以0”的崩溃
    
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
            info_text = self.probe_video_info(file_path)
            self.lbl_preview.setText(info_text)

    def select_output_file(self):
        # 呼出 Windows 原生保存框
        file_path, _ = QFileDialog.getSaveFileName(self, "设置导出路径", self.txt_output.text(), "视频文件 (*.mp4)")
        if file_path:
            self.txt_output.setText(file_path)
    
    def toggle_custom_tab(self, text):
        # 只有当用户选中带有“自定义”字样的选项时，才展开下方的参数面板
        if "自定义" in text:
            self.tab_custom.setVisible(True)
        else:
            self.tab_custom.setVisible(False)
    
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
    app = QApplication(sys.argv)
    window = FFmpegGUI()
    window.show()
    sys.exit(app.exec())