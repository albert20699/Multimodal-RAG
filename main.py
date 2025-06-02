import json
from vector_db import init_chroma_client, init_collections, check_collection_data, fetch_collection_data, save_to_excel
from process_files import process_pdf_changes
from rag_pipeline import rag_query_pipeline
from azure_tool import evaluating_RAG_with_ragas
import os

# 選擇： extractive / free_form / yes_no
QUESTION_TYPE = "extractive"  
# 是否使用圖像處理演算法
WITH_IMAGE_ALGO = True             


def load_qasper_data(question_type):
    """
    根據 question_type 讀取對應的 Qasper 資料並解析成問題與標準答案。
    """
    base_dir = os.path.join("validation_Data", "working Data", "allenai-qasper")
    file_name = f"sampled_qasper_{question_type}.json"
    file_path = os.path.join(base_dir, "sampled", file_name)

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    ground_truths = []

    for item in data:
        question = item["question"]
        answer = item["answer"]

        if question_type == "extractive":
            spans = answer.get("extractive_spans", [])
            ground_truth = " ".join(spans) if isinstance(spans, list) else spans or ""

        elif question_type == "free_form":
            ground_truth = answer.get("free_form_answer", "")

        elif question_type == "yes_no":
            ground_truth = str(answer.get("yes_no", "")) 
            if ground_truth is None:
                ground_truth = ""

        else:
            raise ValueError(f"[ERROR] 不支援的 question_type: {question_type}")
                     
        questions.append(question)
        ground_truths.append(ground_truth)

    return questions, ground_truths

def main(question_type, with_image_algo=True):
    # 1. 初始化 ChromaDB 與向量集合
    client = init_chroma_client()
    text_collection, image_collection = init_collections(client)
    
    check_collection_data(text_collection)
    check_collection_data(image_collection)
    print("[INFO] 向量資料庫初始化完成！")
    
    # 2. 處理 PDF 變更，更新向量資料庫
    deleted_files, changed_files = process_pdf_changes(text_collection, image_collection, ignore_image_processing=not with_image_algo)
    
    # 3. 讀取測試問題與標準答案，執行 RAG 查詢與評測
    test_questions, ground_truths = load_qasper_data(question_type)

    answers, text_contexts = [], []
    for query in test_questions:
        response = rag_query_pipeline(
            query,
            text_collection,
            image_collection,
            dataset_type=question_type if question_type == "yes_no" else None,
            ignore_image_processing=not with_image_algo  
        )
        answers.append(response)
        
        text_result = text_collection.query(query_texts=[query], n_results=4)
        retrieved_text = text_result.get("documents", [])
        retrieved_text = ["\n".join(doc) if isinstance(doc, list) else str(doc) for doc in retrieved_text]
        text_contexts.append(retrieved_text)
    
    # 4. 評估 RAG 結果
    score_text = evaluating_RAG_with_ragas(test_questions, answers, text_contexts, ground_truths)
    df_text = score_text.to_pandas()

    # 根據 question_type 和演算法設定組合輸出檔名
    algo_tag = "with_algo" if with_image_algo else "baseline"
    output_file = f"evaluation_results/score_{question_type}_{algo_tag}.csv"
    df_text.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"[INFO] 文字檢測分數已儲存為 {output_file}")
    
    # 5. 儲存 Chunk 全部區塊資料庫內容，方便查看
    # text_data = fetch_collection_data(text_collection)
    # image_data = fetch_collection_data(image_collection)
    # save_to_excel(text_data, image_data)
    
    print("[INFO] 所有流程處理完成！")

if __name__ == "__main__":
    main(QUESTION_TYPE, with_image_algo=WITH_IMAGE_ALGO)
