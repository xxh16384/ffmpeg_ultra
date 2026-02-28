# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow,
    QProgressBar, QPushButton, QSizePolicy, QSlider,
    QSpacerItem, QTabWidget, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(850, 500)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.main_layout = QHBoxLayout(self.centralwidget)
        self.main_layout.setObjectName(u"main_layout")
        self.left_panel = QVBoxLayout()
        self.left_panel.setObjectName(u"left_panel")
        self.label_1 = QLabel(self.centralwidget)
        self.label_1.setObjectName(u"label_1")

        self.left_panel.addWidget(self.label_1)

        self.btn_input = QPushButton(self.centralwidget)
        self.btn_input.setObjectName(u"btn_input")

        self.left_panel.addWidget(self.btn_input)

        self.txt_input = QLineEdit(self.centralwidget)
        self.txt_input.setObjectName(u"txt_input")

        self.left_panel.addWidget(self.txt_input)

        self.btn_output = QPushButton(self.centralwidget)
        self.btn_output.setObjectName(u"btn_output")

        self.left_panel.addWidget(self.btn_output)

        self.output_layout = QHBoxLayout()
        self.output_layout.setObjectName(u"output_layout")
        self.txt_output = QLineEdit(self.centralwidget)
        self.txt_output.setObjectName(u"txt_output")

        self.output_layout.addWidget(self.txt_output)

        self.cb_format = QComboBox(self.centralwidget)
        self.cb_format.addItem("")
        self.cb_format.addItem("")
        self.cb_format.addItem("")
        self.cb_format.addItem("")
        self.cb_format.addItem("")
        self.cb_format.setObjectName(u"cb_format")
        self.cb_format.setMinimumSize(QSize(75, 0))

        self.output_layout.addWidget(self.cb_format)


        self.left_panel.addLayout(self.output_layout)

        self.verticalSpacer_1 = QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.left_panel.addItem(self.verticalSpacer_1)

        self.label_2 = QLabel(self.centralwidget)
        self.label_2.setObjectName(u"label_2")

        self.left_panel.addWidget(self.label_2)

        self.combo_preset = QComboBox(self.centralwidget)
        self.combo_preset.setObjectName(u"combo_preset")

        self.left_panel.addWidget(self.combo_preset)

        self.chk_preview = QCheckBox(self.centralwidget)
        self.chk_preview.setObjectName(u"chk_preview")

        self.left_panel.addWidget(self.chk_preview)

        self.tab_custom = QTabWidget(self.centralwidget)
        self.tab_custom.setObjectName(u"tab_custom")
        self.tab_custom.setVisible(False)
        self.tab_video = QWidget()
        self.tab_video.setObjectName(u"tab_video")
        self.layout_video = QFormLayout(self.tab_video)
        self.layout_video.setObjectName(u"layout_video")
        self.lbl_v1 = QLabel(self.tab_video)
        self.lbl_v1.setObjectName(u"lbl_v1")

        self.layout_video.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_v1)

        self.cb_v_encoder = QComboBox(self.tab_video)
        self.cb_v_encoder.setObjectName(u"cb_v_encoder")

        self.layout_video.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cb_v_encoder)

        self.lbl_v2 = QLabel(self.tab_video)
        self.lbl_v2.setObjectName(u"lbl_v2")

        self.layout_video.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_v2)

        self.cb_v_fps = QComboBox(self.tab_video)
        self.cb_v_fps.addItem("")
        self.cb_v_fps.addItem("")
        self.cb_v_fps.addItem("")
        self.cb_v_fps.addItem("")
        self.cb_v_fps.setObjectName(u"cb_v_fps")

        self.layout_video.setWidget(1, QFormLayout.ItemRole.FieldRole, self.cb_v_fps)

        self.lbl_v3 = QLabel(self.tab_video)
        self.lbl_v3.setObjectName(u"lbl_v3")

        self.layout_video.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_v3)

        self.cb_v_res = QComboBox(self.tab_video)
        self.cb_v_res.addItem("")
        self.cb_v_res.addItem("")
        self.cb_v_res.addItem("")
        self.cb_v_res.addItem("")
        self.cb_v_res.addItem("")
        self.cb_v_res.setObjectName(u"cb_v_res")

        self.layout_video.setWidget(2, QFormLayout.ItemRole.FieldRole, self.cb_v_res)

        self.lbl_v4 = QLabel(self.tab_video)
        self.lbl_v4.setObjectName(u"lbl_v4")

        self.layout_video.setWidget(3, QFormLayout.ItemRole.LabelRole, self.lbl_v4)

        self.cb_v_rc = QComboBox(self.tab_video)
        self.cb_v_rc.addItem("")
        self.cb_v_rc.addItem("")
        self.cb_v_rc.addItem("")
        self.cb_v_rc.setObjectName(u"cb_v_rc")

        self.layout_video.setWidget(3, QFormLayout.ItemRole.FieldRole, self.cb_v_rc)

        self.lbl_v5 = QLabel(self.tab_video)
        self.lbl_v5.setObjectName(u"lbl_v5")

        self.layout_video.setWidget(4, QFormLayout.ItemRole.LabelRole, self.lbl_v5)

        self.val_layout = QHBoxLayout()
        self.val_layout.setObjectName(u"val_layout")
        self.sld_v_value = QSlider(self.tab_video)
        self.sld_v_value.setObjectName(u"sld_v_value")
        self.sld_v_value.setOrientation(Qt.Horizontal)

        self.val_layout.addWidget(self.sld_v_value)

        self.lbl_v_val_display = QLabel(self.tab_video)
        self.lbl_v_val_display.setObjectName(u"lbl_v_val_display")
        self.lbl_v_val_display.setMinimumSize(QSize(60, 0))

        self.val_layout.addWidget(self.lbl_v_val_display)


        self.layout_video.setLayout(4, QFormLayout.ItemRole.FieldRole, self.val_layout)

        self.tab_custom.addTab(self.tab_video, "")
        self.tab_audio = QWidget()
        self.tab_audio.setObjectName(u"tab_audio")
        self.layout_audio = QFormLayout(self.tab_audio)
        self.layout_audio.setObjectName(u"layout_audio")
        self.lbl_a1 = QLabel(self.tab_audio)
        self.lbl_a1.setObjectName(u"lbl_a1")

        self.layout_audio.setWidget(0, QFormLayout.ItemRole.LabelRole, self.lbl_a1)

        self.cb_a_encoder = QComboBox(self.tab_audio)
        self.cb_a_encoder.addItem("")
        self.cb_a_encoder.addItem("")
        self.cb_a_encoder.addItem("")
        self.cb_a_encoder.addItem("")
        self.cb_a_encoder.setObjectName(u"cb_a_encoder")

        self.layout_audio.setWidget(0, QFormLayout.ItemRole.FieldRole, self.cb_a_encoder)

        self.lbl_a2 = QLabel(self.tab_audio)
        self.lbl_a2.setObjectName(u"lbl_a2")

        self.layout_audio.setWidget(1, QFormLayout.ItemRole.LabelRole, self.lbl_a2)

        self.cb_a_bitrate = QComboBox(self.tab_audio)
        self.cb_a_bitrate.addItem("")
        self.cb_a_bitrate.addItem("")
        self.cb_a_bitrate.addItem("")
        self.cb_a_bitrate.addItem("")
        self.cb_a_bitrate.addItem("")
        self.cb_a_bitrate.setObjectName(u"cb_a_bitrate")

        self.layout_audio.setWidget(1, QFormLayout.ItemRole.FieldRole, self.cb_a_bitrate)

        self.lbl_a3 = QLabel(self.tab_audio)
        self.lbl_a3.setObjectName(u"lbl_a3")

        self.layout_audio.setWidget(2, QFormLayout.ItemRole.LabelRole, self.lbl_a3)

        self.cb_a_sample = QComboBox(self.tab_audio)
        self.cb_a_sample.addItem("")
        self.cb_a_sample.addItem("")
        self.cb_a_sample.addItem("")
        self.cb_a_sample.setObjectName(u"cb_a_sample")

        self.layout_audio.setWidget(2, QFormLayout.ItemRole.FieldRole, self.cb_a_sample)

        self.tab_custom.addTab(self.tab_audio, "")

        self.left_panel.addWidget(self.tab_custom)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.left_panel.addItem(self.verticalSpacer_2)

        self.btn_start = QPushButton(self.centralwidget)
        self.btn_start.setObjectName(u"btn_start")
        self.btn_start.setMinimumSize(QSize(0, 45))

        self.left_panel.addWidget(self.btn_start)

        self.btn_layout = QHBoxLayout()
        self.btn_layout.setObjectName(u"btn_layout")
        self.btn_pause = QPushButton(self.centralwidget)
        self.btn_pause.setObjectName(u"btn_pause")
        self.btn_pause.setEnabled(False)

        self.btn_layout.addWidget(self.btn_pause)

        self.btn_stop = QPushButton(self.centralwidget)
        self.btn_stop.setObjectName(u"btn_stop")
        self.btn_stop.setEnabled(False)

        self.btn_layout.addWidget(self.btn_stop)


        self.left_panel.addLayout(self.btn_layout)


        self.main_layout.addLayout(self.left_panel)

        self.right_panel = QVBoxLayout()
        self.right_panel.setObjectName(u"right_panel")
        self.label_3 = QLabel(self.centralwidget)
        self.label_3.setObjectName(u"label_3")

        self.right_panel.addWidget(self.label_3)

        self.lbl_preview = QLabel(self.centralwidget)
        self.lbl_preview.setObjectName(u"lbl_preview")
        self.lbl_preview.setMinimumSize(QSize(480, 270))
        self.lbl_preview.setAlignment(Qt.AlignCenter)

        self.right_panel.addWidget(self.lbl_preview)

        self.verticalSpacer_3 = QSpacerItem(20, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.right_panel.addItem(self.verticalSpacer_3)

        self.label_4 = QLabel(self.centralwidget)
        self.label_4.setObjectName(u"label_4")

        self.right_panel.addWidget(self.label_4)

        self.progress_bar = QProgressBar(self.centralwidget)
        self.progress_bar.setObjectName(u"progress_bar")
        self.progress_bar.setValue(0)

        self.right_panel.addWidget(self.progress_bar)

        self.lbl_status = QLabel(self.centralwidget)
        self.lbl_status.setObjectName(u"lbl_status")

        self.right_panel.addWidget(self.lbl_status)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.right_panel.addItem(self.verticalSpacer_4)


        self.main_layout.addLayout(self.right_panel)

        self.main_layout.setStretch(0, 1)
        self.main_layout.setStretch(1, 2)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        self.tab_custom.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"xxh\u89c6\u9891\u538b\u5236\u5de5\u5177 v1.0", None))
        self.label_1.setText(QCoreApplication.translate("MainWindow", u"<b>\U0001f4c1 \U0000533a\U000057df\U00004e00\U0000ff1a\U00006587\U00004ef6\U00008c03\U00005ea6</b>", None))
        self.btn_input.setText(QCoreApplication.translate("MainWindow", u"\u9009\u62e9\u539f\u89c6\u9891", None))
        self.txt_input.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u7b49\u5f85\u5bfc\u5165...", None))
        self.btn_output.setText(QCoreApplication.translate("MainWindow", u"\u8bbe\u7f6e\u5bfc\u51fa\u8def\u5f84", None))
        self.txt_output.setPlaceholderText(QCoreApplication.translate("MainWindow", u"\u7b49\u5f85\u8bbe\u7f6e...", None))
        self.cb_format.setItemText(0, QCoreApplication.translate("MainWindow", u".mp4", None))
        self.cb_format.setItemText(1, QCoreApplication.translate("MainWindow", u".mkv", None))
        self.cb_format.setItemText(2, QCoreApplication.translate("MainWindow", u".mov", None))
        self.cb_format.setItemText(3, QCoreApplication.translate("MainWindow", u".flv", None))
        self.cb_format.setItemText(4, QCoreApplication.translate("MainWindow", u".avi", None))

        self.cb_format.setStyleSheet(QCoreApplication.translate("MainWindow", u"font-weight: bold;", None))
        self.label_2.setText(QCoreApplication.translate("MainWindow", u"<b>\u2699\ufe0f \u533a\u57df\u4e8c\uff1a\u538b\u5236\u7b56\u7565</b>", None))
        self.chk_preview.setText(QCoreApplication.translate("MainWindow", u"\u5f00\u542f\u5b9e\u65f6\u753b\u9762\u9884\u89c8", None))
        self.lbl_v1.setText(QCoreApplication.translate("MainWindow", u"\u7f16\u7801\u5668:", None))
        self.lbl_v2.setText(QCoreApplication.translate("MainWindow", u"\u5e27\u7387(FPS):", None))
        self.cb_v_fps.setItemText(0, QCoreApplication.translate("MainWindow", u"\u4fdd\u6301\u6e90", None))
        self.cb_v_fps.setItemText(1, QCoreApplication.translate("MainWindow", u"24", None))
        self.cb_v_fps.setItemText(2, QCoreApplication.translate("MainWindow", u"30", None))
        self.cb_v_fps.setItemText(3, QCoreApplication.translate("MainWindow", u"60", None))

        self.lbl_v3.setText(QCoreApplication.translate("MainWindow", u"\u5206\u8fa8\u7387:", None))
        self.cb_v_res.setItemText(0, QCoreApplication.translate("MainWindow", u"\u4fdd\u6301\u6e90", None))
        self.cb_v_res.setItemText(1, QCoreApplication.translate("MainWindow", u"720p", None))
        self.cb_v_res.setItemText(2, QCoreApplication.translate("MainWindow", u"1080p", None))
        self.cb_v_res.setItemText(3, QCoreApplication.translate("MainWindow", u"1440p", None))
        self.cb_v_res.setItemText(4, QCoreApplication.translate("MainWindow", u"2160p", None))

        self.lbl_v4.setText(QCoreApplication.translate("MainWindow", u"\u7801\u7387\u63a7\u5236:", None))
        self.cb_v_rc.setItemText(0, QCoreApplication.translate("MainWindow", u"cqp", None))
        self.cb_v_rc.setItemText(1, QCoreApplication.translate("MainWindow", u"vbr", None))
        self.cb_v_rc.setItemText(2, QCoreApplication.translate("MainWindow", u"cbr", None))

        self.lbl_v5.setText(QCoreApplication.translate("MainWindow", u"\u53c2\u6570\u6570\u503c:", None))
        self.lbl_v_val_display.setStyleSheet(QCoreApplication.translate("MainWindow", u"font-weight: bold; color: #225555;", None))
        self.lbl_v_val_display.setText(QCoreApplication.translate("MainWindow", u"32", None))
        self.tab_custom.setTabText(self.tab_custom.indexOf(self.tab_video), QCoreApplication.translate("MainWindow", u"\u89c6\u9891\u8bbe\u7f6e", None))
        self.lbl_a1.setText(QCoreApplication.translate("MainWindow", u"\u7f16\u7801\u5668:", None))
        self.cb_a_encoder.setItemText(0, QCoreApplication.translate("MainWindow", u"aac", None))
        self.cb_a_encoder.setItemText(1, QCoreApplication.translate("MainWindow", u"mp3", None))
        self.cb_a_encoder.setItemText(2, QCoreApplication.translate("MainWindow", u"copy", None))
        self.cb_a_encoder.setItemText(3, QCoreApplication.translate("MainWindow", u"an (\u5265\u79bb\u9759\u97f3)", None))

        self.lbl_a2.setText(QCoreApplication.translate("MainWindow", u"\u7801\u7387:", None))
        self.cb_a_bitrate.setItemText(0, QCoreApplication.translate("MainWindow", u"320k", None))
        self.cb_a_bitrate.setItemText(1, QCoreApplication.translate("MainWindow", u"192k", None))
        self.cb_a_bitrate.setItemText(2, QCoreApplication.translate("MainWindow", u"128k", None))
        self.cb_a_bitrate.setItemText(3, QCoreApplication.translate("MainWindow", u"96k", None))
        self.cb_a_bitrate.setItemText(4, QCoreApplication.translate("MainWindow", u"64k", None))

        self.lbl_a3.setText(QCoreApplication.translate("MainWindow", u"\u91c7\u6837\u7387:", None))
        self.cb_a_sample.setItemText(0, QCoreApplication.translate("MainWindow", u"\u4fdd\u6301\u6e90", None))
        self.cb_a_sample.setItemText(1, QCoreApplication.translate("MainWindow", u"44100", None))
        self.cb_a_sample.setItemText(2, QCoreApplication.translate("MainWindow", u"48000", None))

        self.tab_custom.setTabText(self.tab_custom.indexOf(self.tab_audio), QCoreApplication.translate("MainWindow", u"\u97f3\u9891\u8bbe\u7f6e", None))
        self.btn_start.setStyleSheet(QCoreApplication.translate("MainWindow", u"font-weight: bold; font-size: 14px;", None))
        self.btn_start.setText(QCoreApplication.translate("MainWindow", u"\U0001f680 \U00005f00\U000059cb\U0000538b\U00005236", None))
        self.btn_pause.setText(QCoreApplication.translate("MainWindow", u"\u23f8 \u6682\u505c", None))
        self.btn_stop.setText(QCoreApplication.translate("MainWindow", u"\u23f9 \u505c\u6b62", None))
        self.label_3.setText(QCoreApplication.translate("MainWindow", u"<b>\U0001f4fa \U0000533a\U000057df\U00004e09\U0000ff1a\U00005b9e\U000065f6\U000076d1\U000063a7\U00005c4f</b>", None))
        self.lbl_preview.setStyleSheet(QCoreApplication.translate("MainWindow", u"background-color: #1e1e1e; color: #888888; border-radius: 8px; font-size: 16px;", None))
        self.lbl_preview.setText(QCoreApplication.translate("MainWindow", u"\u753b\u9762\u9884\u89c8\u533a\n"
"(\u7b49\u5f85\u538b\u5236\u5f00\u59cb...)", None))
        self.label_4.setText(QCoreApplication.translate("MainWindow", u"<b>\U0001f4ca \U0000533a\U000057df\U000056db\U0000ff1a\U00008fd0\U0000884c\U000072b6\U00006001</b>", None))
        self.lbl_status.setStyleSheet(QCoreApplication.translate("MainWindow", u"color: #666666;", None))
        self.lbl_status.setText(QCoreApplication.translate("MainWindow", u"\u72b6\u6001: \u95f2\u7f6e | \u901f\u5ea6: -- | \u5269\u4f59\u65f6\u95f4: -- |  \u5f53\u524d\u6587\u4ef6\u5927\u5c0f: --", None))
    # retranslateUi

