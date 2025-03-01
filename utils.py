import json5 as json
import pandas as pd
from log import log
from sys import exit
import os

"""加载并解析JSONC配置文件"""
def read_json(fpath)->dict:
    try:
        with open(fpath, 'r', encoding='utf-8') as file:
            data = json.load(file)
            log(f"读取文件 '{fpath}': \n{data}", level='info')
            return data
    except FileNotFoundError:
        log(f"文件 '{fpath}' 未找到。", level='error')
        exit(1)
    except Exception as e:
        log(f"文件 '{fpath}' 不是有效的JSON5格式。详细信息如下：{e}", level='error')
        exit(1)


"""读取Excel文件"""
def read_excel(fpath, sheet_name=None):
    try:
        sheet_name = sheet_name if sheet_name else 0
        df = pd.read_excel(fpath, engine='openpyxl', sheet_name=sheet_name)
        log(f'读取表格 {fpath}, 行数={df.shape[0]}, 列数={df.shape[1]}', level='info')
        return df
    except FileNotFoundError:
        log(f"文件 '{fpath}' 未找到。", level='error')
        exit(1)


"""写入Excel文件"""
def write_excel(df: pd.DataFrame, fpath: str):
    try:
        df.to_excel(fpath, index=False, engine='openpyxl')
        log(f"DataFrame成功写入到 {fpath}, 行数={df.shape[0]}, 列数={df.shape[1]}", level='info')
    except FileNotFoundError:
        log(f"指定的路径 '{fpath}' 不存在或无法访问。", level='error')
    except PermissionError:
        log(f"没有权限将文件写入到 '{fpath}' 或文件正在被其他程序使用。", level='error')
    except ImportError as e:
        if "Missing optional dependency 'openpyxl'" in str(e):
            log("错误：缺少必要的库 'openpyxl'。", level='error')
        else:
            raise  # 如果是其他导入错误，则重新抛出异常
    except Exception as e:
        log(f"未知错误: {e}", level='error')


"""设置DataFrame中列的数据类型"""
def set_df_dtype(df: pd.DataFrame, dtype: dict, name = '表的名字'):
    """
    设置DataFrame中列的数据类型。

    参数:
    df (pd.DataFrame): 要修改的DataFrame。
    dtype (dict): 字典，键是数据类型，值是列名列表。

    返回:
    pd.DataFrame: 修改后的DataFrame。
    """
    for new_type, columns  in dtype.items():
        for column in columns:
            if column in df.columns:
                df[column] = df[column].astype(new_type)
            else:
                log(f" 列 '{column}' 不存在于 '{name}' 中。", level='warning')
    return df


def inteprete(text: str):
    '''
    调用函数,返回空值: "df->None"
    调用函数,返回: "df,df1->df"
    调用函数,返回: "None->df"
    '''
    input, output = text.split('->')
    input, output = [i.strip() for i in input.split(',')], [i.strip() for i in output.split(',')]
    return input, output


def check_columns_eq(df1: pd.DataFrame, df2: pd.DataFrame, fnames: list):
    """ 检查列名是否相同，返回修改后的 df 和 是否相同的标识，以及列不一致表 """
    isColumnsEq = True
    # 列名去空
    df1.columns, df2.columns = df1.columns.astype(str).str.strip(), df2.columns.astype(str).str.strip()
    columns1, columns2 = df1.columns, df2.columns
    if not columns1.equals(columns2):
        columns1, columns2 = sorted(columns1), sorted(columns2)
        if columns1 == columns2:
            df1, df2 = df1[columns1], df2[columns2]
        else:
            isColumnsEq = False

    df_diff_cols = None
    if not isColumnsEq:
        df_data = {"表名": fnames}
        for i in sorted(set(columns1) | set(columns2)):
            df_data[i] = ["" if i in columns1 else "无", 
                          "" if i in columns2 else "无"]
        df_diff_cols = pd.DataFrame(df_data)
        df_diff_cols = df_diff_cols.loc[:, (df_diff_cols != "").any(axis=0)]
        log(f"【比较两个表格的列名】列名不一致:\n{df_diff_cols}", level='info')
        # 修改 df
        df1, df2 = df1[list(set(columns1) & set(columns2))], \
                    df2[list(set(columns1) & set(columns2))]
    
    return isColumnsEq, df_diff_cols, df1, df2


def check_rows_eq(df1: pd.DataFrame, df2: pd.DataFrame):
    # 检查行数是否相同
    if df1.shape[0] != df2.shape[0]:
        log(f"【比较两个表格的行数】行数不一致: 表1={df1.shape[0]} 表2={df2.shape[0]}", level='info')
        return False
    return True


