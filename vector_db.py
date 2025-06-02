from langchain_ollama import OllamaEmbeddings
import os
import json
import pandas as pd
import chromadb
import re

# 從環境變數取得檔案路徑
RAG_FILE_PATH = os.getenv('RAG_FILE_PATH')

class ChromaDBEmbeddingFunction:
    """讓 ChromaDB 使用 Ollama 進行嵌入"""
    def __init__(self, langchain_embeddings):
        self.langchain_embeddings = langchain_embeddings

    def __call__(self, input):
        if isinstance(input, str):
            input = [input]
        return self.langchain_embeddings.embed_documents(input)


# 清理 Excel 不接受的控制字元
def clean_illegal_chars(val):
    if isinstance(val, str):
        # 移除非法控制字元（Unicode U+0000 到 U+001F 與 U+007F）
        return re.sub(r"[\x00-\x1F\x7F]", "", val)
    return val


def get_embedding_function():
    Embedding_model = "mxbai-embed-large"
    return ChromaDBEmbeddingFunction(
        OllamaEmbeddings(
            model=Embedding_model,
            base_url="http://localhost:11434"
        )
    )


def init_chroma_client():
    chroma_db_path = os.path.join(os.getcwd(), "chroma_db")
    os.makedirs(chroma_db_path, exist_ok=True)
    client = chromadb.PersistentClient(path=chroma_db_path)
    return client

def init_collections(client):
    embedding = get_embedding_function()
    text_collection = client.get_or_create_collection(
        name="rag_text_collection",
        metadata={"description": "PDF 文字內容向量資料庫", "hnsw:sync_threshold": 20000},
        embedding_function=embedding
    )
    image_collection = client.get_or_create_collection(
        name="rag_image_collection",
        metadata={"description": "PDF 圖片描述向量資料庫", "hnsw:sync_threshold": 20000},
        embedding_function=embedding
    )
    return text_collection, image_collection

def check_collection_data(collection):
    collection_name = collection.name
    existing_data = collection.get()
    num_records = len(existing_data["ids"]) if "ids" in existing_data else 0
    if num_records > 0:
        print(f"[INFO] 向量資料庫 '{collection_name}' 已存在 {num_records} 筆資料")
    else:
        print(f"[INFO] 向量資料庫 '{collection_name}' 為空")

def fetch_collection_data(collection):
    data = collection.get()
    ids = data.get("ids", [])
    documents = data.get("documents", [])
    metadatas = data.get("metadatas", [])
    # 將 metadatas 轉為 JSON 字串
    metadatas = [json.dumps(meta, ensure_ascii=False) for meta in metadatas]
    return list(zip(ids, documents, metadatas))

def save_to_excel(text_data, image_data, output_file="vector_database.xlsx"):
    text_df = pd.DataFrame(text_data, columns=["ID", "Content", "Metadata"])
    image_df = pd.DataFrame(image_data, columns=["ID", "Content", "Metadata"])
    # 對整個 DataFrame 的每個 cell 清除非法字元
    text_df = text_df.applymap(clean_illegal_chars)
    image_df = image_df.applymap(clean_illegal_chars)
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        text_df.to_excel(writer, sheet_name="Text Data", index=False)
        image_df.to_excel(writer, sheet_name="Image Data", index=False)
    print(f"[INFO] 向量資料已成功存入 {output_file}")

def add_documents_to_collection(collection, documents, ids, metadatas=None):
    print(f"[INFO] 正在新增 {len(documents)} 筆資料到 '{collection.name}'")
    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    print(f"[INFO] 新增成功！")

def delete_documents_from_collection(collection, deleted_files):
    if not deleted_files:
        return
    for pdf_path in deleted_files:
        file_name = os.path.basename(pdf_path)
        results = collection.get()
        if "ids" in results and "metadatas" in results:
            ids_to_delete = [
                doc_id for doc_id, metadata in zip(results["ids"], results["metadatas"])
                if metadata.get("file_name") == file_name
            ]
            if ids_to_delete:
                collection.delete(ids=ids_to_delete)
                print(f"[INFO] 從 '{collection.name}' 刪除 {len(ids_to_delete)} 筆資料 (來源: {file_name})")
            else:
                print(f"[INFO] '{file_name}' 在 '{collection.name}' 中無對應資料")
