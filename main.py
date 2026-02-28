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

from core.utils import get_ext_path
from core.worker import FFmpegWorker
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

        # ==========================================
        # 3. 逐字保留：原汁原味的科普说明书
        # ==========================================
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
        is_qsv = "qsv" in v_enc
        
        # --- 视频编码部分 ---
        if v_enc == "copy":
            args.extend(["-c:v", "copy"])
        else:
            args.extend(["-c:v", v_enc])

            # ✨ 核心修复 1：H264 硬件编码器的护城河
            # 强制所有进入 H264 硬件的视频统一转换为标准的 8-bit yuv420p 格式并锁定 high 规格
            # 这能解决 99% 的 h264_nvenc 和 h264_amf 突然暴毙的问题
            if v_enc in ["h264_nvenc", "h264_amf"]:
                args.extend(["-pix_fmt", "yuv420p", "-profile:v", "high"])
            
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
                
            # --- 码率控制适配 (彻底扫清厂商方言壁垒) ---
            rc_mode = self.cb_v_rc.currentText()
            val_int = self.sld_v_value.value() 
            
            if rc_mode == "cqp":
                val = str(val_int)
                if is_nvenc:
                    # ✨ 核心修复 2：NVENC 真正的“恒定画质”最佳实践
                    # 用 vbr 模式挂载 0 码率，配合 -cq 控制，彻底抛弃不稳定的 constqp
                    args.extend(["-rc", "vbr", "-cq", val, "-b:v", "0"])
                elif is_amf:
                    args.extend(["-rc", "cqp", "-qp_i", val, "-qp_p", val])
                elif is_qsv:
                    args.extend(["-global_quality", val]) # Intel 的恒定质量方言
                else:
                    # 纯 CPU (libx264/x265/svtav1) 必须用 -crf
                    args.extend(["-crf", val]) 
                    
            elif rc_mode == "vbr":
                val = f"{val_int}k"
                if is_nvenc:
                    args.extend(["-rc", "vbr", "-b:v", val, "-maxrate:v", val, "-bufsize:v", val])
                elif is_amf:
                    # AMD 的 VBR 方言叫 vbr_peak
                    args.extend(["-rc", "vbr_peak", "-b:v", val])
                else:
                    # CPU 和通用的 VBR 写法
                    args.extend(["-b:v", val])
                    
            elif rc_mode == "cbr":
                val = f"{val_int}k"
                if is_nvenc:
                    args.extend(["-rc", "cbr", "-b:v", val, "-maxrate:v", val, "-bufsize:v", val])
                elif is_amf:
                    args.extend(["-rc", "cbr", "-b:v", val])
                else:
                    # CPU 强行 CBR 的标准做法是锁死 maxrate 和 bufsize
                    args.extend(["-b:v", val, "-maxrate:v", val, "-bufsize:v", val])

        # --- 音频部分 (完全保留原有逻辑) ---
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
        #print(text) #调试时直接往控制台输出
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