import json
import subprocess
from core.utils import get_ext_path

def build_ffmpeg_args(config):
    """
    纯净的参数翻译引擎：不再依赖任何 UI 控件，只负责把字典翻译成命令行
    :param config: 包含所有 UI 状态的字典
    """
    args = []
    v_enc = config["v_enc"]
    is_nvenc = "nvenc" in v_enc
    is_amf = "amf" in v_enc
    is_qsv = "qsv" in v_enc
    is_cpu = "lib" in v_enc

    # --- 视频编码部分 ---
    if v_enc == "copy":
        args.extend(["-c:v", "copy"])
    else:
        args.extend(["-c:v", v_enc])
        
        # NVIDIA / AMD 硬件 H264 的护城河
        if v_enc in ["h264_nvenc", "h264_amf"]:
            args.extend(["-pix_fmt", "yuv420p", "-profile:v", "high"])
        
        # 帧率处理
        fps = config["fps"]
        if fps != "保持源": 
            args.extend(["-r", fps])
        
        # 分辨率处理
        res = config["res"]
        if res == "1080p": args.extend(["-vf", "scale=-1:1080"])
        elif res == "720p": args.extend(["-vf", "scale=-1:720"])
        elif res == "2160p": args.extend(["-vf", "scale=-1:2160"])
        elif res == "1440p": args.extend(["-vf", "scale=-1:1440"])
            
        # --- 码率控制适配 ---
        rc = config["rc"]
        
        if rc == "cqp":
            val = str(config["cqp_val"]) 
            if is_nvenc:
                args.extend(["-rc", "vbr", "-cq", val, "-b:v", "0"])
            elif is_amf:
                args.extend(["-rc", "cqp", "-qp_i", val, "-qp_p", val])
            elif is_qsv:
                args.extend(["-global_quality", val])
            else:
                args.extend(["-crf", val])
                
        elif rc == "vbr":
            val = f"{config['vbr_cbr_val']}k"
            if is_nvenc:
                args.extend(["-rc", "vbr", "-b:v", val, "-maxrate:v", val, "-bufsize:v", val])
            elif is_amf:
                args.extend(["-rc", "vbr_peak", "-b:v", val])
            else:
                args.extend(["-b:v", val])
                
        elif rc == "cbr":
            val = f"{config['vbr_cbr_val']}k"
            if is_nvenc:
                args.extend(["-rc", "cbr", "-b:v", val, "-maxrate:v", val, "-bufsize:v", val])
            elif is_amf:
                args.extend(["-rc", "cbr", "-b:v", val])
            else:
                args.extend(["-b:v", val, "-maxrate:v", val, "-bufsize:v", val])

    # --- 音频部分 ---
    a_enc = config["a_enc"]
    if "剥离静音" in a_enc: 
        args.extend(["-an"])
    elif a_enc == "copy": 
        args.extend(["-c:a", "copy"])
    else:
        args.extend(["-c:a", a_enc])
        ab = config["a_bit"]
        args.extend(["-b:a", ab])
        ar = config["a_sample"]
        if ar != "保持源": 
            args.extend(["-ar", ar])

    return args

def get_video_duration(file_path):
    cmd = [
        get_ext_path("ffprobe.exe"), "-v", "error", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        file_path
    ]
    CREATE_NO_WINDOW = 0x08000000
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=CREATE_NO_WINDOW)
        return float(result.stdout.strip())
    except Exception as e:
        print(f"探针读取失败: {e}")
        return 1

def probe_video_info(file_path):
    cmd = [
        get_ext_path("ffprobe.exe"), "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path
    ]
    try:
        CREATE_NO_WINDOW = 0x08000000
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', creationflags=CREATE_NO_WINDOW)
        data = json.loads(result.stdout)
        
        video_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
        if not video_stream:
            return "❌ 未能识别到有效的视频流"

        codec = video_stream.get('codec_name', 'UNKNOWN').upper()
        width = video_stream.get('width', 0)
        height = video_stream.get('height', 0)
        
        
        fps_str = video_stream.get('r_frame_rate', '0/0')
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = round(int(num) / int(den), 2) if int(den) != 0 else 0
        else:
            fps = float(fps_str)
            
        bitrate_bps = data.get('format', {}).get('bit_rate') or video_stream.get('bit_rate')
        if bitrate_bps:
            bitrate_display = f"{round(int(bitrate_bps) / 1000000, 2)} Mbps"
        else:
            bitrate_display = "动态/未知"
        
        audio_stream = next((s for s in data.get('streams', []) if s.get('codec_type') == 'audio'), None)
        if audio_stream:
            audio_codec = audio_stream.get('codec_name', 'UNKNOWN').upper()
            audio_codec_text = f"{audio_codec}"
            audio_sample_rate = audio_stream.get('sample_rate', '未知')
            audio_sample_text = f" {audio_sample_rate} Hz"
            audio_bitrate_bps = audio_stream.get('bit_rate')
            if audio_bitrate_bps:
                audio_bitrate_text = f"{round(int(audio_bitrate_bps) / 1000, 2)} Kbps"

        return (
            f"视频|音频 信息\n\n"
            f"[ 编码 ] {codec}|{audio_codec_text}\n"
            f"[ 分辨率 ] {width} x {height}\n"
            f"[ 帧率|采样率 ] {fps} FPS|{audio_sample_text}\n"
            f"[ 码率 ] {bitrate_display}|{audio_bitrate_text}"
        )
    except Exception as e:
        return f"❌ 探针读取失败: {e}"

def check_single_encoder(enc):
    """
    独立硬件点火器：无情地测试指定的单一编码器是否可用。
    没有任何 UI 逻辑，只返回 (是否成功, 错误信息摘要)
    """
    import subprocess
    from core.utils import get_ext_path
    
    cmd = [
        get_ext_path("ffmpeg.exe"), "-y", 
        "-f", "lavfi", "-i", "color=c=black:s=320x240", 
        "-vframes", "1", 
        "-c:v", enc, 
        "-pix_fmt", "yuv420p", 
        "-f", "null", "-"
    ]
    
    CREATE_NO_WINDOW = 0x08000000
    try:
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
            return True, ""
        else:
            return False, result.stderr[-100:]
    except Exception as e:
        return False, str(e)