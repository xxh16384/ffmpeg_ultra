import sys, os

def get_ext_path(executable_name):
    """
    终极寻路雷达：判断当前是开发环境还是单文件 exe 环境
    """
    if hasattr(sys, '_MEIPASS'):
        # 如果是被打包成了单文件 exe，去系统偷偷解压的临时目录的 tools 文件夹里找
        return os.path.join(sys._MEIPASS, "tools", executable_name)
    else:
        # 获取项目根目录 (utils.py 在 core 目录下，所以向上退一级)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # 在项目根目录的 tools 文件夹中寻找
        return os.path.join(base_dir, "tools", executable_name)