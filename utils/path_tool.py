"""
为整个工程提供统一的绝对路径
"""
"""
path_tool.py — 路径工具
技术栈: os.path (路径处理)
用途: 提供统一的绝对路径解析，确保各模块路径引用一致
"""
import os

def get_project_root():
    #当前文件得我绝对路径
    current_file = os.path.abspath(__file__)

    #获取工程的根目录，先取文件所在的文件夹的绝对路径
    current_dir = os.path.dirname(current_file)

    #获取工程根目录
    project_root = os.path.dirname(current_dir)

    return project_root

def get_abs_path(relative_path:str):
    """
    :param relative_path()
    :return: 绝对路径
    """

    project_root = get_project_root()
    return os.path.join(project_root,relative_path)

if __name__ == '__main__':
    print(get_abs_path("config/config.txt"))
