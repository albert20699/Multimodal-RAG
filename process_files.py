import os
import shutil
from pathlib import Path
from io import BytesIO
import comtypes.client
import win32com.client
from docx2pdf import convert as docx_to_pdf
from pptx import Presentation

import file_hashes
import pdf_chunker
import pdf_text_chunker
import image_processor
from vector_db import add_documents_to_collection, delete_documents_from_collection

# 載入環境變數
RAG_FILE_PATH = os.getenv("RAG_FILE_PATH")        # 轉換後 PDF 要存放的資料夾
RAG_RAW_FILE_PATH = os.getenv("RAG_RAW_FILE_PATH")  # 原始檔案（pdf/doc/docx/pptx）的資料夾

# 確保處理後的資料夾存在
os.makedirs(RAG_FILE_PATH, exist_ok=True)


def get_output_pdf_path(input_path: str) -> str:
    """
    給定原始檔路徑，回傳對應的輸出 PDF 路徑（存於 RAG_FILE_PATH 下，副檔名為 .pdf）。
    例如：/raw/foo.docx -> {RAG_FILE_PATH}/foo.pdf
    """
    stem = Path(input_path).stem
    return os.path.join(RAG_FILE_PATH, f"{stem}.pdf")


def convert_doc_to_docx(input_path: str) -> str:
    """
    將 .doc 轉成 .docx，並放到 RAG_RAW_FILE_PATH 底下，回傳新的 .docx 路徑。
    """
    filename = Path(input_path).stem + ".docx"
    output_path = os.path.join(RAG_RAW_FILE_PATH, filename)

    if not os.path.exists(input_path):
        print(f"[ERROR] DOC 檔案不存在：{input_path}")
        return None

    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        doc = word.Documents.Open(os.path.abspath(input_path))
        doc.SaveAs(os.path.abspath(output_path), FileFormat=16)  # 16 表示 docx
        doc.Close()
        print(f"[INFO] 成功將 .doc 轉成 .docx：{input_path} -> {output_path}")
        return output_path
    except Exception as e:
        print(f"[ERROR] 將 .doc 轉 .docx 時發生錯誤：{e}")
        return None
    finally:
        try:
            word.Quit()
        except:
            pass


def convert_doc_to_pdf(input_path: str, output_pdf_fullpath: str) -> bool:
    """
    用 Word COM 介面將 .doc 或 .docx 轉 PDF。
    output_pdf_fullpath 要包含最終的 .pdf 檔名
    回傳 True/False 表示是否成功。
    """
    try:
        wdFormatPDF = 17
        word = comtypes.client.CreateObject("Word.Application")
        doc = word.Documents.Open(os.path.abspath(input_path))
        doc.SaveAs(output_pdf_fullpath, FileFormat=wdFormatPDF)
        doc.Close()
        word.Quit()
        print(f"[INFO] DOC(X) 轉 PDF：{input_path} -> {output_pdf_fullpath}")
        return True
    except Exception as e:
        print(f"[ERROR] DOC(X) 轉 PDF 時失敗：{e}")
        try:
            word.Quit()
        except:
            pass
        return False


def convert_pptx_to_pdf(input_path: str, output_pdf_fullpath: str) -> bool:
    """
    將 .pptx 轉 PDF（這裡採用 copy 模擬或放自己真實轉的程式）。
    如果有其他實作方式，可以在這裡替換；目前僅示範成「複製檔名改 .pdf」。
    回傳 True/False 表示是否成功。
    """
    try:
        # 如果要用 PowerPoint COM 轉 PDF，可以改寫成：
        # powerpoint = comtypes.client.CreateObject("PowerPoint.Application")
        # deck = powerpoint.Presentations.Open(os.path.abspath(input_path))
        # deck.SaveAs(output_pdf_fullpath, 32)  # 32 表示 pptx->pdf
        # deck.Close()
        # powerpoint.Quit()
        shutil.copy(input_path, output_pdf_fullpath)
        print(f"[INFO] PPTX 轉 PDF（模擬複製）：{input_path} -> {output_pdf_fullpath}")
        return True
    except Exception as e:
        print(f"[ERROR] PPTX 轉 PDF 失敗：{e}")
        return False


