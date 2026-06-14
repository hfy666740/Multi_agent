"""
logger_handler.py — 统一日志处理器
技术栈: Python logging, RotatingFileHandler (文件轮转)
用途: 配置全局日志系统，支持控制台输出和文件输出
"""
import logging
from bokeh.command.subcommands.serve import DEFAULT_LOG_FORMAT
from datetime import datetime
from utils.path_tool import get_abs_path
import os

#日志保存的根目录
LOG_ROOT = get_abs_path("logs")

#确保日志的目录存在
os.makedirs(LOG_ROOT,exist_ok=True)

#日志的格式配置
DEFAULT_LOG_FORMAT = logging.Formatter(
    '%(asctime)s- %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

def get_logger(
        name = "agent",
        console_level = logging.INFO,
        file_level = logging.DEBUG,
        log_file = None
):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    #避免重复添加Handler
    if logger.handlers:
        return logger

    #控制台Hanlder输出
    console_hanlder = logging.StreamHandler()#创建控制台Handler
    console_hanlder.setLevel(console_level)#设置控制台日志级别
    console_hanlder.setFormatter(DEFAULT_LOG_FORMAT)#设置日志格式

    logger.addHandler(console_hanlder)#将控制台Handler添加到Logger

    #文件Handler输出
    if not log_file:#日志文件路径
        log_file = os.path.join(LOG_ROOT,f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    file_handler = logging.FileHandler(log_file,encoding='utf-8')#创建文件Handler
    file_handler.setLevel(file_level)#设置文件日志级别
    file_handler.setFormatter(DEFAULT_LOG_FORMAT)#设置日志格式

    logger.addHandler(file_handler)#将文件Handler添加到Logger

    return logger

#快捷获取默认日志记录器
logger = get_logger()

if __name__ == '__main__':
    logger.info("信息日志")
    logger.error("错误日志")
    logger.warning("警告日志")
    logger.debug("调试日志")







