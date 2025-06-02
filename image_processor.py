from azure_tool import generate_with_langchain 
import requests
import base64
import sys
import io
import pytesseract
from PIL import Image
import ollama
import torch
from transformers import CLIPProcessor, CLIPModel
import torch.nn.functional as F

# 建議把 model 跟 processor 移到函式外，只 load 一次
model_name = "openai/clip-vit-base-patch32"
processor = CLIPProcessor.from_pretrained(model_name)
model     = CLIPModel.from_pretrained(model_name)

# 設定 Tesseract OCR 執行檔路徑
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"
# Ollama 伺服器 API 端點
Ollama_URL = "http://localhost:11434/api/generate" 

def image_ocr_by_bytes(image_bytes):
    """
    使用 OCR 擷取圖片中的文字（適用於二進制圖片資料）。
    """
    image = Image.open(io.BytesIO(image_bytes))
    ocr_text = pytesseract.image_to_string(image, lang="chi_tra").strip()
    return ocr_text

def image_ocr_by_path(image_path):
    """
    使用 OCR 擷取圖片中的文字（適用於圖片路徑）。
    """
    image = Image.open(image_path)
    ocr_text = pytesseract.image_to_string(image, lang="chi_tra").strip()
    print(f"[INFO] 圖片 {image_path} 讀取 OCR 成功") 
    return ocr_text


def encode_image(image_path=None, image_bytes=None):
    """將圖片轉為 Base64，支援檔案路徑或直接處理 image_bytes"""
    if image_path:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode("utf-8")
    elif image_bytes:
        if isinstance(image_bytes, bytes):
            return base64.b64encode(image_bytes).decode("utf-8")
        else:
            raise ValueError("image_bytes 必須是 bytes 類型")
    else:
        raise ValueError("必須提供 image_path 或 image_bytes 之一")
    


def get_clip_cosine_score(image_bytes: bytes, text: str) -> float:
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # 分別 encode image/text
    pixel_inputs = processor(images=image, return_tensors="pt")
    text_inputs  = processor(text=[text], return_tensors="pt", padding=True, truncation=True, max_length=77)

    with torch.no_grad():
        img_feats = model.get_image_features(**pixel_inputs)   # [1, D]
        txt_feats = model.get_text_features(**text_inputs)     # [1, D]

    # L2 正規化
    img_norm = img_feats / img_feats.norm(dim=-1, keepdim=True)
    txt_norm = txt_feats / txt_feats.norm(dim=-1, keepdim=True)

    # Cosine 相似度 (值域 [-1,1])
    score = F.cosine_similarity(img_norm, txt_norm).item()
    # 如果你想讓它落在 [0,1]，可以做 (score+1)/2
    return score


def describe_image_with_ollama(image_path=None, image_bytes=None):
    """
    使用 LLaVA (LLaMA + Vision) 模型分析圖片內容，並結合 OCR 文字來提供描述。
    - 只能傳入 image_path 或 image_bytes 其中一個
    """
    if (image_path and image_bytes) or (not image_path and not image_bytes):
        raise ValueError("必須提供 image_path 或 image_bytes ，且不能同時提供兩者")

    print(f"[INFO] 處理描述圖片資訊: {image_path if image_path else '來自 bytes 記憶體'}")

    try:
        # 將圖片轉為 Base64
        image_base64 = encode_image(image_path=image_path, image_bytes=image_bytes)
        
        # OCR 辨識
        if image_path:
            ocr_text = image_ocr_by_path(image_path)  
        else:
            ocr_text = image_ocr_by_bytes(image_bytes)

        # 設置請求參數
        payload = {
            "model": "llava:13b",
            "prompt": (
                f"""
                    根據以下圖片內容，請僅描述圖片中清楚可見的視覺細節。請遵循這些要求：
                    1. 優先根據圖片內的明確特徵進行描述，僅在圖片內容不足時輔以 OCR 文字做輔助。
                    2. 如果圖片本身缺乏具體或有意義的視覺細節，請直接返回空白或僅回覆「」。
                    3. 請不要評論或指出 OCR 文字中的錯誤，僅將 OCR 作為參考資料。
                    4. 不要對圖片進行無意義或過多的猜測，只描述圖片中真實可觀察到的資訊。
                    OCR 內容（僅供參考）：[{ocr_text}]
                """
            ),
            "images": [image_base64],
            "stream": False  # 不使用串流模式
        }

        response = requests.post(Ollama_URL, json=payload)

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()  # 確保回傳內容乾淨
        else:
            return ""

    except Exception as e:
        print(f"[ERROR] LLaVA 處理失敗: {e}")
        return ""

