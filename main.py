import sys
from PySide6.QtWidgets import QApplication

from core.main_window import FFmpegGUI
from core.utils import init_config_files

if __name__ == "__main__":
    init_config_files()
    app = QApplication(sys.argv)
    window = FFmpegGUI()
    window.show()
    sys.exit(app.exec())