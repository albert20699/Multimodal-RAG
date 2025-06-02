import fitz  # PyMuPDF
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 設定最小文字區塊長度閥值
MIN_BLOCK_LENGTH = 100

def extract_text_blocks(pdf_path, min_block_length = MIN_BLOCK_LENGTH):
    text_blocks = []
    doc = fitz.open(pdf_path)
    
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        merged_blocks = []
        temp_text = ""
        temp_x1, temp_y1, temp_x2, temp_y2 = float('inf'), float('inf'), 0, 0
        
        for block in blocks:
            block_text = " ".join([line["spans"][0]["text"] for line in block.get("lines", []) if line["spans"]])
            
            if not block_text.strip():
                continue
            
            # 累計區塊文本，確保不會過短
            if len(temp_text) < min_block_length and temp_text:
                temp_text += " " + block_text
                temp_x1 = min(temp_x1, block["bbox"][0])
                temp_y1 = min(temp_y1, block["bbox"][1])
                temp_x2 = max(temp_x2, block["bbox"][2])
                temp_y2 = max(temp_y2, block["bbox"][3])
            else:
                if temp_text:
                    merged_blocks.append({
                        "text": temp_text,
                        "x1": temp_x1,
                        "y1": temp_y1,
                        "x2": temp_x2,
                        "y2": temp_y2,
                        "page": page_num
                    })
                temp_text = block_text
                temp_x1, temp_y1, temp_x2, temp_y2 = block["bbox"][0], block["bbox"][1], block["bbox"][2], block["bbox"][3]
        
        # 加入最後一個區塊
        if temp_text:
            merged_blocks.append({
                "text": temp_text,
                "x1": temp_x1,
                "y1": temp_y1,
                "x2": temp_x2,
                "y2": temp_y2,
                "page": page_num
            })
        
        text_blocks.extend(merged_blocks)
    
    return text_blocks

def split_text_blocks(text_blocks, chunk_size, chunk_overlap=0):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    split_results = []

    for block in text_blocks:
        chunks = text_splitter.split_text(block["text"])
        
        for chunk in chunks:
            split_results.append({
                "text": chunk,
                "x1": block["x1"], 
                "y1": block["y1"], 
                "x2": block["x2"], 
                "y2": block["y2"], 
                "page": block["page"]
            })
    
    return split_results

if __name__ == "__main__":
    pdf_path = "./RAG_processed_data/Large Language Model-Brained GUI Agents - A survey.pdf"
    text_blocks = extract_text_blocks(pdf_path)
    split_texts = split_text_blocks(text_blocks, chunk_size=512)

    for split in split_texts:
        print(f"Page: {split['page']}, x: {split['x1']}, y: {split['y1']}, Text: {split['text']}\n")
