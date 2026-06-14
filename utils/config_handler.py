"""
config_handler.py — 统一配置加载器
技术栈: PyYAML (YAML解析), os.environ (环境变量)
用途: 从 config/ 目录加载 YAML 配置文件，提供全局配置对象
"""
import os
import sys

# # 直接运行本文件时（如 python utils/config_handler.py），sys.path 不含项目根目录，
# # 会导致 `from utils.xxx` 失败；先把项目根目录加入 sys.path。
# _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if _PROJECT_ROOT not in sys.path:
#     sys.path.insert(0, _PROJECT_ROOT)

import yaml

from utils.path_tool import get_abs_path
def load_rag_config(config_path:str = get_abs_path("config/rag.yml"),encoding:str = "utf-8") -> dict:
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.full_load(f)


def load_chroma_config(config_path:str = get_abs_path("config/chroma.yml"),encoding:str = "utf-8") -> dict:
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.full_load(f)


def load_prompts_config(config_path:str = get_abs_path("config/prompts.yml"),encoding:str = "utf-8") -> dict:
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.full_load(f)


def load_agent_config(config_path:str = get_abs_path("config/agent.yml"),encoding:str = "utf-8") -> dict:
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.full_load(f)


def load_database_config(config_path:str = get_abs_path("config/database.yml"),encoding:str = "utf-8") -> dict:
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.full_load(f)

def tool_config(config_path:str = get_abs_path("config/tool.yml"),encoding:str = "utf-8") -> dict:
    with open(config_path, 'r', encoding=encoding) as f:
        return yaml.full_load(f)

rag_conf = load_rag_config()
tool_conf = tool_config()
chroma_conf = load_chroma_config()
prompts_conf = load_prompts_config()
agent_conf = load_agent_config()
database_conf = load_database_config()


if __name__ == '__main__':
    print(rag_conf['chat_model_name'])

















