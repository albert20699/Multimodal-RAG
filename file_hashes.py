import hashlib
import os
import json

# 載入環境變數
RAG_RAW_FILE_PATH  = os.getenv('RAG_RAW_FILE_PATH')
HASH_DB_FILE = "file_hashes.json"

def calculate_file_hash(file_path):
    """計算檔案的 SHA-256 哈希值"""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def normalize_path(file_path):
    """統一使用 `/` 作為路徑分隔符"""
    return file_path.replace("\\", "/")

def load_previous_hashes():
    """載入之前儲存的哈希值，並確保所有路徑使用 `/` 格式"""
    if os.path.exists(HASH_DB_FILE):
        with open(HASH_DB_FILE, "r") as f:
            hashes = json.load(f)
        return {normalize_path(k): v for k, v in hashes.items()}  # 轉換所有路徑
    return {}

def save_current_hashes(hashes):
    """儲存最新的哈希值，確保所有路徑使用 `/` 格式"""
    normalized_hashes = {normalize_path(k): v for k, v in hashes.items()}
    with open(HASH_DB_FILE, "w") as f:
        json.dump(normalized_hashes, f, indent=4)

def check_for_changes(directory):
    """檢查指定資料夾內是否有檔案變動或刪除"""
    previous_hashes = load_previous_hashes()
    current_hashes = {}

    changed_files = []
    deleted_files = set(previous_hashes.keys())  # 記錄所有舊檔案，後續用來判斷是否被刪除

    for root, _, files in os.walk(directory):
        for file in files:
             if file.endswith((".pdf", ".doc", ".docx")):  # 檢查 PDF, DOC 和 DOCX
                file_path = normalize_path(os.path.join(root, file)) 
                file_hash = calculate_file_hash(file_path)
                current_hashes[file_path] = file_hash

                # 如果檔案是新的或哈希值變更，則標記為變更
                if file_path not in previous_hashes or previous_hashes[file_path] != file_hash:
                    changed_files.append(file_path)

                # 如果檔案仍然存在，就從刪除清單中移除
                deleted_files.discard(file_path)

    # 更新哈希值（僅保留目前仍存在的檔案）
    save_current_hashes(current_hashes)

    # 輸出結果
    if changed_files:
        print("有變更的檔案:", changed_files)
    else:
        print("沒有檔案變更，跳過向量資料庫更新。")

    if deleted_files:
        print("已刪除的檔案:", list(deleted_files))

    return changed_files, list(deleted_files)

def clear_hash_records():
    """清除所有紀錄並重新檢查變動的檔案"""
    if os.path.exists(HASH_DB_FILE):
        os.remove(HASH_DB_FILE)
        print("已清除所有哈希紀錄。")
    else:
        print("沒有舊的哈希紀錄，無需清除。")

if __name__ == "__main__":
    RAG_data_path = RAG_RAW_FILE_PATH 
    # file_hashes.clear_hash_records()
    changed_files, deleted_files = check_for_changes(RAG_data_path)
