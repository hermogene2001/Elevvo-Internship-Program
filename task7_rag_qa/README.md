# Task 7 — LLM-Powered Document Q&A Tool (RAG Basics)

**Level: Industry · Module 8**

Build a minimal RAG tool using 3–5 short sample text documents. Split each into
fixed-size chunks, generate embeddings using a local or API embedding method,
store them in a simple vector store, retrieve the most similar chunk(s) on a
question, pass them to an LLM to answer, and cite which chunks were used.
Enforce a configurable similarity-score threshold below which it must respond
"I don't know" — this is enforced in code, not just by prompt wording. Tested
with an out-of-scope question.

**Covered topics:** Retrieval-Augmented Generation (RAG) basics · Embeddings & Similarity Search · LLM API Integration · Prompt Engineering · Confidence Thresholds

**Bonus:** Can be extended with Streamlit/Gradio or a larger/multi-format set.

## Files

| File | Purpose |
|------|---------|
| `rag_qa.py` | RAG pipeline (chunking, embeddings, vector store, retrieval, answering, threshold). |
| `test_rag.py` | Tests for retrieval, out-of-scope "I don't know", and threshold. |
| `sample_docs/` | Auto-created 5 short sample documents. |

## Run

```bash
cd task7_rag_qa
python rag_qa.py
```

## Features

- **Documents** — Loads 3–5 `.txt` files from `sample_docs/` (auto-created on first run).
- **Chunking** — Fixed-size chunks with configurable overlap.
- **Embeddings** — Supports local `sentence-transformers` (`all-MiniLM-L6-v2`, normalized) or OpenAI embeddings. Falls back gracefully if not installed.
- **Vector store** — Uses `faiss` (IndexFlatIP, cosine similarity on normalized vectors) if available, otherwise in-memory numpy fallback.
- **Retrieval** — Top-k similarity search.
- **Answering** — Passes retrieved chunks as context to an LLM (OpenAI) or uses a deterministic grounded fallback if no API key.
- **Citations** — Returns which chunk IDs/sources were used with similarity scores.
- **Threshold (code-level)** — If no retrieved chunk meets `similarity_threshold`, the tool returns **"I don't know"** without calling the LLM. Tested with "What is the capital of France?" (out of scope).
- **Privacy** — Only uses sample/public documents; never uploads private/sensitive files to third parties.

## Tests

```bash
python -m unittest test_rag -v
# or: pytest test_rag.py -v
```

Tests confirm retrieval works, out-of-scope questions return "I don't know" with no citations, and the threshold is enforced.

## Dependencies

```bash
pip install sentence-transformers faiss-cpu numpy openai python-dotenv
```
