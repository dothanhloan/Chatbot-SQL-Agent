"""
Static data RAG module (đơn giản, giống flow chatbot CLI cũ).
- Đọc tất cả file .docx trong thư mục data/
- Chia nhỏ văn bản thành các đoạn (chunks)
- Tạo embedding bằng sentence-transformers (HuggingFaceEmbeddings)
- Lưu vào FAISS trong bộ nhớ
- Cho phép retrieve top-k đoạn liên quan và build context text
"""

import os
import logging
from pathlib import Path
from typing import List, Tuple

from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
K_DEFAULT = 3


class StaticRAG:
    def __init__(self) -> None:
        self.embeddings = None
        self.vector_store = None
        self.initialized = False

    def _load_docx_files(self) -> List[Tuple[str, str]]:
        if not DATA_DIR.exists():
            logger.warning("StaticRAG: data dir does not exist: %s", DATA_DIR)
            return []

        docs: List[Tuple[str, str]] = []
        for path in DATA_DIR.glob("*.docx"):
            try:
                doc = DocxDocument(str(path))
                text = "\n".join(p.text for p in doc.paragraphs)
                text = text.strip()
                if text:
                    docs.append((path.name, text))
                    logger.info("StaticRAG: loaded %s (%d chars)", path.name, len(text))
            except Exception as e:  # noqa: BLE001
                logger.error("StaticRAG: error reading %s: %s", path, e)
        return docs

    def initialize(self) -> bool:
        """Build embeddings + FAISS index in memory.

        Trả về True nếu khởi tạo thành công, False nếu không.
        """
        try:
            docs = self._load_docx_files()
            if not docs:
                logger.warning("StaticRAG: no .docx files found in %s", DATA_DIR)
                return False

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
            )

            texts: List[str] = []
            metadatas = []
            for filename, full_text in docs:
                chunks = splitter.split_text(full_text)
                for idx, chunk in enumerate(chunks):
                    texts.append(chunk)
                    metadatas.append({"filename": filename, "chunk_index": idx})

            if not texts:
                logger.warning("StaticRAG: no chunks generated from documents")
                return False

            logger.info("StaticRAG: loading embedding model %s", EMBEDDING_MODEL)
            self.embeddings = HuggingFaceEmbeddings(
                model_name=EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
            )

            logger.info("StaticRAG: building FAISS index with %d chunks", len(texts))
            self.vector_store = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
            self.initialized = True
            logger.info("StaticRAG: initialized successfully")
            return True
        except Exception as e:  # noqa: BLE001
            logger.error("StaticRAG: failed to initialize: %s", e, exc_info=True)
            self.initialized = False
            self.vector_store = None
            return False

    def is_initialized(self) -> bool:
        return bool(self.initialized and self.vector_store is not None)

    def build_context(self, question: str, k: int = K_DEFAULT) -> str:
        """Retrieve top-k relevant chunks and concatenate into a context string."""
        if not self.is_initialized():
            logger.warning("StaticRAG: called build_context but not initialized")
            return ""

        try:
            docs_and_scores = self.vector_store.similarity_search_with_score(question, k=k)
            if not docs_and_scores:
                return ""

            parts: List[str] = []
            for idx, (doc, score) in enumerate(docs_and_scores, start=1):
                meta = doc.metadata or {}
                filename = meta.get("filename", "unknown")
                chunk_index = meta.get("chunk_index", "?")
                header = f"[Nguồn {idx}: {filename} - chunk {chunk_index}, score={score:.3f}]"
                parts.append(header)
                parts.append(doc.page_content)

            return "\n\n".join(parts)
        except Exception as e:  # noqa: BLE001
            logger.error("StaticRAG: error building context: %s", e, exc_info=True)
            return ""


# Singleton instance
_rag_instance: StaticRAG | None = None


def get_rag_instance() -> StaticRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = StaticRAG()
    return _rag_instance


def initialize_rag() -> bool:
    rag = get_rag_instance()
    return rag.initialize()


def build_static_context(question: str, k: int = K_DEFAULT) -> str:
    rag = get_rag_instance()
    if not rag.is_initialized():
        return ""
    return rag.build_context(question, k=k)
