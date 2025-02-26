from PyQt5.QtWidgets import QMainWindow, QAction, QStackedWidget, \
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QHBoxLayout, QLineEdit, \
        QCheckBox, QMessageBox, QDialog, QGridLayout, QScrollArea
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QIcon, QPainter, QPixmap
from utils import read_json, read_excel, check_columns_eq, \
    export_multiple_df, get_basename
import os
from functools import partial

from logic import Logic

class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("joelee的excel批量处理工具")
        self.setWindowIcon(QIcon("R/icon.ico"))
        self.setGeometry(100, 100, 600, 400)
        self.setWindowOpacity(0.99)
        
        self.readConfig()
        self.initUI()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        pixmap = QPixmap("R/background.png")
        scaled_pixmap = pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(self.rect(), scaled_pixmap)
    
    def readConfig(self):
        config = read_json("config/config.jsonc")
        for func_name, func_details in config.items():
            sub_config = read_json(func_details["config"])
            config[func_name]["files"] = {fname: {"symbol": symbol, "path": ""}  for fname, symbol in sub_config["files"].items()}
            config[func_name]["actions"] = sub_config["actions"]
            config[func_name]["index"] = 0
            del config[func_name]["config"]
        # 帮助
        config.setdefault("帮助", {})["func"] = "help"
        config["帮助"]["index"] = 0
        self.config = config

    def initUI(self):
        # 创建菜单栏
        menubar = self.menuBar()
        menu_function = menubar.addMenu("功能")
        menu_help = menubar.addMenu("帮助")
        
        # 创建菜单栏容器
        self.stack = QStackedWidget()  # 容器,管理多个页面,同一时间只展示一个页面
        self.setCentralWidget(self.stack)  # 将该容器设置为中央部件

        # 往菜单栏和容器 添加 项目和页
        for func_name in self.config.keys():
            page = self.create_function_page(func_name)
            self.config[func_name]["index"] = self.stack.addWidget(page)

            action = QAction(func_name, self)
            action.triggered.connect(lambda checked, fn=func_name: self.switch_page(fn))

            if func_name == "帮助":
                menu_help.addAction(action)
            else:
                menu_function.addAction(action)
        
        # 默认显示帮助
        self.switch_page("帮助")


    def switch_page(self, func_name):
        self.stack.setCurrentIndex(self.config[func_name]["index"])
    
    def show_checkbox_dialog(self, title, item_list, msg) -> list:
        dialog = QDialog(self)
        dialog.setWindowTitle(title)

        msg_widge = QLineEdit(msg)
        msg_widge.setReadOnly(True)

        # 设置滚动区域和滚动部件
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widge = QWidget()
        scroll_layout = QGridLayout(scroll_widge)

        checkboxes = []
        n_col = 3
        for i, item in enumerate(item_list):
            checkbox = QCheckBox(item)
            checkboxes.append(checkbox)
            scroll_layout.addWidget(checkbox, i//n_col, i%n_col)
        scroll_area.setWidget(scroll_widge)
        # 设置确认按钮
        confirm_button = QPushButton("确认")
        confirm_button.clicked.connect(
            partial(self.process_checkbox_selection, dialog, checkboxes))
        # 设置 dialog 的 Layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(msg_widge)
        main_layout.addWidget(scroll_area)
        main_layout.addWidget(confirm_button)

        dialog.setLayout(main_layout)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            selected_items = []
            for checkbox in checkboxes:
                if checkbox.isChecked():
                    selected_items.append(checkbox.text())
            return selected_items
        
        return []
    
    def process_checkbox_selection(self, parent, checkboxes):
        any_selected = False
        for checkbox in checkboxes:
            if checkbox.isChecked():
                any_selected = True
                break
        if any_selected:
            parent.accept()
        else:
            self.warning(f"用户没做任何选择", parent=parent)
    
    def select_file(self, fname):
        default_dir = os.path.join(os.getcwd(), "data")
        file_path, _ = QFileDialog.getOpenFileName(self, f"选择{fname}", default_dir, "所有文件 (*)")
        return file_path if file_path else ""

    def select_save_file(self, output_widge, func_name, fname):
        fpath = self.select_file(fname)
        self.config[func_name]["files"][fname]["path"] = fpath
        output_widge.setText(fpath)
    
    def check_file_paths(self, fpaths_dict, none_path=""):
        for fname, fpath_dict in fpaths_dict.items():
            fpath = fpath_dict["path"]
            if fpath == none_path:
                self.warning(f"用户未选择{fname}")
                return False
            if not os.path.exists(fpath):
                self.warning(f"{fname}={fpath}不存在")
                return False
        return True

    def confirm_actionloop(self, func_name):
        # 检查路径是否有效
        if self.check_file_paths(self.config[func_name]["files"]):
            try:
                Logic.action_loop(self.config[func_name])
                self.tip(f"\"{func_name}\" 已完成,请查看 data 目录", False)
            except Exception as e:
                self.warning(f"发生未知错误: {e}", disappear=False)
    
    def get_select_files_layout(self, func_name, confirm_callback):
        layout = QVBoxLayout()

        # 添加文件选择按钮和路径标签
        fnames = self.config[func_name]["files"].keys()
        for fname in fnames:
            fpath = self.config[func_name]["files"][fname]["path"]
            file_line_layout = QHBoxLayout()
            file_path = QLineEdit(fpath)
            file_path.setReadOnly(True)
            select_button = QPushButton(f"选择{fname}")
            select_button.clicked.connect(
                partial(self.select_save_file, file_path, func_name, fname))
            file_line_layout.addWidget(select_button)
            file_line_layout.addWidget(file_path)
            
            layout.addLayout(file_line_layout)
        
        # 添加确认按钮
        confirm_button = QPushButton("确认")
        confirm_button.clicked.connect(confirm_callback)
        layout.addWidget(confirm_button)

        return layout

    def create_actionloop_page(self, func_name):
        page = QWidget()
        layout = self.get_select_files_layout(func_name, 
            partial(self.confirm_actionloop, func_name))
        page.setLayout(layout)
        return page
    
    def create_help_page(self, func_name):
        page = QWidget()
        layout = QVBoxLayout()
        help_info = ("帮助文档\n\n这是一个用于批量处理Excel的工具。\n"
                    "您的所有数据均保存在本地，该软件仅用作批处理excel文件\n"
                    "菜单栏的\"功能\"的所有菜单项均由 config 目录下的配置文件决定")
        layout.addWidget(QLabel(help_info))
        layout.addWidget(QLabel("版权信息\n\n© 2025 joelee 版权所有"))
        page.setLayout(layout)
        return page
    
    def confirm_compare(self, func_name):
        # 检查路径是否有效
        if not self.check_file_paths(self.config[func_name]["files"]):
            return

        df1_path = self.config[func_name]["files"]["表1"]["path"]
        df2_path = self.config[func_name]["files"]["表2"]["path"]
        out_path = f"data/差异表_{get_basename(df1_path)}_{get_basename(df2_path)}.xlsx"

        # 根据 path 读取相关文件
        df1 = read_excel(df1_path)
        df2 = read_excel(df2_path)

        # 检查列是否相同
        col_eq, df_diff_col, df1, df2 = check_columns_eq(df1, df2, 
            [get_basename(df1_path, True), get_basename(df2_path, True)])

        # 选择 排序列
        msg = f"两表的所有列的列名能一一对应" if col_eq else f"两表的所有列的列名不能一一对应,因此仅比较能一一对应的列"
        selected_cols = self.show_checkbox_dialog("请选择排序列", df1.columns.tolist(), msg)
        if selected_cols == []:
            return

        # 比较
        try:
            df_eq, comparison = Logic.compare(df1, df2, selected_cols)
        except Exception as e:
            self.warning(f"发生未知错误: {e}", disappear=False)
    
        # 输出结果
        disappear = False
        if col_eq and df_eq:
            self.tip(f"两表: 列完全相同，数据完全相同", disappear)
        elif col_eq and not df_eq:
            export_multiple_df([comparison], out_path, ["差异表"])
            self.tip(f"两表: 列完全相同，数据不完全相同\n请查看 \"{out_path}\"\nsheet_name=\"差异表\"", disappear)
        elif not col_eq and not df_eq:
            export_multiple_df([comparison, df_diff_col], out_path, ["差异表", "列差异表"])
            self.tip(f"两表: 列不完全相同，相同列的数据不完全相同\n请查看 \"{out_path}\"\nsheet_name=\"差异表,列差异表\"", disappear)
        else:
            export_multiple_df([df_diff_col], out_path, ["列差异表"])
            self.tip(f"两表: 列不完全相同，相同列的数据完全相同\n请查看 \"{out_path}\"\nsheet_name=\"列差异表\"", disappear)
    
    def create_compare_page(self, func_name):
        page = QWidget()
        layout = self.get_select_files_layout(func_name, partial(self.confirm_compare, func_name))
        page.setLayout(layout)
        return page

    def create_function_page(self, func_name):
        page_factory = {
            "compare": self.create_compare_page,
            "action_loop": self.create_actionloop_page,
            "help": self.create_help_page
        }
        func = self.config[func_name]["func"]
        if func not in page_factory.keys():
            self.warning(f"未知功能 {func}")
        return page_factory[func](func_name)

    def tip(self, msg, disappear=True):
        msgbox = QMessageBox(self)
        msgbox.setIcon(QMessageBox.Information)
        msgbox.setText(msg)
        msgbox.setWindowTitle("tips")
        msgbox.setStandardButtons(QMessageBox.Ok)
        if disappear:
            QTimer.singleShot(2000, msgbox.close)
        msgbox.show()

    def warning(self, msg, disappear=True, parent=None):
        parent = parent if parent else self
        msgbox = QMessageBox(parent)
        msgbox.setIcon(QMessageBox.Warning)
        msgbox.setText(msg)
        msgbox.setWindowTitle("warning")
        msgbox.setStandardButtons(QMessageBox.Ok)
        if disappear:
            QTimer.singleShot(2000, msgbox.close)
        msgbox.show()
