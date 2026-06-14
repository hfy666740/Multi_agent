"""
总结服务类：用户提问，调用检索服务获取相关文档，使用生成模型生成答案。
"""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser

from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompt
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model


def print_prompt(prompt):
    print("**********prompt start**********")
    print(prompt.to_string())
    print("**********prompt end**********")
    return prompt

class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        # 使用混合检索（语义+关键词），可通过 rag.yml 的 retrieval_mode 配置切换
        from utils.config_handler import rag_conf
        if rag_conf.get('retrieval_mode', 'semantic') == 'hybrid':
            self.retriever = self.vector_store.get_hybrid_retriever()
        else:
            self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompt()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    def _init_chain(self):
        chain = self.prompt_template | print_prompt | self.model | StrOutputParser()
        return chain

    def retrieve_docs(self, query:str)->list[Document]:
        return self.retriever.invoke(query)

    def rag_summarize(self, query:str)->str:
        context_docs = self.retrieve_docs(query)
        context = ''
        counter = 0
        for doc in context_docs:
            counter += 1
            context += f"\n参考资料{counter}：参考资料：{doc.page_content} | 参考元数据：{doc.metadata}\n"

        return self.chain.invoke(
            {
                'input': query,
                'context': context
             }
        )

if __name__ == '__main__':
    rag_service = RagSummarizeService()
    query = "小户型适合哪些扫地机器人"
    answer = rag_service.rag_summarize(query)
    print(answer)