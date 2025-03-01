import pandas as pd
from log import log, log_df
import re
from datetime import datetime
from utils import write_excel, set_df_dtype

"""根据排序列列表，筛选重复行，用重复行的数据补充缺失值信息"""
def fill(df: pd.DataFrame, by: list, log_columns: list):
    df_t = df.copy()

    # 检查排序列是否存在且不为空
    for col in by:
        if col not in df.columns or df[col].isnull().all():
            log(f"排序列 '{col}' 不存在或包含空值.", level='warning')
    
    duplicate_mask = df_t.duplicated(subset=by, keep=False)  # 包括第一次出现的
    duplicate_first = duplicate_mask & (~df_t.duplicated(subset=by, keep='first'))  # 仅用作日志
    
    other = list(set(df_t.columns.tolist()) - set(by))
    df_t[other] = df_t.groupby(by)[other].transform(lambda df_group: df_group.ffill().bfill())
    
    # 打印日志
    log_df(df.loc[duplicate_mask, log_columns], f"【重复组缺失值】按照排序列 '{by}' 筛选的重复组: 数量={sum(duplicate_first)}", level='info')
    log_df(df_t.loc[duplicate_mask, log_columns], f"【重复组缺失值】补充缺失值后: ", level='info')
    return df_t


"""根据排序列找到重复组，并根据判等列判断两行是否相等。如果相等，则删除其中一个，并累加指定的列"""
def eq_sum(df: pd.DataFrame, by: list, eq: list, sum1: list, log_columns: list):
    """log_columns 仅用作打印日志"""
    df_t = df.copy()

    # 检查排序列是否存在且不为空
    for col in by:
        if col not in df.columns or df[col].isnull().all():
            log(f"排序列 '{col}' 不存在或包含空值.", level='warning')
    
    # 累加
    # [sum] 取出 sum 列的所有分组 -> DataFrameGroupBy 
    # .transform('sum') 对分组进行变换操作 -> DataFrame
    df_t[sum1] = df_t.groupby(by + eq)[sum1].transform('sum')  

    # 删除
    duplicates_non_first = df_t.duplicated(subset=by + eq, keep='first')
    duplicates_first = df_t.duplicated(subset=by + eq, keep=False) & (~duplicates_non_first)

    # 打印日志
    log_df(df.loc[duplicates_non_first, log_columns], f"【删除重复行 & 累加】 by={by} eq={eq} sum={sum1}, 要删除的行: 数量={sum(duplicates_non_first)}", level='info')
    log_df(df_t.loc[duplicates_first, log_columns], f"【删除重复行 & 累加】 by={by} eq={eq} sum={sum1}, 保留的行: 数量={sum(duplicates_first)}", level='info')

    return df_t[~duplicates_non_first]


"""筛选某列的值，移除符合条件的行，并且可以使用正则表达式进行筛选"""
def rm_row(df: pd.DataFrame, rm_rules: list[dict[str: str]], log_columns: list[str]) -> pd.DataFrame:
    """log_columns 仅用作打印日志
    [{}, {}]
    """
    df_t = df.copy()

    mask = pd.Series(False, index=df_t.index)

    for rule in rm_rules:
        mask0 = pd.Series(True, index=df_t.index)
        for column, regex in rule.items():
            # 并
            mask0 &= df_t[column].astype(str).str.contains(regex, regex=True, na=False, flags=re.IGNORECASE)
        mask |= mask0
    
    df_t = df_t[~mask]

    # 打印日志
    if mask.any():
        log_df(df.loc[mask, log_columns], f"【删除行】根据如下规则 '{rm_rules}' 要删除的行: ", level='info')
    else:
        log("【删除行】根据规则 '{rm_rules}' 没筛选出要删除的行")

    return df_t


