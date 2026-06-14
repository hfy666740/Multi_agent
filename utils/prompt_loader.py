"""
prompt_loader.py — Prompt 统一加载器
技术栈: Python I/O (文件读取), YAML 配置 (prompts.yml)
用途: 从 prompt/ 目录加载各 Agent 提示词文件
"""
from utils.config_handler import prompts_conf
from utils.path_tool import get_abs_path
from utils.logger_handler import logger
def load_system_prompt():
    try:
        system_prompt_path = get_abs_path(prompts_conf['main_prompt_path'])
    except KeyError as e:
        logger.error(f"[load_system_prompt]在yaml配置项中没有main_prompt_path配置项")
        raise e

    try:
        return open(system_prompt_path, 'r', encoding='utf-8').read()
    except Exception as e:
        logger.error(f"[load_system_prompt]加载系统提示词system失败，错误信息：{str(e)}")
        raise e


def load_rag_prompt():
    try:
        rag_prompt_path = get_abs_path(prompts_conf['rag_summarize_prompt_path'])
    except KeyError as e:
        logger.error(f"[load_rag_prompt]在yaml配置项中没有rag_summarize_prompt_path配置项")
        raise e

    try:
        return open(rag_prompt_path, 'r', encoding='utf-8').read()
    except Exception as e:
        logger.error(f"[load_rag_prompt]加载系统提示词rag失败，错误信息：{str(e)}")
        raise e


def load_report_prompt():
    try:
        report_prompt_path = get_abs_path(prompts_conf['report_prompt_path'])
    except KeyError as e:
        logger.error(f"[load_report_prompt]在yaml配置项中没有report_prompt_path配置项")
        raise e

    try:
        return open(report_prompt_path, 'r', encoding='utf-8').read()
    except Exception as e:
        logger.error(f"[load_report_prompt]加载系统提示词report失败，错误信息：{str(e)}")
        raise e
    

def supervisor_load_prompt():
    try:
        supervisor_prompt_path = get_abs_path(prompts_conf['supervisor_prompt_path'])
    except KeyError as e:
        logger.error(f"[Supervisor_load_prompt]在yaml配置项中没有supervisor_prompt_path配置项")
        raise e

    try:
        return open(supervisor_prompt_path, 'r', encoding='utf-8').read()
    except Exception as e:
        logger.error(f"[Supervisor_load_prompt]加载系统提示词supervisor失败，错误信息：{str(e)}")
        raise e
    
def knowledge_load_prompt():
    try:
        knowledge_prompt_path = get_abs_path(prompts_conf['knowledge_prompt_path'])
    except KeyError as e:
        logger.error(f"[knowledge_load_prompt]在yaml配置项中没有knowledge_prompt_path配置项")
        raise e

    try:
        return open(knowledge_prompt_path, 'r', encoding='utf-8').read()
    except Exception as e:
        logger.error(f"[knowledge_load_prompt]加载系统提示词knowledge失败，错误信息：{str(e)}")
        raise e
    
def weather_load_prompt():
    try:
        weather_prompt_path = get_abs_path(prompts_conf['weather_prompt_path'])
    except KeyError as e:
        logger.error(f"[weather_load_prompt]在yaml配置项中没有weather_prompt_path配置项")
        raise e

    try:
        return open(weather_prompt_path, 'r', encoding='utf-8').read()
    except Exception as e:
        logger.error(f"[weather_load_prompt]加载系统提示词weather失败，错误信息：{str(e)}")
        raise e

if __name__ == '__main__':
    print(load_system_prompt())
    # print(load_rag_prompt())
    # print(load_report_prompt())