def convert_to_pdf(input_path: str) -> str:
    """
    根據 input_path 的副檔名，自動選擇轉 PDF 或複製：
      - .pdf: 直接複製到 RAG_FILE_PATH
      - .docx: 先用 docx2pdf 轉成 PDF
      - .doc: 先轉成 .docx，再轉 PDF
      - .pptx: 用 convert_pptx_to_pdf 轉成 PDF
    回傳 output_pdf_path（成功情況）或 None（失敗）。
    """
    ext = Path(input_path).suffix.lower().lstrip(".")
    output_pdf_path = get_output_pdf_path(input_path)

    try:
        if ext == "pdf":
            shutil.copy(input_path, output_pdf_path)
            print(f"[INFO] 直接複製 PDF：{input_path} -> {output_pdf_path}")
            return output_pdf_path

        elif ext == "docx":
            # docx2pdf 底層也會呼叫 Word 轉 PDF
            docx_to_pdf(input_path, output_pdf_path)
            print(f"[INFO] DOCX 轉 PDF：{input_path} -> {output_pdf_path}")
            return output_pdf_path

        elif ext == "doc":
            # 先轉成 .docx，再用 docx2pdf
            temp_docx = convert_doc_to_docx(input_path)
            if temp_docx:
                docx_to_pdf(temp_docx, output_pdf_path)
                # 刪掉臨時的 .docx
                try:
                    os.remove(temp_docx)
                    print(f"[INFO] 刪除臨時 .docx：{temp_docx}")
                except:
                    pass
                print(f"[INFO] DOC 轉 PDF 完成：{input_path} -> {output_pdf_path}")
                return output_pdf_path
            else:
                return None

        elif ext == "pptx":
            success = convert_pptx_to_pdf(input_path, output_pdf_path)
            return output_pdf_path if success else None

        else:
            print(f"[WARN] 不支援的檔案格式：{input_path}")
            return None

    except Exception as e:
        print(f"[ERROR] convert_to_pdf 失敗 ({input_path})：{e}")
        return None


def process_files():
    """
    增量式地轉換與刪除：
      - 先呼叫 file_hashes.check_for_changes，拿到 raw 資料夾中「修改或新增」以及「刪除」的檔案清單。
      - 針對修改/新增的檔案，呼叫 convert_to_pdf，回傳轉換後的 PDF 路徑（若成功）。    
      - 針對刪除的檔案，刪除對應的輸出 PDF，並回傳被刪除的 PDF 路徑。
    回傳 tuple： (converted_pdf_paths, deleted_pdf_paths)
    """
    # 1. 取得 raw 資料夾中「新增/修改」與「刪除」的檔名（full path）
    changed_raw_paths, deleted_raw_paths = file_hashes.check_for_changes(RAG_RAW_FILE_PATH)

    converted_pdfs = []
    deleted_pdfs = []

    # 2. 處理「被刪除的 raw 檔」，對應刪除輸出 pdf
    for raw_path in deleted_raw_paths:
        out_pdf = get_output_pdf_path(raw_path)
        if os.path.exists(out_pdf):
            try:
                os.remove(out_pdf)
                deleted_pdfs.append(out_pdf)
                print(f"[INFO] 已刪除輸出 PDF：{out_pdf}")
            except Exception as e:
                print(f"[ERROR] 刪除輸出 PDF 失敗：{out_pdf} ({e})")

    # 3. 處理「新增/修改的 raw 檔」，轉 PDF（或複製）
    for raw_path in changed_raw_paths:
        out_pdf = convert_to_pdf(raw_path)
        if out_pdf:
            converted_pdfs.append(out_pdf)

    return converted_pdfs, deleted_pdfs


