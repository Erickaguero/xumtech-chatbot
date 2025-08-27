from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple
import threading, re, unicodedata
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from rapidfuzz import fuzz

# --------- Tuning (más sensible) ---------
import os

def getenv_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

# Defaults más flexibles (se aplican al hacer commit y desplegar)
ALPHA = getenv_float("NLP_ALPHA", 0.6)          # más peso al fuzzy que antes
THRESH_UNDERSTOOD = getenv_float("NLP_UNDERSTOOD", 0.55)  # responde directo con menor puntaje
THRESH_AMBIG = getenv_float("NLP_AMBIG", 0.35)            # menos "no entendido"
TOPK = 3
# --------- Normalización ---------
_normalize_re = re.compile(r"[^\w\s]", flags=re.UNICODE)

def _strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfkd if unicodedata.category(ch) != "Mn")

def normalize(text: str) -> str:
    if not text:
        return ""
    t = _normalize_re.sub(" ", _strip_accents(text.lower().strip()))
    return re.sub(r"\s+", " ", t)

# --------- Index ---------
@dataclass
class Index:
    vectorizer: TfidfVectorizer
    tfidf_matrix: any
    faq_ids: List[int]
    questions_raw: List[str]
    questions_norm: List[str]

class NLPEngine:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._index: Index | None = None

    def build(self, questions: List[Tuple[int, str]]) -> None:
        """Construye el índice TF-IDF a partir de (id, question)."""
        faq_ids = [q[0] for q in questions]
        q_raw = [q[1] for q in questions]
        q_norm = [normalize(q) for q in q_raw]

        vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            analyzer="word",
            ngram_range=(1, 3),   # antes (1,2) ⇒ más recall
            min_df=1,
            max_df=1.0,           # no filtramos por frecuencia alta
            sublinear_tf=True     # suaviza TF (ayuda un poco)
        )
        tfidf_matrix = vectorizer.fit_transform(q_norm)

        with self._lock:
            self._index = Index(vectorizer, tfidf_matrix, faq_ids, q_raw, q_norm)

    def is_ready(self) -> bool:
        return self._index is not None

    def query(self, text: str):
        idx = self._index
        if idx is None:
            return None

        qn = normalize(text)
        if not qn:
            return None

        # ---- Similitud TF-IDF (coseno)
        qv = idx.vectorizer.transform([qn])
        cos_scores = linear_kernel(qv, idx.tfidf_matrix).flatten()

        # ---- Fuzzy “robusto” para textos cortos y con extras
        def _f(a: str, b: str) -> float:
            return max(
                fuzz.partial_ratio(a, b) / 100.0,   # 'hola' vs 'hola (buenas...)'
                fuzz.token_set_ratio(a, b) / 100.0, # ignora repeticiones/orden
                fuzz.QRatio(a, b) / 100.0           # respaldo general
            )

        fuzzy_scores = np.array([_f(qn, ref) for ref in idx.questions_norm], dtype=float)

        # ---- Mezcla dinámica: si la consulta es MUY corta, subimos el peso del fuzzy
        alpha = ALPHA
        if len(qn) <= 5 or len(qn.split()) <= 1:   # 'hola', 'hey', etc.
            alpha = min(0.5, ALPHA)                # como mucho 50% TF-IDF / 50% fuzzy

        final = alpha * cos_scores + (1.0 - alpha) * fuzzy_scores

        if final.size == 0:
            return None

        # ---- Top-K
        k = min(TOPK, final.size)
        top_idx = np.argpartition(-final, range(k))[:k]
        top_idx = top_idx[np.argsort(-final[top_idx])]

        return {
            "conf": float(final[top_idx[0]]),
            "faq_ids": [idx.faq_ids[i] for i in top_idx],
            "questions": [idx.questions_raw[i] for i in top_idx],
        }

engine = NLPEngine()