import json
import subprocess
from core.utils import get_ext_path

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