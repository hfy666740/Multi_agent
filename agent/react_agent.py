
from langchain.agents import create_agent
from model.factory import chat_model
from agent.tool.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                    get_current_month, fetch_external_data,fill_context_for_report)
from utils.prompt_loader import load_system_prompt
from agent.tool.middleware import monitor_tool, log_before_model, report_prompt_switch



class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompt(),
            tools=[rag_summarize, get_weather, get_user_location, get_user_id,
            get_current_month, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch]
    )

    def execute_stream(self, query:str):
        input_dict={
            "messages":[
                {"role":"user","content":query}
            ]
        }

        #第三个参数context就是上下文runtime中的信息，就是我们做提示词切换的标记
        previous_content = ""
        for chunk in self.agent.stream(input_dict,stream_mode="values",context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                current_content = latest_message.content.strip()
                # 只返回新增的部分
                new_content = current_content[len(previous_content):]
                previous_content = current_content
                if new_content:
                    yield new_content


if __name__ == '__main__':
    agent = ReactAgent()
    query = "扫地机器人在我所在的地区的气温下如何保养"
    for chunk in agent.execute_stream(query):
        print(chunk,end="",flush=True)