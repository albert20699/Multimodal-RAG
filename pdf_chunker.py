import os
import fitz  # PyMuPDF
import io
import math
from PIL import Image
import pytesseract
import pdf_text_chunker
import image_processor

# 設定 Tesseract OCR 執行檔路徑
pytesseract.pytesseract.tesseract_cmd = r"C:/Program Files/Tesseract-OCR/tesseract.exe"

def is_valid_image(img):
    img = img.convert("RGB")
    colors = img.getcolors(maxcolors=img.size[0] * img.size[1])
    if colors is None:
        return True
    return len(colors) != 1

def boxes_distance(bbox1, bbox2):
    x1, y1, x2, y2 = bbox1
    a1, b1, a2, b2 = bbox2
    dx = max(a1 - x2, x1 - a2, 0)
    dy = max(b1 - y2, y1 - b2, 0)
    return math.hypot(dx, dy)

def merge_overlapping_boxes(boxes, threshold=0):
    boxes = boxes.copy()
    changed = True
    while changed:
        changed = False
        new_boxes = []
        while boxes:
            current = boxes.pop(0)
            merged_box = current
            i = 0
            while i < len(boxes):
                if boxes_distance(merged_box, boxes[i]) <= threshold:
                    bx1, by1, bx2, by2 = merged_box
                    cx1, cy1, cx2, cy2 = boxes[i]
                    merged_box = (min(bx1, cx1), min(by1, cy1), max(bx2, cx2), max(by2, cy2))
                    boxes.pop(i)
                    changed = True
                else:
                    i += 1
            new_boxes.append(merged_box)
        boxes = new_boxes
    return boxes

def pdf_page_to_image(pdf_path, page_number):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_number)
    pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    return img

def process_pdf_with_ocr(pdf_path, chunk_size=512, merge_threshold=20, padding=10, ignore_image_processing=False):
    print(f"\n[INFO] 開始處理 PDF: {pdf_path}")
    pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]

    # 文字區塊處理
    text_blocks = pdf_text_chunker.extract_text_blocks(pdf_path)
    split_texts = pdf_text_chunker.split_text_blocks(text_blocks, chunk_size=chunk_size)
    
    if ignore_image_processing:
        print("[INFO] 已啟用 ignore_image_processing，將略過所有圖片處理。")
        return split_texts

    # 以下為圖片處理區塊
    output_folder_merged = "extracted_images"
    os.makedirs(output_folder_merged, exist_ok=True)
    output_folder_individual = "extracted_individual_images"
    os.makedirs(output_folder_individual, exist_ok=True)

    pdf_file = fitz.open(pdf_path)
    for page_index in range(len(pdf_file)):
        print(f"[INFO] 處理第 {page_index + 1} 頁...")
        page = pdf_file.load_page(page_index)
        image_list = page.get_images(full=True)
        image_info_list = page.get_image_info(hashes=False, xrefs=True)

        valid_image_info_list = []
        if image_list:
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = pdf_file.extract_image(xref)
                image_bytes = base_image["image"]
                img_ind = Image.open(io.BytesIO(image_bytes))
                if not is_valid_image(img_ind):
                    print(f"[INFO] 單色圖片跳過: {pdf_basename}_page{page_index+1}_img{img_idx+1}.png")
                    continue
                output_path_ind = os.path.join(output_folder_individual, f"{pdf_basename}_page{page_index+1}_img{img_idx+1}.png")
                img_ind.save(output_path_ind)
                valid_image_info_list.append(image_info_list[img_idx])

        if not valid_image_info_list:
            continue

        bboxes = [info["bbox"] for info in valid_image_info_list]
        merged_bboxes = merge_overlapping_boxes(bboxes, threshold=merge_threshold)
        print(f"[INFO] 有效圖片數：{len(bboxes)}，合併後數：{len(merged_bboxes)}")

        for idx, bbox in enumerate(merged_bboxes):
            padded_bbox = (
                bbox[0] - padding, bbox[1] - padding,
                bbox[2] + padding, bbox[3] + padding
            )
            clip_rect = fitz.Rect(padded_bbox)
            pix = page.get_pixmap(clip=clip_rect)
            if pix.width == 0 or pix.height == 0:
                continue
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()

            description = image_processor.describe_image_with_azure(image_bytes=image_bytes)
            print(f"[DEBUG] Azure 圖片描述：{description}")
            
            # 這裡使用 CLIP 模型找最相符文字區塊
            max_score = -1.0
            best_index = None
            for index, split in enumerate(split_texts):
                if split["page"] == page_index:
                    score = image_processor.get_clip_cosine_score(image_bytes, split["text"])
                    if score > max_score:
                        max_score = score
                        best_index = index

            if best_index is not None:
                print(f"[DEBUG] 對應到的文字區塊 index={best_index}")
                print(f"[DEBUG] 對應區塊原始文字內容：\n{split_texts[best_index]['text']}\n")
                split_texts[best_index]["text"] += " " + description
                print(f"[INFO] 合併到區塊 index={best_index} 分數={max_score:.4f}")

            output_path_merged = os.path.join(output_folder_merged, f"{pdf_basename}_page{page_index+1}_box{idx+1}.png")
            img.save(output_path_merged)
            print(f"[INFO] 儲存合併後圖片：{output_path_merged}")

    print(f"[INFO] 完成處理，共 {len(split_texts)} 區塊")
    return split_texts

if __name__ == "__main__":
    pdf_path = "./RAG_data/Translate_Once_Translate_Twice_Translate_Thrice_and_Attribute_Identifying_Authors_and_Machine_Translation_Tools_in_Translated_Text.pdf"
    split_texts = process_pdf_with_ocr(pdf_path, merge_threshold=20, padding=10)
    print(f"[INFO] 最終區塊數：{len(split_texts)}")

    output_image = pdf_page_to_image(pdf_path, page_number=3)
    output_image.show()
