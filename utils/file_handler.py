"""
file_handler.py — 文件处理工具集
技术栈: LangChain Document Loaders (PDF/TXT), hashlib (MD5校验)
用途: 文件读写、格式检测、MD5 校验、文档加载
"""
import os
import hashlib
from utils.logger_handler import logger
from langchain_core.documents import Document
from langchain_community.document_loaders import PythonLoader, TextLoader, PyPDFLoader


def get_file_md5(filepath:str) -> str: # 计算文件的MD5的十六进制字符串
    if not os.path.exists(filepath):
        logger.error(f"[md5计算]文件{filepath}不存在")
        return ""

    if not os.path.isfile(filepath):
        logger.error(f"[md5计算]路径{filepath}不是文件")
        return ""

    md5_obj = hashlib.md5()

    chunk_size = 4096
    try:
        with open(filepath, "rb") as f:
            while chunk:= f.read(chunk_size):
                md5_obj.update(chunk)
        return md5_obj.hexdigest()
    except Exception as e:
        logger.error(f"计算文件{filepath}md5失败. {str(e)}")
        return None


def listdir_with_allowed_type(dir_path, allowed_extensions):    #返回文件夹内的文件列表
    """
    列出指定目录下所有扩展名在 allowed_extensions 中的文件路径
    :param dir_path: 目录路径
    :param allowed_extensions: 允许的扩展名元组，例如 ('.txt', '.pdf') 或 ('txt', 'pdf')
    :return: 符合条件的文件绝对路径列表
    """
    if not os.path.isdir(dir_path):
        logger.error(f"[listdir_with_allowed_type]{dir_path} 不是一个目录")
        return []

    files = []
    for filename in os.listdir(dir_path):
        full_path = os.path.join(dir_path, filename)
        if not os.path.isfile(full_path):     # 如果是目录就跳过
            continue
        # 获取文件扩展名（带点）
        ext = os.path.splitext(filename)[1].lower()
        # 兼容配置中扩展名带点或不带点的情况
        if ext and ext[1:] in allowed_extensions or ext in allowed_extensions:
            files.append(os.path.abspath(full_path))
    return files



def pdf_loader(file_path:str,passwd=None) -> list[Document]:
    try:
        return PyPDFLoader(file_path,password=passwd).load()
    except ImportError:
        logger.error("pypdf 包未安装，请运行: pip install pypdf")
        raise
    except Exception as e:
        logger.error(f"加载PDF文件失败: {str(e)}")
        raise


def txt_loader(file_path:str) -> list[Document]:
    return TextLoader(file_path, encoding='utf-8').load()
