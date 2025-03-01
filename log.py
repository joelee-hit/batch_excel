import logging
from sys import stdout
import pandas as pd
import os

# 自定义过滤器类，用于限制只记录特定级别的日志
class LogLevelFilter(logging.Filter):
    def __init__(self, level):
        self.level = level

    def filter(self, record):
        return record.levelno == self.level

def apply_pd_settings():
    pd.set_option('display.max_rows', None)  # 显示所有行
    pd.set_option('display.max_columns', None)  # 显示所有列
    pd.set_option('display.width', None)  # 取消列宽限制
    pd.set_option('display.max_colwidth', None)  # 显示完整列内容 

def restore_pd_settings():
    pd.reset_option('display.max_rows')
    pd.reset_option('display.max_columns')
    pd.reset_option('display.width')
    pd.reset_option('display.max_colwidth')

def setup_logger():
    # 创建相关文件夹
    os.makedirs("data",exist_ok=True)
    os.makedirs("log", exist_ok=True)
    os.makedirs("config", exist_ok=True)
    # 创建日志记录器
    logger = logging.getLogger('my_logger')
    logger.setLevel(logging.INFO)  # 设置最低日志级别为DEBUG
    
    # 创建处理器并设置日志级别
    simple_handler = logging.FileHandler('log/简单日志.txt', mode='w', encoding="utf-8")  # 覆写模式
    simple_filter = LogLevelFilter(logging.INFO)
    simple_handler.addFilter(simple_filter)

    standard_handler = logging.FileHandler('log/标准日志.txt', mode='a', encoding="utf-8")  # 默认追加模式
    standard_handler.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler(stdout)
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器并将它们添加到处理器
    formatter = logging.Formatter('%(asctime)s - %(levelname)s : %(message)s\n')
    simple_handler.setFormatter(formatter)
    standard_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 将处理器添加到日志记录器
    logger.addHandler(simple_handler)
    logger.addHandler(standard_handler)
    logger.addHandler(console_handler)

    # pandas 输出设置
    apply_pd_settings()
    
    return logger

# 配置日志记录器
logger = setup_logger()

######
# 日志工具函数
######

# 打印 普通信息
def log(msg: str, level='info'):
    """
    打印普通信息到日志文件中。
    
    参数:
    msg (str): 要打印的普通信息。
    level (str): 日志级别('debug', 'info', 'warning', 'error')。
    """
    if level.lower() == 'debug':
        logger.debug(msg)
    elif level.lower() == 'info':
        logger.info(msg)
    elif level.lower() == 'warning':
        logger.warning(msg)
    elif level.lower() == 'error':
        logger.error(msg)
    else:
        raise ValueError(f"未知的日志级别: {level}")


# 打印 DataFrame
def log_df(df: pd.DataFrame, prefix='DataFrame内容:', level='info'):
    """
    打印DataFrame的信息到日志文件中。
    
    参数:
    df (pd.DataFrame): 要打印的DataFrame。
    level (str): 日志级别('debug', 'info', 'warning', 'error')。
    """
    # 将DataFrame转换为字符串以便于日志记录
    df_string = f'{prefix}\n{df.to_string()}'
    log(df_string, level)
    
    
