# Xumtech Chatbot

Mini bot conversacional (FastAPI + Frontend estático) para responder preguntas frecuentes usando **TF‑IDF + fuzzy matching**. Diseñado para correr **100% en el navegador** sin instalaciones extra del usuario, con **API REST** y almacenamiento en **SQLite** (o Postgres opcional).

> Demo (Render): `https://xumtech-chatbot.onrender.com/`

---

## ✨ Características

* UI ligera (HTML/CSS/JS) servida por FastAPI (same‑origin, sin CORS en prod).
* Respuestas en < 5 s (típicamente < 100 ms) con **TF‑IDF (word+char)** + **RapidFuzz**.
* Estados: `understood`, `ambiguous` (con sugerencias) y `not_understood`.
* **Entrenamiento** por:

  * `seed_data.json` (fuente de verdad por commit)
  * Endpoints admin (`POST /api/faq`, `POST /api/faq/bulk`)
  * Scripts de importación masiva
* Persistencia: **SQLite** (por defecto) o **Postgres** (`DB_URL`).
* Seguridad: endpoints admin con **Bearer** (`ADMIN_TOKEN`).
* Móvil: input a 16px y meta viewport para evitar **zoom** al enfocar (iOS).

---

## 🧱 Stack

* **Backend:** FastAPI, Uvicorn, SQLAlchemy, Pydantic
* **NLP:** scikit‑learn, RapidFuzz, NumPy/SciPy
* **DB:** SQLite local, Postgres opcional
* **Infra demo:** Render Web Service

---

## 📁 Estructura del proyecto

```
xumtech-chatbot/
├─ backend/
│  ├─ app.py               # FastAPI + endpoints + serve frontend
│  ├─ nlp.py               # Normalización + índice TF‑IDF + fuzzy
│  ├─ db.py                # Engine + sesión + seed/reseed helpers
│  ├─ models.py, schemas.py
│  ├─ seed_data.json       # FAQs por defecto (fuente de verdad)
│  ├─ requirements.txt
│  └─ (tools/ scripts de import opcional)
└─ frontend/
   ├─ index.html           # Chat UI (API_BASE="" en prod)
   └─ styles.css           # Tema + fix móvil (font-size ≥ 16px)
```

---

## 🚀 Arranque local (como producción: FastAPI sirve el frontend)

```powershell
cd C:\Users\erick\Python\xumtech-chatbot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

$env:ADMIN_TOKEN = "supersecreto123"           # para endpoints admin
# Sensibilidad NLP (opcionales)
$env:NLP_ALPHA = "0.6"; $env:NLP_UNDERSTOOD = "0.55"; $env:NLP_AMBIG = "0.35"

python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

* Frontend: `http://127.0.0.1:8000/`
* Docs/Swagger: `http://127.0.0.1:8000/docs`
* Health: `http://127.0.0.1:8000/health`

### Reiniciar con seed nuevo

```powershell
Ctrl+C
Remove-Item .\backend\data.db -ErrorAction Ignore
python -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

---

## ⚙️ Variables de entorno

| Variable         | Ejemplo                  | Descripción                             |
| ---------------- | ------------------------ | --------------------------------------- |
| `ADMIN_TOKEN`    | `supersecreto123`        | Token Bearer para endpoints admin       |
| `NLP_ALPHA`      | `0.6`                    | Mezcla cosine vs fuzzy (↑ = más cosine) |
| `NLP_UNDERSTOOD` | `0.55`                   | Umbral para responder directo           |
| `NLP_AMBIG`      | `0.35`                   | Umbral para marcar ambiguo              |
| `DB_PATH`        | `/data/data.db`          | Ruta SQLite (Render Disk)               |
| `DB_URL`         | `postgresql+psycopg://…` | Postgres opcional                       |

> En prod (Render) puedes definirlas en **Environment** y verificar en `/health`.

---

## 🧠 Entrenamiento (FAQs)

### 1) Seed (por commit)

