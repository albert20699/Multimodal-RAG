import sys
from langchain_ollama import OllamaEmbeddings
from datasets import Dataset
import os
import base64
from openai import AzureOpenAI
from mimetypes import guess_type
from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAIEmbeddings
from ragas.metrics import (
    faithfulness,
    answer_correctness,
    answer_relevancy,
    context_precision,
    context_recall,
)
from ragas import evaluate


# 設定 Azure OpenAI 環境變數
endpoint = os.getenv("ENDPOINT_URL")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
deployment = os.getenv("DEPLOYMENT_NAME", "gpt-4o")
api_version = "2024-02-15-preview"
embedding_deployment="text-embedding-ada-002"
embedding_api_version="2023-05-15"

def local_image_to_data_url(image_path):
    """
    將本機圖片轉換為 base64 編碼的 data URL
    """
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = "application/octet-stream"

    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode("utf-8")

    return f"data:{mime_type};base64,{base64_encoded_data}"



def generate_with_openai(text_prompt, image_path=None, system_prompt=None):
    """
    使用 Azure OpenAI 生成回答。
    可選地接受 system_prompt 作為系統訊息，如果為 None 則不包含。
    如果提供 image_path，會將本地圖片轉成 base64 data URL 並附加至 user 訊息中。
    """
    messages = []

    # 如果有系統提示，先加入 system message
    if system_prompt:
        messages.append({
            "role": "system",
            "content": system_prompt
        })

    # 加入 user text prompt
    messages.append({
        "role": "user",
        "content": [{"type": "text", "text": text_prompt}]
    })

    # 如果有圖片，轉檔並加入同一 user 訊息
    if image_path:
        data_url = local_image_to_data_url(image_path)
        messages[-1]["content"].append({
            "type": "image_url",
            "image_url": {"url": data_url}
        })

    # 初始化 Azure OpenAI 客戶端
    client = AzureOpenAI(
        api_key=api_key,
        api_version=api_version,
        base_url=f"{endpoint}openai/deployments/{deployment}",
    )

    # 呼叫 chat completion 並加上錯誤處理
    try:
        completion = client.chat.completions.create(
            model=deployment,
            messages=messages,
            max_tokens=800,
            temperature=0.7,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None,
            stream=False
        )
        return completion.choices[0].message.content

    except Exception as e:
        print("[ERROR] OpenAI 生成錯誤：", e)
        print("[INFO] 返回空回應以避免程式中斷。")
        return ""


def generate_with_langchain(text_prompt, image_path=None, image_bytes=None):
    if image_path and image_bytes:
        raise ValueError("請只傳入 image_path 或 image_bytes 其中之一，不能同時傳入")

    messages = [{"role": "user", "content": [{"type": "text", "text": text_prompt}]}]

    try:
        if image_path or image_bytes:
            if image_path:
                with open(image_path, "rb") as f:
                    img_bytes = f.read()
                mime_type, _ = guess_type(image_path)
            else:
                img_bytes = image_bytes
                mime_type = "image/png"  # 預設為 PNG，可根據需要調整

            if mime_type is None:
                mime_type = "application/octet-stream"

            base64_data = base64.b64encode(img_bytes).decode("utf-8")
            data_url = f"data:{mime_type};base64,{base64_data}"

            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })

        # 初始化 Azure OpenAI 客戶端
        azure_model = AzureChatOpenAI(
            openai_api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key,
            azure_deployment=deployment,
            model=deployment,
        )

        completion = azure_model.invoke(messages)
        return completion.content

    except Exception as e:
        print("[ERROR] LangChain 調用 Azure OpenAI 發生錯誤：", e)
        return "[無法產生回應]"



def embedding_with_langchain(text_embedding):
    # 初始化 Embeddings
    embeddings = AzureOpenAIEmbeddings(
        openai_api_type="azure",
        azure_deployment=embedding_deployment,
        api_key=api_key,
        azure_endpoint=endpoint,
        openai_api_version=embedding_api_version 
    )
    query_result = embeddings.embed_query(text_embedding)
    return query_result


def evaluating_RAG_with_ragas(test_questions, answers, contexts, ground_truth):
    # 轉換 ground_truths 的格式，使 reference 為單一字串
    dataset = Dataset.from_dict({
        "question": test_questions,
        "answer": answers,
        "contexts": contexts,
        "ground_truth": ground_truth,
    })

    # 初始化 Azure OpenAI 客戶端
    azure_model = AzureChatOpenAI(
        openai_api_version=api_version,
        azure_endpoint=endpoint,
        api_key=api_key,
        azure_deployment=deployment,
        model=deployment,
    )

    # ✅ **使用與 ChromaDB 相同的 `OllamaEmbeddings`**
    embedding_model = OllamaEmbeddings(
        model="mxbai-embed-large",  # 確保與 ChromaDB 相同
        base_url="http://localhost:11434"
    )

    # ✅ **評估時改用 `OllamaEmbeddings`，而不是 Azure OpenAI**
    result = evaluate(dataset=dataset, metrics=[
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    ], llm=azure_model, embeddings=embedding_model)

    return result



if __name__ == "__main__":
    user_input =   """123456"""

    response = generate_with_langchain(user_input)
    print(response)

    image_input = "./RAG_processed_data/螢幕擷取畫面 (1).png"
    response_with_image = generate_with_openai("幫我描述圖片:", image_input)
    print(response_with_image)

    embedding_input = "請告訴我今天的天氣如何？"
    embedding_result = generate_with_openai(embedding_input)
    print(embedding_result)


