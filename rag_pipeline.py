import os
import re
import json
import uuid
from azure_tool import generate_with_openai
import pdf_chunker

# 從環境變數取得檔案路徑
RAG_FILE_PATH = os.getenv('RAG_FILE_PATH')


import json
import os
from azure_tool import generate_with_openai


def generate_alternatives_and_keywords(query):
    """
    使用 Azure OpenAI 同時生成三個檢索查詢變體與三個對應關鍵字
    回傳格式：
        queries: ["查詢版本1", "查詢版本2", "查詢版本3"],
        keywords: ["關鍵字1", "關鍵字2", "關鍵字3"]
    如果呼叫失敗、被 Content Filter 擋掉或解析 JSON 失敗，則回傳 ([], [])。
    """
    # 系統提示：定義 Assistant 行為和固定 JSON 輸出格式
    system_prompt = """
        你是一個 AI 助手，負責根據用戶輸入的問題，同時完成兩件事：
        1. 生成三個不同版本的檢索查詢（alternative queries）
        2. 從原始問題中抽取三個最能代表核心意圖或主題的關鍵字（keywords）

        請嚴格遵循以下 JSON 格式輸出，不要包含其他說明：
        {
        "queries": [
            "查詢版本1",
            "查詢版本2",
            "查詢版本3"
        ],
        "keywords": [
            "關鍵字1",
            "關鍵字2",
            "關鍵字3"
        ]
        }
    """
    # 使用者提示：僅放原始問題
    user_prompt = f"原始問題: \"{query}\""

    try:
        # 呼叫 Azure OpenAI，先傳 system，再傳 user
        result = generate_with_openai(
            text_prompt=user_prompt,
            system_prompt=system_prompt
        )
    except Exception as e:
        # 連 API 都出錯（網路、Key 或其他），直接回傳空
        print(f"[ERROR] 呼叫 generate_with_openai 失敗：{e}")
        return [], []

    # 如果 result 為 None 或空字串，代表可能被 Content Filter 過濾掉
    if not result or not result.strip():
        print("[WARN] generate_alternatives_and_keywords：回應為空，可能被 Content Filter 擋掉。")
        return [], []

    # 嘗試解析 JSON
    try:
        data = json.loads(result)
    except json.JSONDecodeError as e:
        print(f"[ERROR] 解析 JSON 失敗，回傳內容：\n{result}\n錯誤：{e}")
        return [], []
    except Exception as e:
        print(f"[ERROR] 解析結果時發生未知錯誤：{e}")
        return [], []

    # 如果解析成功，但裡面沒有預期的 keys，也安全處理
    queries = data.get("queries")
    keywords = data.get("keywords")
    if not isinstance(queries, list) or not isinstance(keywords, list):
        print(f"[WARN] JSON 結構不符預期: {data}")
        return [], []

    # 最後回傳
    return queries, keywords



def query_chromadb(collection, query_text, n_results=1):
    return collection.query(query_texts=[query_text], n_results=n_results)


def rag_query_pipeline(query_text, text_collection, image_collection, dataset_type, ignore_image_processing=False):
    """
    RAG 查詢流程：
    1. 使用 generate_alternatives_and_keywords 取得三個查詢變體與三個關鍵字；
    2. 對文字集合（text_collection）分別使用三個查詢變體與三個關鍵字進行檢索；
    3. 若未忽略圖片，僅對原始 query_text 執行圖片檢索；
    4. 合併文字上下文，（若有）並將圖片路徑傳入 OpenAI 生成最終答案。
    """
    # 生成查詢變體與關鍵字
    alternative_queries, keywords = generate_alternatives_and_keywords(query_text)
    if len(alternative_queries) != 3:
        print("[INFO] 生成的查詢變體不足 3 個，僅使用原始查詢進行檢索。")
        alternative_queries = [query_text]

    print(f"[INFO] 抽取到的關鍵字列表: {keywords}")

    # 聚合文字上下文
    aggregated_texts = []
    seen_text_ids = set()
    all_queries = alternative_queries + keywords
    for q in all_queries:
        text_result = query_chromadb(text_collection, q)
        text_docs = text_result.get("documents", [])
        text_ids = text_result.get("ids", [])
        if text_docs and text_ids:
            current_id = text_ids[0]
            if isinstance(current_id, list):
                current_id = tuple(current_id)
            if current_id not in seen_text_ids:
                context = (
                    " ".join(text_docs[0])
                    if isinstance(text_docs[0], list)
                    else str(text_docs[0])
                )
                aggregated_texts.append(context)
                seen_text_ids.add(current_id)
            else:
                print(f"[DEBUG] 文件 id {current_id} 已存在，跳過重複內容")

    # 僅對原始查詢執行圖片檢索
    selected_image_path = None
    if not ignore_image_processing:
        image_result = query_chromadb(image_collection, query_text)
        image_metadata = image_result.get("metadatas", [])
        if image_metadata and image_metadata[0]:
            image_meta = image_metadata[0][0]
            file_name = image_meta.get("file_name")
            page_num = image_meta.get("page")
            print(f"[INFO] 找到圖片資訊: {file_name} - 第 {page_num} 頁 (原始查詢)")
            full_pdf_path = os.path.join(RAG_FILE_PATH, file_name)
            image = pdf_chunker.pdf_page_to_image(full_pdf_path, page_num)
            hash_name = str(uuid.uuid4())
            image_path = f"./images_data/output_page_{hash_name}.png"
            os.makedirs(os.path.dirname(image_path), exist_ok=True)
            image.save(image_path)
            selected_image_path = image_path

    # 組合文字上下文與問題
    merged_text_context = "\n".join(aggregated_texts)
    if dataset_type == "yes_no":
        # 若為 yes/no 類型，提示詞需限制答案格式，避免模型回傳其他內容
        augmented_prompt = (
            f"背景資訊: {merged_text_context}\n\n"
            f"問題: {query_text}\n"
            f"規則：請根據背景資訊判斷問題的答案，僅回覆 'yes' 或 'no'，不需要其他說明。\n"
            f"回答:"
        )
    else:
        # 一般自由文字回答
        augmented_prompt = (
            f"背景資訊: {merged_text_context}\n\n"
            f"問題: {query_text}\n"
            f"回答:"
        )
    print("######## 增強後的提示詞 ########")
    print(augmented_prompt)

    # 呼叫 OpenAI 生成最終回答，若有圖片則傳入路徑
    response = generate_with_openai(
        text_prompt=augmented_prompt,
        image_path=selected_image_path
    )
    return response
