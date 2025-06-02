# Qasper-RAG：基於 Qasper 問答資料集的檢索增強生成

本專案應用 **檢索增強生成（RAG）** 技術於 [Qasper](https://allenai.org/data/qasper) 資料集，支援三種問題類型：

- 抽取式（Extractive）
- 自由形式（Free-form）
- 是／否（Yes/No）

每種問題類型均有兩種版本實作：
1. `with_algo`：含圖像處理與多模態嵌入的強化型 RAG（實驗性）。
2. `baseline`：僅使用文字的傳統 RAG（基準比較）。

👉 [English Version](README.md)

---

## 📂 檔案總覽

| 問題類型   | 強化演算法（with_algo）                 | 基準模型（baseline）                     |
|------------|------------------------------------------|-------------------------------------------|
| Extractive | `rag_qasper_extractive_with_algo.py`     | `rag_qasper_extractive_baseline.py`       |
| Free-form  | `rag_qasper_freeform_with_algo.py`       | `rag_qasper_freeform_baseline.py`         |
| Yes/No     | `rag_qasper_yesno_with_algo.py`          | `rag_qasper_yesno_baseline.py`            |

---

## 🚀 執行方式

1. 安裝必要套件

```bash
pip install -r requirements.txt
```

2. 執行任一主程式腳本

```bash
python rag_qasper_extractive_with_algo.py
```

---

## 🔧 功能特色

- 🖼️ 支援多模態資料：從 PDF 中解析表格與圖片
- 🎯 圖文對齊強化檢索：整合 CLIP 進行語意相似度計算
- 📊 支援生成效果評估：可比較強化版與基準版輸出品質
- 🗂️ 腳本架構清楚：依問題類型與演算法分類管理

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
- RAG 評估工具：RAGAS：https://github.com/explodinggradients/ragas  
- 視覺模型：CLIP、BLIP、Azure Captioning  

---

## 🤝 貢獻與回饋

歡迎提出 issue 或 PR，提供改進建議或問題回報！