Edita **`backend/seed_data.json`** (UTF‑8, lista de objetos `{question, answer, tags?}`) y reinicia la DB (local) o redeploy (sin Disk) para que tome el seed.

### 2) Swagger (admin)

`POST /api/faq` en `/docs` con header:

```
Authorization: Bearer supersecreto123
```

### 3) Importación masiva (scripts)

Ejemplo (carpeta con muchos `.json`):

```powershell
python tools\import_folder.py backend\lote_jsons --base http://127.0.0.1:8000 --token supersecreto123
# Producción
python tools\import_folder.py backend\lote_jsons --base https://xumtech-chatbot.onrender.com --token supersecreto123
```

### 4) Reseed (opcional)

Endpoint admin para vaciar tabla y resembrar desde `seed_data.json`:

```
POST /api/admin/reseed   (Authorization: Bearer …)
```

---

## 🔌 API rápida

| Método | Ruta            | Descripción                                      |
| ------ | --------------- | ------------------------------------------------ |
| GET    | `/health`       | Estado + parámetros NLP                          |
| GET    | `/api/faq`      | Lista de FAQs (id, question)                     |
| POST   | `/api/faq`      | **Admin**. Crear FAQ                             |
| POST   | `/api/faq/bulk` | **Admin**. Carga masiva (opcional)               |
| POST   | `/api/query`    | Consulta del chat `{message}` → respuesta/estado |
| GET    | `/docs`         | Swagger UI                                       |

---

## 🧩 Frontend

* `frontend/index.html` debe tener `API_BASE = ""` en producción (same‑origin).
* Meta viewport recomendado:

```html
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover, interactive-widget=resizes-content">
```

* Fix móvil: en `styles.css` los elementos `input/textarea/button` con `font-size: 16px` para evitar zoom al enfocar (iOS).

---

## ☁️ Deploy en Render (Web Service)

1. Subir repo a GitHub.
2. Render → **New → Web Service** → conecta el repo.
3. **Build:** `pip install -r backend/requirements.txt`
4. **Start:** `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`
5. **Env vars:** `ADMIN_TOKEN`, `NLP_*` y opcional `DB_PATH` o `DB_URL`.
6. (Opcional) **Disk** para SQLite persistente → mount `/data` + `DB_PATH=/data/data.db`.
7. Deploy. Verifica `/health` y `/docs`.

---

## 🔒 Seguridad

* Endpoints admin protegidos por **Bearer**.
* Same‑origin en producción (frontend servido por FastAPI).
* CORS restringido en desarrollo a `127.0.0.1:5500` si sirves el frontend aparte.
* (Opcional) Rate limiting y logs con `RotatingFileHandler`.

---

## 📈 Escalabilidad y mejoras

* DB a **Postgres** + pool de conexiones.
* Índice TF‑IDF incremental y/o embeddings + ANN.
* Cache de respuestas frecuentes.
* CDN para estáticos.
* Telemetría (Prometheus/Grafana, OpenTelemetry).
* UI: accesibilidad, i18n, y panel admin CRUD.

---

## 🧪 Pruebas de aceptación

* ≥ 10 FAQs en `seed_data.json`.
* 3 escenarios: understood (directo), ambiguous (sugerencias), not\_understood.
* Latencia típica < 100 ms (ver logs) y < 5 s garantizado.

---

## 🔧 Troubleshooting

* **No toma el seed:** borra `backend/data.db` (local) o usa `/api/admin/reseed` (prod con Disk).
* **“Sin conexión” en prod:** revisa `API_BASE = ""` y `/health` ok.
* **Cache CSS/JS:** hard reload o usa `?v=fecha` en `<link>`.
* **“Hola” no responde en prod:** asegúrate de cargar esa FAQ en producción o incluirla en el seed.

---

## 📜 Licencia

MIT (o la que definas).

---

## 👤 Autor

Erick Aguero — Prueba técnica Xumtech.