"""根据某列的值进行筛选，通过规则增加行。"""
def add_row(df: pd.DataFrame, add_rules: dict[str: dict[str: list[dict[str: str]]]], log_columns: list[str]) -> pd.DataFrame:
    """
    根据某列的值进行筛选，并通过规则增加行。

    :param df: 输入的 DataFrame
    :param add_rules: 增加行的规则字典，例如 {"列名": {"值": [{"新列名": "新值", ...}, ...]}}
    :param log_columns: 用于打印日志的列名列表
    :return: 增加行后的 DataFrame
    """
    df_t = df.copy()

    # 创建一个空 DataFrame 用于存储新增的行
    new_rows = pd.DataFrame(columns=df_t.columns)
    matched_rows_4log = pd.DataFrame(columns=df_t.columns)
    
    # 遍历规则
    def alter_row(row, alter_rule: dict):
        for new_col, new_val in alter_rule.items():
            row[new_col] = new_val
        return row

    for column, rules in add_rules.items():
        for value, new_row_data_list in rules.items():
            # 筛选出符合条件的行
            mask = df_t[column].astype(str).str.contains(value, regex=True, na=False, flags=re.IGNORECASE)
            if mask.any():
                matched_rows = df_t[mask]
                matched_rows_4log = pd.concat([matched_rows_4log, matched_rows], ignore_index=True, axis=0)
                
                # 为每个匹配的行生成新行
                for new_row_data in new_row_data_list:
                    new_matched_rows = matched_rows.apply(alter_row, alter_rule=new_row_data, axis=1)
                    new_rows = pd.concat([new_rows, new_matched_rows], ignore_index=True)
    
    # 打印新增的行的日志信息
    if not new_rows.empty:
        log_df(matched_rows_4log[log_columns], f"【增加行】根据 '{add_rules}' 匹配到的行: 数量={matched_rows_4log.shape[0]}", level='info')
        log_df(new_rows[log_columns], f"【增加行】新增的行: 数量={new_rows.shape[0]}", level='info')
    else:
        log(f"【增加行】根据 '{add_rules}' 匹配到的行: 数量=0", level='info')
    
    # 将新行追加到原始 DataFrame 中
    df_t = pd.concat([df_t, new_rows], ignore_index=True)
    
    return df_t


"""根据改列值规则，进行某列的筛选和改值。"""
def alter_val(df: pd.DataFrame, alter_rules: dict[str: dict[str: str]], log_columns: list[str]):
    '''{'MSKU': {'原MSKU': {'品名': '新品名', 'MSKU': '新MSKU'}}},
    log_columns仅为日志输出
    '''
    df_t = df.copy()

    def alter_row(row, alter_rule: dict):
        for new_col, new_val in alter_rule.items():
            row[new_col] = new_val
        return row

    mask_total = pd.Series(False, index=df_t.index)  # 仅作日志使用
    columns_altered = list(set(k3 for v1 in alter_rules.values() for v2 in v1.values() for k3 in v2.keys()))  # 仅作日志使用
    columns_by = list(k for k in alter_rules.keys())  # 仅作日志使用

    for column, rules in alter_rules.items():
        for value, alter_row_data_dict in rules.items():
            # 筛选出符合条件的行
            mask = df_t[column].astype(str).str.contains(value, regex=True, na=False, flags=re.IGNORECASE)

            if mask.any():
                mask_total |= mask
                matched_rows = df_t[mask]
                df_t[mask] = matched_rows.apply(alter_row, alter_rule=alter_row_data_dict, axis=1)

    # 打印日志
    if mask_total.any():
        df_by = df.loc[mask_total, columns_by]
        df_static = df.loc[mask_total, list(set(log_columns) - set(columns_altered) - set(columns_by))]
        df_before = df.loc[mask_total, columns_altered].copy().rename(columns=lambda x: f"before_{x}")
        df_after = df_t.loc[mask_total, columns_altered].copy().rename(columns=lambda x: f"after_{x}")
        df_comparison = pd.concat([df_by, df_before, df_after, df_static], axis=1)
        log_df(df_comparison, f"【改列值】根据改值规则 '{alter_rules}', 修改如下: 行数={df_comparison.shape[0]}")
    else:
        log(f"【改列值】根据改值规则 '{alter_rules}', 修改如下: 行数=0")

    return df_t


