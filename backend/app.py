from __future__ import annotations
import os
import json
from typing import List

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from .db import init_db, seed_if_empty, get_session
from .models import FAQ
from .schemas import FAQOut, FAQIn, QueryIn, QueryOut
from .nlp import engine, THRESH_UNDERSTOOD, THRESH_AMBIG

# Cargar variables de .env (opcional; igual tomará variables del entorno)
load_dotenv()

app = FastAPI(title="Xumtech Chatbot API", version="0.2.0")

# CORS (ajusta en producción)
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup() -> None:
    # Crear DB y sembrar FAQs si hace falta
    init_db()
    seed_if_empty()
    # Construir índice NLP con las preguntas actuales
    with next(get_session()) as s:  # type: ignore
        rows = s.execute(select(FAQ.id, FAQ.question)).all()
        engine.build([(r[0], r[1]) for r in rows])

@app.get("/health")
def health():
    return {"status": "ok", "nlp_ready": engine.is_ready()}

@app.get("/api/faq", response_model=List[FAQOut])
def list_faqs(session: Session = Depends(get_session)):
    rows = session.execute(select(FAQ.id, FAQ.question)).all()
    return [FAQOut(id=r[0], question=r[1]) for r in rows]

# Crear nueva FAQ (protegido con Bearer token)
@app.post("/api/faq", status_code=201)
def create_faq(
    payload: FAQIn,
    session: Session = Depends(get_session),
    authorization: str | None = Header(None, alias="Authorization"),
):
    admin_token = os.getenv("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN no configurado")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta Bearer token")
    token = authorization.replace("Bearer ", "", 1).strip()
    if token != admin_token:
        raise HTTPException(status_code=403, detail="Token inválido")

    tags_json = json.dumps(payload.tags) if payload.tags is not None else None
    faq = FAQ(question=payload.question, answer=payload.answer, tags=tags_json)
    session.add(faq)
    session.commit()

    # Reindexar el motor NLP con la nueva lista de preguntas
    rows = session.execute(select(FAQ.id, FAQ.question)).all()
    engine.build([(r[0], r[1]) for r in rows])

    return {"id": faq.id}

# Endpoint de consultas del chatbot
@app.post("/api/query", response_model=QueryOut)
def query(payload: QueryIn, session: Session = Depends(get_session)):
    if not engine.is_ready():
        raise HTTPException(status_code=503, detail="NLP no listo")

    res = engine.query(payload.message)
    if res is None:
        return QueryOut(
            answer=None, confidence=0.0, matched_question=None,
            alternatives=[], status="not_understood"
        )

    conf = res["conf"]
    top_ids = res["faq_ids"]
    top_qs = res["questions"]

    if conf >= THRESH_UNDERSTOOD:
        best = session.get(FAQ, top_ids[0])
        return QueryOut(
            answer=best.answer if best else None,
            confidence=conf,
            matched_question=top_qs[0],
            alternatives=[],
            status="understood",
        )

    if conf >= THRESH_AMBIG:
        return QueryOut(
            answer=None,
            confidence=conf,
            matched_question=top_qs[0],
            alternatives=top_qs,
            status="ambiguous",
        )

    return QueryOut(
        answer=None,
        confidence=conf,
        matched_question=None,
        alternatives=top_qs,
        status="not_understood",
    )


# --- Para desplegar a WEB ---
from pathlib import Path
from fastapi.staticfiles import StaticFiles

ROOT_DIR = Path(__file__).resolve().parents[1]  # repo root
FRONTEND_DIR = ROOT_DIR / "frontend"

# Sirve el frontend estático en "/"
# (mantén los endpoints /api/* y /docs como están)
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")