def process_pdf_changes(text_collection: str, image_collection: str, ignore_image_processing: bool = False):
    """
    呼叫 process_files 取得「新增/修改的 PDF 路徑」與「已刪除的 PDF 路徑」，
    並將它們同步到向量資料庫：
      1. 先把所有被刪除或修改 (changed) 的 PDF IDs 從 text_collection 與 image_collection 刪除。
      2. 針對每個修改/新增的 PDF，做文字分塊與圖片描述，然後新增到向量庫。
    """
    changed_pdfs, deleted_pdfs = process_files()

    # 統一把 deleted + changed 當作要刪除的 document IDs（因為如果同一份檔案被修改，先刪除舊版本）
    # 這邊約定：ID 用 PDF 檔名（不含資料夾）
    deleted_doc_ids = [os.path.basename(p).rsplit(".", 1)[0] for p in deleted_pdfs + changed_pdfs]
    delete_documents_from_collection(text_collection, deleted_doc_ids)
    delete_documents_from_collection(image_collection, deleted_doc_ids)

    # 處理每一個修改/新增的 PDF
    for pdf_path in changed_pdfs:
        pdf_name = os.path.basename(pdf_path)
        file_type = Path(pdf_name).stem  # 當作 ID prefix

        # 1) 嘗試用 OCR 做文字分塊，若失敗改純文字
        try:
            pdf_chunks = pdf_chunker.process_pdf_with_ocr(
                pdf_path,
                merge_threshold=80,
                padding=40,
                ignore_image_processing=ignore_image_processing,
            )
        except Exception as e:
            print(f"[WARN] OCR 處理失敗，改用純文字分塊: {e}")
            text_blocks = pdf_text_chunker.extract_text_blocks(pdf_path)
            pdf_chunks = pdf_text_chunker.split_text_blocks(text_blocks, chunk_size=512)

        text_doc_ids, text_documents, text_metadatas = [], [], []
        image_doc_ids, image_documents, image_metadatas = [], [], []
        processed_pages = set()

        for idx, chunk in enumerate(pdf_chunks):
            page_num = chunk["page"]
            text_id = f"{file_type}_page{page_num}_txt{idx}"
            text_doc_ids.append(text_id)
            text_documents.append(chunk["text"])
            text_metadatas.append({
                "content_type": "text",
                "page": page_num,
                "file_type": file_type,
                "file_name": pdf_name
            })

            # 如果不需要 image 處理或這頁已處理過，就跳過
            if ignore_image_processing or page_num in processed_pages:
                continue
            processed_pages.add(page_num)

            # 從 PDF 這頁擷取圖片、轉成 bytes，丟給 Azure 產生描述
            img = pdf_chunker.pdf_page_to_image(pdf_path, page_num)
            buf = BytesIO()
            img.save(buf, format="PNG")
            image_bytes = buf.getvalue()
            image_desc = image_processor.describe_image_with_azure(image_bytes=image_bytes) or ""

            image_id = f"{file_type}_page{page_num}_img"
            image_doc_ids.append(image_id)
            image_documents.append(image_desc)
            image_metadatas.append({
                "content_type": "image",
                "page": page_num,
                "file_type": file_type,
                "file_name": pdf_name
            })

        # 最後把所有新產出的 text / image documents 加到向量庫
        if text_documents:
            add_documents_to_collection(text_collection, text_documents, text_doc_ids, text_metadatas)
        if image_documents and not ignore_image_processing:
            add_documents_to_collection(image_collection, image_documents, image_doc_ids, image_metadatas)

    return deleted_pdfs, changed_pdfs


if __name__ == "__main__":
    # 若直接執行此檔，僅做一次 process_files（不打向量庫）
    converted, deleted = process_files()
    print(f"[MAIN] 轉換完成，共新增/修改 {len(converted)} 個 PDF，刪除 {len(deleted)} 個 PDF")
