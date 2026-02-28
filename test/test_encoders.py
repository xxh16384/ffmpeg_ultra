import sys
import os
import subprocess

# 把项目根目录加入系统路径，确保能导入 main 和 core
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from PySide6.QtWidgets import QApplication
from main import FFmpegGUI
from core.utils import get_ext_path

def run_bulletproof_test():
    app = QApplication(sys.argv)
    print("🚀 正在后台挂载 GUI 实例，提取参数翻译逻辑...")
    gui = FFmpegGUI()
    ffmpeg_path = get_ext_path("ffmpeg.exe")

    # ==========================================
    # 1. 制造真正的物理测试文件，防止虚拟流报错逃逸
    # ==========================================
    source_vid = "test_source_real.mp4"
    if not os.path.exists(source_vid):
        print("🎬 正在生成物理测试片源...")
        CREATE_NO_WINDOW = 0x08000000
        subprocess.run([
            ffmpeg_path, "-y", "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
            "-c:v", "libx264", "-preset", "ultrafast", source_vid
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)

    encoders = gui.available_v_encoders
    modes = ["cqp", "vbr", "cbr"]
    report = {}

    print(f"\n🎯 准备开始 {len(encoders)} x 3 真实物理撞库测试...\n")
    
    gui.combo_preset.setCurrentText("⚙️ 自定义参数...")

    # ==========================================
    # 2. 严苛轰炸测试
    # ==========================================
    for enc in encoders:
        if enc == "copy": 
            continue
            
        report[enc] = {}
        gui.cb_v_encoder.setCurrentText(enc)

        for mode in modes:
            print(f"[{enc} + {mode:<3}] 测试中...", end="", flush=True)
            gui.cb_v_rc.setCurrentText(mode)

            # 触发翻译逻辑
            args = gui.build_ffmpeg_args()
            test_out = "test_out_temp.mp4"
            cmd = [ffmpeg_path, "-y", "-i", source_vid] + args + [test_out]

            try:
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, # 把 stderr 重定向到 stdout 一起读取
                    text=True, encoding='utf-8', errors='ignore', creationflags=CREATE_NO_WINDOW, timeout=8
                )
                
                output_log = result.stdout.lower()
                
                # ✨ 核心改进：只要日志里有“未识别的选项”或“错误”，或者返回码非零，统统按崩溃处理！
                if result.returncode != 0 or "unrecognized option" in output_log or "error splitting" in output_log or "conversion failed" in output_log:
                    print(" ❌ 崩溃")
                    report[enc][mode] = "❌"
                    # 抓取最后一行有用的报错
                    lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                    # 倒序查找最像报错的那一行
                    err_msg = lines[-1] if lines else "未知错误，无输出"
                    for line in reversed(lines):
                        if "error" in line.lower() or "unrecognized option" in line.lower():
                            err_msg = line
                            break
                    report[enc][f"{mode}_err"] = err_msg
                else:
                    print(" ✅ 完美通过")
                    report[enc][mode] = "✅"
                    
            except subprocess.TimeoutExpired:
                print(" ⚠️ 超时")
                report[enc][mode] = "⚠️ (超时卡死)"
            except Exception as e:
                print(f" ⚠️ 异常: {e}")
                report[enc][mode] = f"⚠️ ({e})"

    # ==========================================
    # 3. 打印华丽的测试报告
    # ==========================================
    print("\n" + "="*65)
    print("📊 FFmpeg 翻译逻辑扫雷报告 (物理版)")
    print("="*65)
    print(f"{'编码器引擎':<15} | {'CQP':<6} | {'VBR':<6} | {'CBR':<6}")
    print("-" * 60)
    for enc, results in report.items():
        cqp = results.get("cqp", "-")
        vbr = results.get("vbr", "-")
        cbr = results.get("cbr", "-")
        print(f"{enc:<15} | {cqp:<6} | {vbr:<6} | {cbr:<6}")

    print("\n💥 崩溃详情精准诊断:")
    has_error = False
    for enc, results in report.items():
        for mode in modes:
            if results.get(mode) == "❌":
                has_error = True
                print(f"[{enc} + {mode.upper()}] 致命报错 -> {results.get(f'{mode}_err')}")
                
    if not has_error:
        print("🎉 恭喜！当前翻译逻辑无懈可击，全部真实压制通过！")

    # ==========================================
    # 4. 打扫战场
    # ==========================================
    for file in [source_vid, "test_out_temp.mp4"]:
        if os.path.exists(file):
            try: os.remove(file)
            except: pass
            
    sys.exit(0)

if __name__ == "__main__":
    run_bulletproof_test()