"""分仓"""
def split(df: pd.DataFrame, split_rules: list[dict[str: str]], extract: bool, log_columns: list, name: str):
    '''  split_rules: [{'品名': '', 'MSKU': ''}, {'其他列': ''}]  '''
    df_t = df.copy()

    mask0 = pd.Series(False, index=df_t.index)
    for rule in split_rules:
        mask1 = pd.Series(True, index=df_t.index)
        for column, value in rule.items():
            mask2 = df_t[column].astype(str).str.contains(value, regex=True, na=False, flags=re.IGNORECASE)
            mask1 &= mask2

        mask0 |= mask1
    
    # 打印日志
    log_df(df_t.loc[mask0, log_columns], f"【分割: {name}】规则='{split_rules}' extract={extract} 数量={sum(mask0)}")
    
    if extract:
        return df_t[mask0].copy(), df_t[~mask0]
    else:
        return df_t[mask0].copy(), df_t
    

"""格式化表"""
def format(df: pd.DataFrame, format_rules: dict, columns: list, log_columns: list, name: str):
    ''' {'copy': [['城市', '其他列'], ],
         'constant': [['城市', '其他列']],
         'concat': [['城市', , ]],
         'None': [['城市', , ]]
         } 
    '''
    df_t = pd.DataFrame(columns=columns, index=df.index)

    if not df.empty:
        for action_t, list1 in format_rules.items():
            action = action_t.lower()
            if action == 'copy':
                columns1, columns2 = [v[0] for v in list1], [v[1] for v in list1]
                df_t[columns1] = df[columns2]
            elif action == 'constant':
                columns1, columns2 = [v[0] for v in list1], [v[1] for v in list1]
                df_t[columns1] = columns2
                # for column, value in zip(columns, list2):
                #     df_t[column] = value
            elif action == 'concat':
                for list2 in list1:
                    column, columns_cat = list2[0], list2[1:]
                    df_t[column] = df[columns_cat].fillna("").astype('str').apply(lambda x: ' '.join(x).strip(), axis=1)
            elif action == 'None':
                continue
            else:
                continue
    
    # 打印日志
    log(f"【格式化构造新表: {name}】行数={df_t.shape[0]}, 列数={df_t.shape[1]}")

    return df_t


def export(df: pd.DataFrame, export_dtype: dict, name: str, suffix: str, count_cols: list):
    today = datetime.now().strftime('%m.%d')
    today = '.'.join([i.lstrip('0 ') for i in today.split('.')])
    count = df[count_cols].drop_duplicates().shape[0] if count_cols != [] else df.shape[0]
    fpath = f"data/{today} {name} {count}单{suffix}.xlsx"

    set_df_dtype(df, export_dtype, name)
    write_excel(df, fpath)
    log(f"【写表: {name}】已写入 '{fpath}'")


"""增加或填充一列"""
def add_col(df: pd.DataFrame, add_rules: dict, log_columns: list, name: str):
    '''
    add_rules: {'仓库代码/Warehouse Code': 
        {
            "WPLA16": [
                {"品名": "(?=.*喷壶)(?=.*(?:蓝|黑黄|橙色|317|灰色|灰红)).*"},
                {}
            ]
        }
    }
    '''
    df_t = df.copy()

    for add_column, dict1 in add_rules.items():
        if add_column not in df_t.columns:
            df_t[add_column] = None
        
        for add_value, list2 in dict1.items():
            mask2 = pd.Series(False, index=df_t.index)

            for and_dict in list2:
                mask1 = pd.Series(True, index=df_t.index)

                for by_column, by_value in and_dict.items():
                    mask0 = df_t[by_column].astype(str).str.contains(by_value, regex=True, na=False, flags=re.IGNORECASE)
                    # and 和
                    mask1 &= mask0
                
                mask2 |= mask1 
                
            
            # 改值
            mask2 &= pd.isna(df_t[add_column])
            if mask2.any():
                df_t.loc[mask2, [add_column]] = add_value
        
        # 检查 add_column 列是否还有空值
        log(f"【增加或补充一列: {name}】增加的列={add_column}, 空值数量={df_t[add_column].isna().sum()}", level='info')

    return df_t


def concat_df(input: list[pd.DataFrame], axis: str):
    axis = 1 if axis == "横向" else 0
    df = pd.concat(input, axis=axis)
    log(f"【拼接两个表格】axis={axis}, 行数={df.shape[0]},列数={df.shape[1]}")
    return df

    
    







