"""
agent_tools.py — Agent 工具函数集合
技术栈: LangChain (Tool 装饰器), RAG (检索增强生成), DashScope (天气API)
用途: 定义所有 Agent 可调用的外部工具函数（RAG 检索、天气查询、报告生成等）
"""
import os.path
import sys
from utils.logger_handler import logger
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
import random
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path
import requests
import yaml
from utils.config_handler import tool_conf
# 直接加载工具配置


rag = RagSummarizeService()

user_ids = ['1001', '1002', '1003', '1004', '1005', '1006', '1007', '1008', '1009', '1010']
month_arr = ['2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06',
             '2025-07', '2025-08', '2025-09', '2025-10', '2025-11', '2025-12']
external_data = {}

@tool(description="从向量存储中检索参考资料")
def rag_summarize(query:str)->str:
    return rag.rag_summarize(query)


def city_to_adcode(city_name: str) -> str | None:
    """调用高德地理编码API，将城市名转换为adcode"""
    geo_url = "https://restapi.amap.com/v3/geocode/geo"
    params = {
        "key": tool_conf["GaoDe"],
        "address": city_name,
        "output": "json"
    }
    try:
        resp = requests.get(geo_url, params=params, timeout=5)
        data = resp.json()
        if data["status"] == "1" and data["geocodes"]:
            return data["geocodes"][0]["adcode"]
        else:
            return None
    except Exception:
        return None


def get_ip_city() -> str:
    """通过IP定位获取当前城市"""
    try:
        # 使用 ipinfo.io 获取城市
        resp = requests.get("https://ipinfo.io/json", timeout=5)
        data = resp.json()
        city = data.get("city", "武汉")
        logger.info(f"[IP定位] 获取到城市: {city}")
        return city
    except Exception as e:
        logger.warning(f"[IP定位] 获取失败，使用默认城市: {str(e)}")
        return "武汉"
    

@tool(description="获取指定城市的天气，以消息字符串的形式返回，如不指定城市则自动获取用户所在城市")
def get_weather(city_name: str = None) -> str:
    """
    查询指定城市的实时天气信息。
    参数 city_name: 城市名称，例如"北京"、"上海"、"广州"。如果不传则自动获取用户所在城市。
    返回格式化的天气字符串，包含天气现象、温度、湿度、风向风力、体感温度等信息。
    """
    # 如果不传城市名，则获取用户当前位置
    if not city_name:
        city_name = get_ip_city()
        logger.info(f"[get_weather] 自动获取用户位置: {city_name}")
    
    # 1. 将城市名转换为adcode
    adcode = city_to_adcode(city_name)
    if not adcode:
        return f"错误：无法识别城市 '{city_name}'，请检查城市名称是否正确。"

    # 2. 调用高德天气API - 先获取实时天气
    weather_url = "https://restapi.amap.com/v3/weather/weatherInfo"
    params_base = {
        "key": tool_conf["GaoDe"],
        "city": adcode,
        "output": "json"
    }
    try:
        # 获取实时天气
        params_base["extensions"] = "base"
        resp = requests.get(weather_url, params=params_base, timeout=5)
        data = resp.json()
        if data["status"] != "1":
            return f"天气查询失败：{data.get('info', '未知错误')}"

        live = data["lives"][0]
        # 城市名称优先使用工具传入的参数（因为高德返回的可能是拼音或简称）
        display_city = city_name if city_name else live['city']
        result = (
            f"=== 实时天气 ===\n"
            f"查询城市：{display_city}\n"
            f"当前天气：{live['weather']}\n"
            f"当前温度：{live['temperature']}℃\n"
            f"当前湿度：{live['humidity']}%\n"
            f"当前风向：{live['winddirection']}\n"
            f"当前风力：{live['windpower']}级\n"
            f"数据更新时间：{live['reporttime']}"
        )

        # 获取天气预报（含体感温度等更多信息）
        params_base["extensions"] = "all"
        resp_forecast = requests.get(weather_url, params=params_base, timeout=5)
        forecast_data = resp_forecast.json()
        if forecast_data["status"] == "1" and forecast_data.get("forecasts"):
            forecast = forecast_data["forecasts"][0]
            cast_list = forecast.get("casts", [])
            if cast_list:
                today = cast_list[0]
                result += (
                    f"\n\n=== 今日天气预报 ===\n"
                    f"白天温度：{today['daytemp']}℃\n"
                    f"夜间温度：{today['nighttemp']}℃\n"
                    f"白天天气：{today['dayweather']}\n"
                    f"夜间天气：{today['nightweather']}\n"
                    f"白天风向：{today['daywind']}\n"
                    f"白天风力：{today['daypower']}级"
                )

        return result
    except Exception as e:
        return f"天气查询过程中发生异常：{str(e)}"


@tool(description="获取当用户所在城市的名称，以纯字符串的形式返回")
def get_user_location()->str:
    return get_ip_city()


@tool(description="获取用户的ID，以纯字符串的形式返回")
def get_user_id()->str:
    return random.choice(user_ids)


@tool(description="获取当前月份，以纯字符串的形式返回")
def get_current_month()->str:
    return random.choice(month_arr)


@tool(description="从外部系统中获取指定用户在指定月份的使用记录，以纯字符串的形式返回，如果未检索到返回空字符串")
def fetch_external_data(user_id:str,month:str)->str:
    pass


def generate_external_data()->str:
    '''
    {
    "user_id": {
        "month": {"用户1001在2025-01月使用了工具A、工具B、工具C"},
        "month": "用户1001在2025-02月使用了工具A、工具D",
        ...
        }
    }
    :param user_id:
    :param month:
    :return:
    '''
    if not external_data:
        external_data_path=get_abs_path(agent_conf['external_data_path'])

        if not os.path.exists(external_data_path):
            raise FileNotFoundError(f"外部数据文件不存在，路径：{external_data_path}不存在")

        with open(external_data_path, 'r', encoding='utf-8') as f:
            for line in f.readlines()[1:]:  # 跳过第一行表头
                arr:list[str] = line.strip().split(",")

                user_id:str = arr[0].replace('"', '')
                feature:str = arr[1].replace('"', '')
                efficiency:str = arr[2].replace('"', '')
                consumables:str = arr[3].replace('"', '')
                compartson:str = arr[4].replace('"', '')
                time:str = arr[5].replace('"', '')

                if user_id not in external_data:
                    external_data[user_id] = {}

                    external_data[user_id][time] = {
                        "特征": feature,
                        "效率": efficiency,
                        "耗材": consumables,
                        "对比": compartson
                    }

@tool(description="从外部系统中获取指定用户在指定月份的使用记录，以纯字符串的形式返回，如果未检索到返回空字符串")
def fetch_external_data(user_id:str,month:str)->str:
    generate_external_data()

    try:
        return external_data[user_id][month]
    except KeyError:
        logger.warning(f"[fetch_external_data]未检索到用户{user_id}在{month}的使用记录")
        return ""

@tool(description="填充上下文信息，注入report=True")
def fill_context_for_report():
    return "fill context for report已调用"
