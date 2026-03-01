import sys, os

def get_ext_path(executable_name):
    """
    终极寻路雷达：判断当前是开发环境还是单文件 exe 环境
    """
    if hasattr(sys, '_MEIPASS'):
        # ✨ 核心修复：打包命令用的是 ";."，引擎被释放在了临时目录的最外层根目录。
        # 所以这里去掉了 "tools" 这一层！
        return os.path.join(sys._MEIPASS, executable_name)
    else:
        # 开发环境下（源码运行）：获取项目根目录并进入 tools 文件夹
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_dir, "tools", executable_name)
    
def get_app_dir():
    """
    外部物理路径雷达：获取程序真正运行的物理目录
    """
    import sys, os
    if getattr(sys, 'frozen', False):
        # 如果是被打包成了 exe，返回 exe 所在的真实目录
        return os.path.dirname(sys.executable)
    else:
        # ✨ 核心修复：抛弃 __file__，改用 sys.argv[0]
        # sys.argv[0] 永远指向你启动程序的那个入口文件（也就是 main.py）
        # 这样无论这个函数被移到哪个深层文件夹，它都能精准咬死项目根目录！
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def init_config_files():
    """初始化配置文件：如果不存在，则自动生成默认配置"""
    import os
    app_dir = get_app_dir()
    config_dir = os.path.join(app_dir, "config")
    
    # 如果 config 文件夹不存在，建一个
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        
    presets_path = os.path.join(config_dir, "presets.yaml")
    tooltips_path = os.path.join(config_dir, "tooltips.yaml")
    
    # ==========================================
    # 1. 自动生成预设文件
    # ==========================================
    if not os.path.exists(presets_path):
        default_presets = """presets:
  - name: "会议录屏极致瘦身 (AV1, 30帧, CQP)"
    requires: "av1"
    ui_state:
      fps: "30"
      res: "保持源"
      rc: "cqp"
      val: 32
      a_enc: "aac"
      a_bit: "128k"
      a_sample: "保持源"

  - name: "高画质收藏版 (HEVC/H.265, VBR)"
    requires: "hevc"
    ui_state:
      fps: "保持源"
      res: "保持源"
      rc: "vbr"
      val: 5000
      a_enc: "aac"
      a_bit: "320k"
      a_sample: "保持源"

  - name: "老设备高兼容版 (H.264, CBR)"
    requires: "264"
    ui_state:
      fps: "保持源"
      res: "保持源"
      rc: "cbr"
      val: 2000
      a_enc: "aac"
      a_bit: "192k"
      a_sample: "保持源"

  - name: "压片战争最小视频 (HEVC/H.265, VBR)"
    requires: "x265"
    ui_state:
      fps: "24"
      res: "720p"
      rc: "vbr"
      val: 100
      a_enc: "aac"
      a_bit: "64k"
      a_sample: "保持源"
"""
        with open(presets_path, 'w', encoding='utf-8') as f:
            f.write(default_presets)
            print("✨ 已自动生成默认 presets.yaml")

    # ==========================================
    # 2. 自动生成科普提示文件
    # ==========================================
    if not os.path.exists(tooltips_path):
        default_tooltips = """encoder_tips:
  av1_nvenc: "【NVIDIA 40系+ 专享】目前最先进的硬件AV1编码器，极高压缩比，画质优秀。"
  hevc_nvenc: "【NVIDIA 硬件加速】H.265编码。平衡了画质与文件体积，适合压制高清收藏。 "
  h264_nvenc: "【NVIDIA 硬件加速】H.264编码。兼容性之王，压制速度极快，适合快速出片。"
  av1_amf: "【AMD 7000系+ 专享】AMD 硬件AV1方案。适合新一代显卡用户追求高效压缩。"
  hevc_amf: "【AMD 硬件加速】HEVC编码。AMD核显或独显用户压制高码率视频的首选。"
  h264_amf: "【AMD 硬件加速】H.264编码。极致的编码速度，适合对兼容性要求高的普通视频。"
  av1_qsv: "【Intel Arc/新酷睿专享】Intel QSV 硬件AV1编码。效率极高，多媒体性能强劲。"
  hevc_qsv: "【Intel 硬件加速】HEVC编码。Intel核显用户压制高画质视频的低功耗方案。"
  h264_qsv: "【Intel 硬件加速】H.264编码。广泛应用于流媒体，性能稳定且兼容性好。"
  libsvtav1: "【纯 CPU 软压】由 Intel/Netflix 开发。虽然压制极慢，但同体积下画质是目前的神话。"
  libx265: "【纯 CPU 软压】HEVC 标准压制。适合电影、纪录片深度压制，追求极致画质细节。"
  libx264: "【纯 CPU 软压】最稳、最慢、最清晰的H.264方案。不依赖显卡，不挑驱动。"
  copy: "【流复制模式】不进行任何重新编码。仅更换封装容器，速度取决于磁盘，画质0损失。"

preset_tips:
  "会议录屏极致瘦身 (AV1, 30帧, CQP)": "采用最新的 AV1 编码，适合录制幻灯片，文件体积缩小 50% 以上。"
  "高画质收藏版 (HEVC/H.265, VBR)": "兼顾画质与兼容性，适合存储 1080p/4K 电影，支持硬件加速。"
  "老设备高兼容版 (H.264, CBR)": "最传统的格式，几乎能在任何破旧的播放器或电视上流畅运行。"
  "压片战争最小视频 (HEVC/H.265, VBR)": "极致压缩，纯属整活儿，文件体积极小。"
  "⚙️ 自定义参数...": "进入极客模式，手动微调每一项硬核压制参数。"

rc_tips:
  cqp: |
    <b>[ 质量恒定模式 ]</b><br>固定每一帧的压缩倍率。不限制码率，只保证画面清晰度。<br><b>数值意义：</b>0 为无损（文件巨大），51 为极模糊。<br><b>建议范围：</b>18 - 28。数值越小，画质越好，体积越大。
  vbr: |
    <b>[ 动态码率模式 ]</b><br>根据画面复杂度分配码率。复杂画面多给点，静止画面少给点。<br><b>数值意义：</b>设置的是‘目标平均码率’。<br><b>适用场景：</b>本地收藏、视频发布。是兼顾体积与画质的最佳平衡方案。
  cbr: |
    <b>[ 固定码率模式 ]</b><br>全程保持恒定的传输速率，不顾画面复杂度，强行填充码率。<br><b>数值意义：</b>设置的是‘固定传输速率’。<br><b>适用场景：</b>直播推流、老式硬件播放。缺点是简单画面浪费空间，复杂画面可能模糊。
"""
        with open(tooltips_path, 'w', encoding='utf-8') as f:
            f.write(default_tooltips)
            print("✨ 已自动生成默认 tooltips.yaml")