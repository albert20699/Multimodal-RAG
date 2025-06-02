# Qasper-RAG: Retrieval-Augmented Generation on the Qasper QA Dataset

This project applies **Retrieval-Augmented Generation (RAG)** to the [Qasper](https://allenai.org/data/qasper) dataset, supporting three question types:

- Extractive
- Free-form
- Yes/No

Each type includes two RAG implementations:
1. `with_algo`: Enhanced RAG with image preprocessing and multimodal embeddings.
2. `baseline`: Text-only RAG for benchmarking.

👉 [繁體中文版本](README.zh.md)

---

## 📂 File Overview

| Question Type | Enhanced Algorithm (`with_algo`)        | Baseline (`baseline`)                     |
|---------------|------------------------------------------|-------------------------------------------|
| Extractive    | `rag_qasper_extractive_with_algo.py`     | `rag_qasper_extractive_baseline.py`       |
| Free-form     | `rag_qasper_freeform_with_algo.py`       | `rag_qasper_freeform_baseline.py`         |
| Yes/No        | `rag_qasper_yesno_with_algo.py`          | `rag_qasper_yesno_baseline.py`            |

---

## 🚀 Getting Started

1. Install dependencies

```bash
pip install -r requirements.txt
```

2. Run an example script

```bash
python rag_qasper_extractive_with_algo.py
```

---

## 🔧 Features

- 🖼️ Multimodal support: Table & image parsing from PDFs
- 🎯 Enhanced retrieval with CLIP-based image-text alignment
- 📊 Evaluation-ready pipeline for baseline vs. enhanced RAG
- 🗂️ Clear script organization by question type and approach

---

## 🧪 Progress

- [x] Baseline RAG for all question types
- [x] Enhanced algorithm with multimodal integration
- [ ] Full evaluation & analysis
- [ ] LangChain / LlamaIndex integration
- [ ] UI / CLI wrapper (optional)

---

## 📘 References

- Qasper Dataset: https://allenai.org/data/qasper  
- RAG Evaluation: https://github.com/explodinggradients/ragas  
- Vision Models: CLIP, BLIP, Azure Captioning  

---

## 🤝 Contributions

Feel free to open issues or PRs to contribute, suggest improvements, or report bugs!