def compare_df(df1: pd.DataFrame, df2: pd.DataFrame, sort_columns: list):
    # 列名映射
    other_columns_dict = {i: f"差异_{i}" for i in df1.columns if i not in sort_columns}
    sort_columns_dict = {i: f"排序_{i}" for i in sort_columns}

    # 处理缺失值并转换为字符串类型
    df1 = df1.fillna('').astype(str).apply(lambda x: x.str.strip())
    df2 = df2.fillna('').astype(str).apply(lambda x: x.str.strip())

    # 对两个DataFrame按照排序列进行排序
    df1 = df1.sort_values(by=sort_columns).reset_index(drop=True)
    df2 = df2.sort_values(by=sort_columns).reset_index(drop=True)

    # 分组
    df1_g = df1.groupby(by=sort_columns)
    df2_g = df2.groupby(by=sort_columns)
    # 获取所有唯一的分组键
    all_keys = set(df1_g.groups.keys()).union(set(df2_g.groups.keys()))

    # 创建一个新的DataFrame用于存储比较结果
    comparison = pd.DataFrame(columns=['差异标识']+list(sort_columns_dict.values()), index=range(df1.shape[0]+df2.shape[0])).astype('str')
    comparison['差异状态'] = False
    comparison['差异标识'] = ''

    c_idx = 0
    # 遍历所有分组键
    for key in all_keys:
        # 获取 df1 和 df2 中对应的分组
        df1_group = df1_g.get_group(key if isinstance(key, (list, tuple, set)) else (key,)) if key in df1_g.groups else pd.DataFrame()
        df2_group = df2_g.get_group(key if isinstance(key, (list, tuple, set)) else (key,)) if key in df2_g.groups else pd.DataFrame()

        # 双方的数量相同
        if df1_group.shape[0] == df2_group.shape[0] and df1_group.shape[0] != 0:
            for (_,v1), (_,v2) in zip(df1_group.iterrows(), df2_group.iterrows()):
                v1_eq_v2 = v1.eq(v2)
                if not all(v1_eq_v2):
                    comparison.at[c_idx, "差异标识"] = "比较:表1<->表2"
                    comparison.at[c_idx, "差异状态"] = True
                    for i, j in sort_columns_dict.items():
                        comparison.at[c_idx, j] = f"{v1[i]}"
                    for i, j in other_columns_dict.items():
                        if v1[i] != v2[i]:
                            comparison.at[c_idx, j] = f"{v1[i]} <-> {v2[i]}"
                    # 更新 c_idx
                    c_idx += 1
        else:
            # df2_group 不为空
            if df1_group.empty:
                for _, row2 in df2_group.iterrows():
                    comparison.at[c_idx, "差异标识"] = "独有:表2"
                    comparison.at[c_idx, "差异状态"] = True 
                    for i, j in sort_columns_dict.items():
                        comparison.at[c_idx, j] = f"{row2[i]}"
                    for i, j in other_columns_dict.items():
                        if row2[i] != '':
                            comparison.at[c_idx, j] = f"{row2[i]}"
                    # 更新 c_idx
                    c_idx += 1
            # df1_group 不为空
            elif df2_group.empty:
                for _, row1 in df1_group.iterrows():
                    comparison.at[c_idx, "差异标识"] = "独有:表1"
                    comparison.at[c_idx, "差异状态"] = True
                    for i, j in sort_columns_dict.items():
                        comparison.at[c_idx, j] = f"{row1[i]}"
                    for i, j in other_columns_dict.items():
                        if row1[i] != '':
                            comparison.at[c_idx, j] = f"{row1[i]}"
                    # 更新 c_idx
                    c_idx += 1
            else:
                for _, row1 in df1_group.iterrows():
                    comparison.at[c_idx, "差异标识"] = "共有:表1"
                    comparison.at[c_idx, "差异状态"] = True
                    for i, j in sort_columns_dict.items():
                        comparison.at[c_idx, j] = f"{row1[i]}"
                    for i, j in other_columns_dict.items():
                        if row1[i] != '':
                            comparison.at[c_idx, j] = f"{row1[i]}"
                    # 更新 c_idx
                    c_idx += 1
                for _, row2 in df2_group.iterrows():
                    comparison.at[c_idx, "差异标识"] = "共有:表2"
                    comparison.at[c_idx, "差异状态"] = True
                    for i, j in sort_columns_dict.items():
                        comparison.at[c_idx, j] = f"{row2[i]}"
                    for i, j in other_columns_dict.items():
                        if row2[i] != '':
                            comparison.at[c_idx, j] = f"{row2[i]}"
                    # 更新 c_idx
                    c_idx += 1
    
    if comparison['差异状态'].any():
        comparison = comparison[comparison['差异状态']]
        comparison = comparison.drop(['差异状态'], axis=1)
        print(f"【比较两个表格】sort_columns={sort_columns},行数={comparison.shape[0]},列数={comparison.shape[1]} 两表格不完全一致")
        return False, comparison
    else:
        print(f"【比较两个表格】sort_columns={sort_columns},行数={comparison.shape[0]},列数={comparison.shape[1]} 两个表完全一致")
        return True, comparison


def get_basename(fpath: str, extension=False):
    if extension:
        return os.path.basename(fpath)
    return os.path.splitext(os.path.basename(fpath))[0]
    
def export_multiple_df(dfs: list[pd.DataFrame], fpath, sheet_names=None):
    try:
        with pd.ExcelWriter(fpath) as writer:
            if sheet_names is None:
                sheet_names = [f"Sheet{i+1}" for i in range(len(dfs))]
            assert len(dfs) == len(sheet_names), "【导出多个表格】dfs 和 sheetnames 长度不一"
            for df, sheet_name in zip(dfs, sheet_names):
                df.to_excel(writer, sheet_name=sheet_name, index=False)
    except Exception as e:
        log(f"【导出多个表格】出现错误：{e}")

    
            
            
