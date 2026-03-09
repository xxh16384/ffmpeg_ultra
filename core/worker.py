import subprocess, psutil
from PySide6.QtCore import QThread, Signal
from core.utils import get_ext_path

class FFmpegWorker(QThread):
    log_signal = Signal(str)
    error_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, input_file, output_file, enable_preview, preview_port, encode_args): 
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.enable_preview = enable_preview  
        self.preview_port = preview_port      
        self.encode_args = encode_args 
        self.process = None 
        self.is_cancelled = False 

    def run(self):
        cmd = [get_ext_path("ffmpeg.exe"), "-y", "-i", self.input_file]
        cmd.extend(self.encode_args)
        cmd.append(self.output_file)

        if self.enable_preview:
            # 采用 tcp 本地回环进行内存管道传输，mjpeg 格式，1 FPS
            cmd.extend([
                "-f", "image2pipe", 
                "-vcodec", "mjpeg", 
                "-r", "1", 
                f"tcp://127.0.0.1:{self.preview_port}"
            ])
            
        # ====== 新增：增加-progress获取规整进度======
        cmd.extend(["-progress", "-", "-nostats"])

        try:
            CREATE_NO_WINDOW = 0x08000000
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                text=True, encoding='utf-8', errors='ignore', creationflags=CREATE_NO_WINDOW
            )

            error_lines = []
            for line in self.process.stdout:
                line_str = line.strip()
                self.log_signal.emit(line_str)
                # 简单缓存最后10行用于报警
                if len(error_lines) > 10:
                    error_lines.pop(0)
                error_lines.append(line_str)

            self.process.stdout.close()
            self.process.wait()
            
            if self.process.returncode != 0 and not self.is_cancelled:
                err_summary = "\n".join(error_lines)
                self.error_signal.emit(f"❌ FFmpeg 发生致命错误 (Exit {self.process.returncode})\n\n{err_summary}")
                # 注意：发生错误时，不仅要 error，还要最终 emit finished 以清理状态
                
            self.finished_signal.emit()
            
        except Exception as e:
            import traceback
            error_msg = traceback.format_exc()
            print(f"\n【💥后台致命崩溃报告】:\n{error_msg}\n")
            
            self.log_signal.emit(f"线程启动崩溃，详见控制台！错误: {e}")
            self.is_cancelled = True
            self.finished_signal.emit()

    def stop(self):
        """强制结束进程"""
        self.is_cancelled = True 
        if self.process:
            try:
                p = psutil.Process(self.process.pid)
                for child in p.children(recursive=True):
                    child.kill()
                p.kill()
            except Exception:
                pass 

    def pause(self):
        """挂起进程 (路线 A)"""
        if self.process:
            psutil.Process(self.process.pid).suspend()

    def resume(self):
        """恢复进程 (路线 A)"""
        if self.process:
            psutil.Process(self.process.pid).resume()