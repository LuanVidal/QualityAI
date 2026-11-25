"""Identidade visual industrial e limpa do protótipo."""

APP_STYLESHEET = r"""
* {
    font-family: "Poppins", "Segoe UI";
    font-size: 14px;
    color: #f4fbff;
}
QMainWindow, QWidget#AppRoot {
    background: #071827;
}
QWidget#PageBody, QScrollArea, QScrollArea QWidget#qt_scrollarea_viewport {
    background: #071827;
}
QWidget#Sidebar {
    background: #0b1d31;
    border-right: 1px solid #123d5b;
}
QLabel#BrandLogo {
    background: #f7fcff;
    border: 1px solid #278bb0;
    border-radius: 14px;
    padding: 4px;
}
QLabel#BrandName {
    font-size: 21px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#BrandCaption, QLabel#Muted, QLabel#CardCaption, QLabel#SectionHint {
    color: #91b8ca;
}
QPushButton#NavButton {
    background: transparent;
    color: #a9c6d5;
    border: 0;
    border-left: 3px solid transparent;
    padding: 13px 16px;
    text-align: left;
    font-weight: 600;
}
QPushButton#NavButton:hover {
    background: #0e2c47;
    color: #ffffff;
}
QPushButton#NavButton:checked {
    background: #0b3554;
    border-left: 3px solid #00c3b2;
    color: #ffffff;
}
QWidget#Topbar {
    background: #092039;
    border-bottom: 1px solid #123d5b;
}
QLabel#PageTitle {
    font-size: 21px;
    font-weight: 650;
}
QLabel#StatusOnline {
    color: #54f3bd;
    background: #07372f;
    border: 1px solid #0b8e72;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 12px;
    font-weight: 600;
}
QLabel#StatusOffline {
    color: #ffbd66;
    background: #342919;
    border: 1px solid #624923;
    border-radius: 10px;
    padding: 2px 9px;
    font-size: 12px;
    font-weight: 600;
}
QFrame#Panel, QFrame#StatCard, QFrame#Hero {
    background: #0b2238;
    border: 1px solid #154561;
    border-radius: 12px;
}
QFrame#Hero {
    background: #0a2943;
    border: 1px solid #0b6590;
}
QLabel#HeroEyebrow {
    color: #18d8cf;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#HeroTitle {
    font-size: 28px;
    font-weight: 700;
}
QLabel#HeroText {
    color: #b1ccd9;
    font-size: 15px;
}
QLabel#CardValue {
    font-size: 27px;
    font-weight: 700;
}
QLabel#SectionTitle {
    font-size: 17px;
    font-weight: 650;
}
QLabel#DialogTitle {
    font-size: 22px;
    font-weight: 700;
}
QFrame#RecipeDetails {
    background: #081b2d;
    border: 1px solid #174b67;
    border-radius: 9px;
}
QLabel#RecipeType {
    color: #20d6c6;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#RecipeDescription {
    color: #b1ccd9;
}
QLabel#VideoView {
    background: #03111f;
    border: 1px solid #176081;
    border-radius: 10px;
    color: #6f8292;
    qproperty-alignment: AlignCenter;
}
QPushButton {
    background: #10324e;
    border: 1px solid #1a5b7c;
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 600;
}
QPushButton:hover { background: #154665; border-color: #2289aa; }
QPushButton:pressed { background: #0b2941; }
QPushButton:disabled { color: #668091; background: #102231; border-color: #20394b; }
QPushButton#PrimaryButton {
    background: #0873d1;
    color: #ffffff;
    border: 1px solid #18b9d5;
}
QPushButton#PrimaryButton:hover { background: #078fd5; }
QPushButton#OkButton {
    background: #009a78;
    border-color: #16d9aa;
    color: #ffffff;
}
QPushButton#OkButton:hover { background: #00b98d; }
QPushButton#OkButton:disabled {
    background: #16241f;
    border-color: #294237;
    color: #63766c;
}
QPushButton#NokButton {
    background: #a83f49;
    border-color: #e1616c;
    color: #ffffff;
}
QPushButton#NokButton:hover { background: #bd4a55; }
QPushButton#NokButton:disabled {
    background: #281a1d;
    border-color: #493036;
    color: #7c6266;
}
QPushButton#DangerOutlineButton {
    color: #ff9ca4;
    background: transparent;
    border: 1px solid #8d424c;
}
QPushButton#DangerOutlineButton:hover {
    color: #ffffff;
    background: #7d303b;
    border-color: #e1616c;
}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background: #071b2e;
    border: 1px solid #195271;
    border-radius: 7px;
    padding: 7px 9px;
    min-height: 20px;
}
QDialog {
    background: #091d30;
}
QFormLayout QLabel {
    color: #a9c6d5;
    font-weight: 600;
}
QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QLineEdit:focus {
    border-color: #00c3b2;
}
QCheckBox { spacing: 9px; }
QCheckBox::indicator {
    width: 17px;
    height: 17px;
    border: 1px solid #28718e;
    border-radius: 4px;
    background: #071b2e;
}
QCheckBox::indicator:checked {
    background: #00b99b;
    border-color: #18dbc1;
}
QSlider::groove:horizontal {
    height: 5px;
    background: #173e56;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -6px 0;
    background: #00c3b2;
    border-radius: 8px;
}
QProgressBar {
    background: #071b2e;
    border: 1px solid #174b67;
    border-radius: 7px;
    height: 14px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk { background: #00bda8; border-radius: 6px; }
QTextEdit, QListWidget {
    background: #061725;
    border: 1px solid #16465f;
    border-radius: 8px;
    padding: 8px;
}
QListWidget::item { padding: 7px; border-bottom: 1px solid #12364c; }
QScrollArea { border: 0; background: #071827; }
QScrollBar:vertical { background: #091d30; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #1c5b79; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QLabel#ResultOk {
    color: #61f2c2;
    background: #073a31;
    border: 1px solid #0aa57f;
    border-radius: 12px;
    font-size: 42px;
    font-weight: 750;
    qproperty-alignment: AlignCenter;
}
QLabel#ResultNok {
    color: #ff7c85;
    background: #3a1d24;
    border: 1px solid #7e3540;
    border-radius: 12px;
    font-size: 42px;
    font-weight: 750;
    qproperty-alignment: AlignCenter;
}
QLabel#ResultReview {
    color: #ffc767;
    background: #3a2c18;
    border: 1px solid #765728;
    border-radius: 12px;
    font-size: 34px;
    font-weight: 750;
    qproperty-alignment: AlignCenter;
}
"""
