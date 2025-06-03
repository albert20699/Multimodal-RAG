👉 [English Version](README.md)

# Multimodal-RAG：基於多模態模型的檢索增強生成

本專案整合 **檢索增強生成（RAG）** 與多模態模型，應用於 [Qasper](https://allenai.org/data/qasper) 問答資料集，評估其在處理複雜文檔時的表現。

本系統支援以下三種問題類型：

- **抽取式（Extractive）**：答案可直接從原始文件中擷取，通常為明確句子或片段。
- **自由形式（Free-form）**：答案可能需整合多段文字內容，無法直接摘錄。
- **是／否（Yes/No）**：答案為「是」或「否」，有時包含簡要說明。

每種類型皆可搭配下列兩種處理模式執行：

1. **強化版本（with_algo）**：加入圖像處理與多模態特徵（如 CLIP）提升檢索準確度。
2. **基準版本（baseline）**：純文字處理流程，作為對照比較。

---

## 🔧 功能說明

- 可將 DOC、DOCX 和 PPTX 檔案轉換為 PDF 檔案預處理。
- 從 PDF 中擷取圖片，透過極值範圍整併相鄰區塊，還原為完整圖像。
- 搭配 CLIP 模型進行圖文語意對齊與相似度檢索。
- 對每個檔案頁面建立圖像向量，檢索時可對應回原頁面截圖，提升查詢結果的相關性。
- 透過多查詢檢索器，創造更全面提示詞，提升檢索範圍。

---

## 🗂️ 檔案資料夾

```mathematica
project_root/
├── evaluation_results/
│   ├── score_extractive_with_algo_example.csv
│   └── …
│       ──(最終使用 Qasper 進行評估後產生的 CSV 檔案，記錄各種指標與結果)
│
├── extracted_images/
│   └── …
│       ──(從多個被切割的小圖中重構而成的完整圖像，放置所有還原後的圖片)
│
├── extracted_individual_images/
│   └── …
│       ──(原本從 PDF 擷取時所產生的零散小圖，尚未經過整併的原始截取結果)
│
├── images_data/
│   └── …
│       ──(將整本 PDF 的每一頁逐頁截圖後的圖檔，用於後續影像處理／向量化)
│
├── RAG_raw_data/
│   ├── example1.docx
│   ├── example2.pptx
│   ├── example3.pdf
│   └── …
│       ──(使用者提供、尚未處理的原始檔案：DOC、DOCX、PPTX 等格式)
│
├── RAG_processed_data/
│   ├── example1.pdf
│   ├── example2.pdf
│   ├── example3.pdf
│   └── …
│       ──(RAG_raw_data 中所有檔案經過轉成 PDF 並完成預處理後自動生成的資料夾，存放處理好的 PDF)
│
└── validation_Data/working Data/
    └── allenai-qasper/
        ├── qasper_extractive.json
        ├── qasper_free_form.json
        │   ──(官方 Qasper 資料集原始資料)
        │      
        └── sampled/
            ├── extractive/
            ├── free_form/
            ├── yes_no/
            │   └── … 
            │       ──(對應 arxiv 論文 PDF 檔案)
            │       
            ├── sampled_qasper_extractive.json
            └── … 
                ──(從 allenai-qasper 資料集中隨機抽取的 20 份不同類型問答資料，供系統驗證使用)
```

---

## 🚀 執行方式

1. 安裝必要套件

```bash
pip install -r requirements.txt
```

2. 使用者可透過修改 `main.py` 檔案中的以下參數，自由切換六種組合（3 類問題 × 2 種模式）：

```python
# 選擇問題類型：extractive / free_form / yes_no
QUESTION_TYPE = "extractive"

# 是否啟用圖像處理與多模態強化檢索
WITH_IMAGE_ALGO = True
```

3. 執行主程式腳本

```bash
python main.py
```


---

## 🧪 目前進度

- [x] 完成三類問題的 baseline 版本
- [x] 完成含圖像處理的強化演算法
- [ ] 系統化評估與效能分析
- [ ] 整合 LangChain / LlamaIndex 模組
- [ ] 增加 CLI / 簡易 UI 包裝

---

## 📘 參考資源

- Qasper 資料集：https://allenai.org/data/qasper  
- RAG 評估工具 RAGAS：https://github.com/explodinggradients/ragas  
- CLIP 神經網路視覺模型：https://github.com/openai/CLIP
