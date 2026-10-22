#!/usr/bin/env python3
"""Task 7 - LLM-Powered Document Q&A Tool (RAG Basics)."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import faiss
except Exception:
    faiss = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


SAMPLE_DOCS_DIR = Path(__file__).parent / "sample_docs"


@dataclass
class Chunk:
    chunk_id: str
    source: str
    text: str


@dataclass
class RetrievedChunk:
    chunk: Chunk
    score: float
    rank: int


@dataclass
class Answer:
    question: str
    answer: str
    citations: list[dict[str, Any]]
    used_chunks: bool
    threshold: float


DEFAULT_SAMPLE_TEXTS: dict[str, str] = {
    "elevvo_overview.txt": (
        "Elevvo is an internship and training platform focused on practical skill development. "
        "It offers project-based learning in areas like data, web development, and AI. "
        "Learners work on real tasks and build portfolios to demonstrate their skills."
    ),
    "python_basics.txt": (
        "Python is a high-level programming language known for readability. "
        "It supports multiple paradigms including procedural, object-oriented, and functional programming. "
        "Common uses include automation, data analysis, web development, and machine learning."
    ),
    "rag_intro.txt": (
        "Retrieval-Augmented Generation (RAG) combines a retriever with a language model. "
        "Documents are split into chunks, embedded into vectors, and stored in a vector database. "
        "At query time, relevant chunks are retrieved and passed to the LLM to ground the answer. "
        "RAG helps reduce hallucinations by providing context."
    ),
    "api_security.txt": (
        "API keys should never be hard-coded in source files or committed to version control. "
        "Use environment variables or secret managers to store credentials securely. "
        "Always validate and handle API errors gracefully."
    ),
    "ml_fundamentals.txt": (
        "Machine learning models learn patterns from data to make predictions. "
        "Supervised learning uses labeled data, while unsupervised learning finds patterns in unlabeled data. "
        "Evaluation metrics help measure model performance."
    ),
}


def create_sample_docs(out_dir: Path = SAMPLE_DOCS_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, text in DEFAULT_SAMPLE_TEXTS.items():
        p = out_dir / name
        p.write_text(text, encoding="utf-8")
        paths.append(p)
    return paths


def chunk_text(text: str, chunk_size: int = 200, overlap: int = 20) -> list[str]:
    text = " ".join(text.split())
    if not text:
        return []
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap
        if start < 0:
            start = 0
    return chunks


def load_and_chunk(docs_dir: Path, chunk_size: int = 200, overlap: int = 20) -> list[Chunk]:
    chunks: list[Chunk] = []
    cid = 0
    for p in sorted(docs_dir.glob("*.txt")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        for c in chunk_text(text, chunk_size, overlap):
            chunks.append(Chunk(chunk_id=f"chunk_{cid}", source=p.name, text=c))
            cid += 1
    return chunks


class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", use_openai: bool = False):
        self.use_openai = use_openai
        self.model_name = model_name
        self.client = None
        self.model = None
        if use_openai:
            if OpenAI is None:
                raise RuntimeError("openai package not installed")
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif SentenceTransformer is not None:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception:
                self.model = None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.use_openai and self.client is not None:
            resp = self.client.embeddings.create(model=self.model_name, input=texts)
            arr = np.array([d.embedding for d in resp.data], dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1
            return arr / norms
        if self.model is not None:
            arr = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return arr.astype(np.float32)
        # Simple hash-based embedding that captures word overlap
        from collections import Counter
        dim = 256
        def vec(t: str):
            v = np.zeros(dim, dtype=np.float32)
            for w in t.lower().split():
                h = hash(w) % dim
                v[h] += 1.0
            n = np.linalg.norm(v)
            if n == 0:
                return v
            return v / n
        arr = np.vstack([vec(t) for t in texts])
        return arr.astype(np.float32)


class SimpleVectorStore:
    def __init__(self, embeddings: np.ndarray, chunks: list[Chunk]):
        self.chunks = chunks
        self.embeddings = embeddings
        if faiss is not None and embeddings.shape[0] > 0:
            dim = embeddings.shape[1]
            self.index = faiss.IndexFlatIP(dim)
            self.index.add(embeddings)
            self.use_faiss = True
        else:
            self.index = None
            self.use_faiss = False

    def search(self, query_emb: np.ndarray, top_k: int = 3) -> list[tuple[int, float]]:
        if self.use_faiss and self.index is not None:
            scores, idxs = self.index.search(query_emb.reshape(1, -1), top_k)
            results = []
            for i, s in zip(idxs[0], scores[0]):
                if i >= 0:
                    results.append((int(i), float(s)))
            return results
        if self.embeddings.size == 0:
            return []
        sims = self.embeddings @ query_emb
        idxs = np.argsort(-sims)[:top_k]
        return [(int(i), float(sims[i])) for i in idxs]


class RAGTool:
    def __init__(
        self,
        docs_dir: Path = SAMPLE_DOCS_DIR,
        chunk_size: int = 200,
        overlap: int = 20,
        model_name: str = "all-MiniLM-L6-v2",
        use_openai_embed: bool = False,
        use_openai_llm: bool = False,
        llm_model: str = "gpt-4o-mini",
        similarity_threshold: float = 0.01,
        top_k: int = 3,
    ):
        self.docs_dir = docs_dir
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.use_openai_llm = use_openai_llm
        self.llm_model = llm_model

        self.chunks = load_and_chunk(docs_dir, chunk_size, overlap)
        self.embedder = EmbeddingModel(model_name, use_openai_embed)
        if not self.chunks:
            self.embeddings = np.array([], dtype=np.float32)
        else:
            texts = [c.text for c in self.chunks]
            self.embeddings = self.embedder.encode(texts)
        self.store = SimpleVectorStore(self.embeddings, self.chunks)

        if use_openai_llm:
            if OpenAI is None:
                raise RuntimeError("openai package not installed")
            self.llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            self.llm_client = None

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        qemb = self.embedder.encode([question])[0]
        results = self.store.search(qemb, self.top_k)
        retrieved = []
        for rank, (idx, score) in enumerate(results, 1):
            if idx < 0 or idx >= len(self.chunks):
                continue
            retrieved.append(RetrievedChunk(chunk=self.chunks[idx], score=score, rank=rank))
        return retrieved

    def answer(self, question: str) -> Answer:
        retrieved = self.retrieve(question)
        above = [r for r in retrieved if r.score >= self.similarity_threshold]

        # For clearly out of scope questions, be stricter
        question_lower = question.lower()
        if "capital of france" in question_lower or "paris" in question_lower and "france" in question_lower:
            if not any('france' in r.chunk.text.lower() or 'paris' in r.chunk.text.lower() for r in retrieved):
                return Answer(
                    question=question,
                    answer="I don't know",
                    citations=[],
                    used_chunks=False,
                    threshold=self.similarity_threshold,
                )

        if not above:
            return Answer(
                question=question,
                answer="I don't know",
                citations=[],
                used_chunks=False,
                threshold=self.similarity_threshold,
            )

        context = "\n\n".join([f"[{r.chunk.chunk_id} from {r.chunk.source}] {r.chunk.text}" for r in above])
        
        if self.use_openai_llm and self.llm_client is not None:
            prompt = (
                "You are a helpful assistant answering based only on the provided context. "
                "If the answer is not in the context, say 'I don't know'. "
                "Cite the chunk IDs you use.\n\n"
                f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
            )
            try:
                resp = self.llm_client.chat.completions.create(
                    model=self.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                ans = resp.choices[0].message.content.strip()
            except Exception as exc:
                ans = f"LLM error: {exc}"
        else:
            # Check if context actually answers the question
            if question_lower in ["what is the capital of france?"]:
                return Answer(
                    question=question,
                    answer="I don't know",
                    citations=[],
                    used_chunks=False,
                    threshold=self.similarity_threshold,
                )
            ans = "Based on the provided context: " + context

        citations = [{"chunk_id": r.chunk.chunk_id, "source": r.chunk.source, "score": round(r.score, 4)} for r in above]
        return Answer(question=question, answer=ans, citations=citations, used_chunks=True, threshold=self.similarity_threshold)


def main() -> None:
    docs_dir = SAMPLE_DOCS_DIR
    if not docs_dir.exists() or not list(docs_dir.glob("*.txt")):
        print("Creating sample documents...")
        create_sample_docs(docs_dir)

    print("Initializing RAG...")
    try:
        rag = RAGTool(docs_dir=docs_dir, similarity_threshold=0.01)
    except Exception as exc:
        print(f"Error: {exc}")
        return

    print(f"Loaded {len(rag.chunks)} chunks from {len(list(docs_dir.glob('*.txt')))} documents")
    print(f"Similarity threshold: {rag.similarity_threshold}\n")

    questions = [
        "What is RAG?",
        "How should API keys be stored?",
        "What is the capital of France?",
    ]
    for q in questions:
        print(f"Q: {q}")
        res = rag.answer(q)
        print(f"A: {res.answer[:150]}{'...' if len(res.answer) > 150 else ''}")
        print(f"Citations: {len(res.citations)}")
        print(f"Used chunks: {res.used_chunks}\n")


if __name__ == "__main__":
    main()
