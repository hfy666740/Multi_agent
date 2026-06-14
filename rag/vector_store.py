import os.path
from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.config_handler import chroma_conf
from model.factory import chat_model, embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
import os
from utils.file_handler import pdf_loader, txt_loader,listdir_with_allowed_type,get_file_md5
from utils.logger_handler import logger
from rag.keyword_retriever import KeywordRetriever
from rag.hybrid_retriever import HybridRetriever

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf['collection_name'],
            embedding_function=embed_model,
            persist_directory=get_abs_path(chroma_conf['persist_directory'])# 这里可以根据需要设置持久化目录        

        )
        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf['chunk_size'],
            chunk_overlap=chroma_conf['chunk_overlap'],
            separators=chroma_conf['separators'],
            length_function=len
        )
        self.keyword_retriever = KeywordRetriever()

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf['k']})

    def get_hybrid_retriever(self):
        """获取混合检索器（语义+关键词）"""
        return HybridRetriever(
            semantic_retriever=self.get_retriever(),
            keyword_retriever=self.keyword_retriever
        )

    def load_documents(self):  # 加载知识库
        def check_md5_hex(md5_for_check:str):
            if not os.path.exists(get_abs_path(chroma_conf['md5_hex_store'])):
                open(get_abs_path(chroma_conf['md5_hex_store']), 'w',encoding="utf-8").close()  # 创建空文件
                return False  # 如果文件不存在，说明没有存储过MD5值，直接返回False
            with open(get_abs_path(chroma_conf['md5_hex_store']), 'r', encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True  # 如果找到匹配的MD5值，返回True
            return False  # 如果没有找到匹配的MD5值，返回False

        def save_md5_hex(md5_hex:str):
            with open(get_abs_path(chroma_conf['md5_hex_store']), 'a', encoding="utf-8") as f:
                f.write(md5_hex + "\n")  # 将新的MD5值写入文件，换行分隔

        def get_file_documents(read_path:str):
            if read_path.endswith('.pdf'):
                return pdf_loader(read_path)
            if read_path.endswith('.txt'):
                return txt_loader(read_path)

            return []

        allowed_files_path:list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf['data_path']),
            tuple(chroma_conf['allow_knowledge_file_type'])
        )

        for path in allowed_files_path:
            md5_hex = get_file_md5(path)
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path} 已经存在知识库内，跳过。")
                continue  # 如果MD5值已经存在，说明文件已经处理过，跳过

            try:
                documents:list[Document] = get_file_documents(path)
                if not documents:
                    logger.warning(f"[加载知识库]无法加载文档 {path}，分片后没有有效文本内容。跳过")
                    continue  # 如果无法加载文档，跳过


                split_document:list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库] {path}，分片后没有有效文本内容。跳过")
                    continue  # 如果无法分割文档，跳过

                self.vector_store.add_documents(split_document)
                # 同步构建BM25关键词检索索引
                self.keyword_retriever.build_index(split_document)
                save_md5_hex(md5_hex)  # 保存新的MD5值以避免重复处理

                logger.info(f"[加载知识库]成功加载文档 {path}，并添加到知识库中。")

            except Exception as e:
                #exc_info=True参数会在日志中输出完整的异常堆栈信息，帮助我们更好地定位问题
                logger.error(f"[加载知识库]加载文档 {path} 失败：{str(e)}",exc_info=True)
                continue  # 如果加载文档时发生错误，跳过该文件继续处理下一个文件

if __name__ == '__main__':
    vs = VectorStoreService()
    vs.load_documents()
    print('知识库加载完成')