# 使用 Azure Tool 進行圖片描述
def describe_image_with_azure(image_path=None, image_bytes=None):
    """
    使用 Azure Tool 分析圖片內容，並結合 OCR 文字來提供描述。
    """
    if (image_path and image_bytes) or (not image_path and not image_bytes):
        raise ValueError("必須提供 image_path 或 image_bytes ，且不能同時提供兩者")
    
    print(f"[INFO] 使用 Azure Tool 處理圖片描述: {image_path if image_path else '來自 bytes 記憶體'}")
    
    try:
        # 先進行 OCR 辨識
        if image_path:
            ocr_text = image_ocr_by_path(image_path)
        else:
            ocr_text = image_ocr_by_bytes(image_bytes)
        
        # 組合 prompt，這邊你可以依需求調整文字內容
        prompt_text = (
            "根據以下圖片內容，請僅描述圖片中清楚可見的視覺細節。請遵循這些要求：\n"
            "1. 優先根據圖片內的明確特徵進行描述，僅在圖片內容不足時以 OCR 文字做輔助。\n"
            "2. 如果圖片本身缺乏具體或有意義的視覺細節，請直接返回空白或僅回覆「」。\n"
            "3. 請不要評論或指出 OCR 文字中的錯誤，僅將 OCR 作為參考資料。\n"
            "4. 不要對圖片進行無意義或過多的猜測，只描述圖片中真實可觀察到的資訊。\n"
            f"OCR 內容（僅供參考）：[{ocr_text}]"
        )
        
        # 呼叫 Azure Tool 來產生圖片描述（同時送出 prompt 與圖片）
        if image_path:
            response_text = generate_with_langchain(prompt_text, image_path=image_path)
        else:
            response_text = generate_with_langchain(prompt_text, image_bytes=image_bytes)
        return response_text.strip()

    except Exception as e:
        print(f"[ERROR] Azure Tool 處理失敗: {e}")
        return ""

def refine_ocr_text(ocr_text):
    """
    優化 OCR 輸出內容，移除亂碼與無意義文字，保留有效資訊。
    """
    print(f"[INFO] 圖片正在對於 OCR 文本過濾有效內容...") 
    try:
        response = ollama.chat(
            model="phi4",  # 確保這個模型名稱正確
            messages=[
                {
                    "role": "user",
                    "content": (
                        "以下是把一張圖片進行 OCR 出來的結果，只需要移除雜亂的文字跟不規則的數字或特殊字元，留下有意義通順符合邏輯文字的部分，不要改寫太多，回覆時也不要加入其他文字內容。"
                        f"OCR 內容如下：[{ocr_text}]"
                    ),
                }
            ],
        )
        # 確保 response 有內容
        print(f"[INFO] 圖片過濾 OCR 內容成功") 
        return response.get("message", {}).get("content", "").strip()
    except Exception as e:
        return ""

if __name__ == "__main__":
    test_path = "./extracted_images/20240130_智能客服機器人_智域_page6_box1.png"
    
    # 讀入圖片 bytes
    with open(test_path, "rb") as f:
        image_bytes = f.read()
    
    # 測試 image_bytes 描述功能
    print("[TEST] 使用 image_bytes 呼叫 describe_image_with_azure():")
    result = describe_image_with_azure(image_bytes=image_bytes)
    print("[RESULT] 描述結果：")
    print(result)

