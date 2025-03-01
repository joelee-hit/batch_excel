from utils import read_excel, inteprete, compare_df
from tool import *
from sys import exit
import os

class Logic:
    @staticmethod
    def select_file():
        """选择文件并返回文件路径"""
        import tkinter.filedialog as filedialog
        file_path = filedialog.askopenfilename(title="选择文件", initialdir="data")
        return file_path

    @staticmethod
    def show_file_path(file_path):
        """显示文件路径"""
        import tkinter.messagebox as messagebox
        if file_path:
            messagebox.showinfo("文件选择", f"你选择的文件路径是: {file_path}")

    @staticmethod
    def check_paths_validity(files_list):
        invalid_paths = []
        for file in files_list:
            if not os.path.exists(file):
                invalid_paths.append(file)
        return invalid_paths

    @staticmethod
    def compare(df1, df2, sort_columns):
        try:
            df_eq, comparison = compare_df(df1, df2, sort_columns)
            return df_eq, comparison
        except Exception as e:
            log(f"【比较两个表格】未知错误: {e}", level="error")
            exit(1)

    @staticmethod
    def action_loop(config: dict):
        df_dict = {}
        for k, v in config["files"].items():
            df_dict[v["symbol"]] = read_excel(v["path"])

        actions_list = sorted(config['actions'].items(), key=lambda x: int(x[0]))

        # 根据配置文件中的动作处理 DataFrame
        for _, actions in actions_list:
            for action_code, details in actions.items():
                if action_code == "1" or action_code == "fill":
                    # 示例：找到重复组，并补充相应列的信息（具体逻辑需要根据需求定制）
                    by, log_columns = details['by'], details['log_columns']
                    input, output = inteprete(details['df'])
                    df_dict[output[0]] = fill(df_dict[input[0]], by, log_columns)
                elif action_code == "2" or action_code == "eq_sum":
                    # 示例：找到重复组，再根据判等列判断两行是否相等，若相等则删除，累加列进行累加
                    by, eq, sum1, log_columns = details['by'], details['eq'], \
                                                details['sum'], details['log_columns']
                    input, output = inteprete(details['df'])
                    df_dict[output[0]] = eq_sum(df_dict[input[0]], by, eq, sum1, log_columns)
                elif action_code == "3" or action_code == "rm_row":
                    # 筛选某列的值，移除相应的行
                    rm_rules, log_columns = details['rm_rules'], details['log_columns']
                    input, output = inteprete(details['df'])
                    df_dict[output[0]] = rm_row(df_dict[input[0]], rm_rules, log_columns)
                elif action_code == "4" or action_code == "add_row":
                    # 根据某列的值进行筛选，通过规则增加行
                    add_rules, log_columns = details['add_rules'], details['log_columns']
                    input, output = inteprete(details['df'])
                    df_dict[output[0]] = add_row(df_dict[input[0]], add_rules, log_columns)
                elif action_code == "5" or action_code == "alter_val":
                    # 根据改列值规则，进行某列的筛选和改值
                    alter_rules, log_columns = details['alter_rules'], details['log_columns']
                    input, output = inteprete(details['df'])
                    df_dict[output[0]] = alter_val(df_dict[input[0]], alter_rules, log_columns)
                elif action_code == "6" or action_code == "split":
                    # 分仓
                    split_rules, extract, log_columns, name = details["split_rules"], \
                        details["extract"], details["log_columns"], details["name"]
                    input, output = inteprete(details['df'])
                    df_dict[output[0]], df_dict[output[1]] = split(df_dict[input[0]], split_rules, extract, log_columns, name)
                elif action_code == "7" or action_code == "format":
                    # 格式化表
                    format_rules, columns, log_columns, name = details["format_rules"], \
                        details["columns"], details["log_columns"], details["name"]
                    input, output = inteprete(details['df'])
                    df_dict[output[0]] = format(df_dict[input[0]], format_rules, columns, log_columns, name)
                elif action_code == "8" or action_code == "add_col":
                    # 增加某列
                    add_rules, log_columns, name = details["add_rules"], details["log_columns"], details["name"]
                    input, output = inteprete(details['df'])
                    df_dict[output[0]] = add_col(df_dict[input[0]], add_rules, log_columns, name)
                elif action_code == "9" or action_code == "export":
                    # 导出表格
                    export_dtype, name, suffix, count_cols = details["export_dtype"], \
                        details["name"], details["suffix"], details["count_cols"]
                    input, output = inteprete(details['df'])
                    export(df_dict[input[0]], export_dtype, name, suffix, count_cols)
                elif action_code == "10" or action_code == "concat_df":
                    # 合并表格
                    axis = details["axis"]  # 横向: 1  纵向: 0
                    input, output = inteprete(details["df"])
                    input = [df_dict[i] for i in input]
                    df_dict[output[0]] = concat_df(input, axis)