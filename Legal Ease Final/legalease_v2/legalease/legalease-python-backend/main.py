from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import cases, upload, chat, pdf, voice, tags, deadlines, search
import os

app = FastAPI(title="LegalEase AI Backend", version="1.0.0")

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and any deployed frontend origin.
# Update ALLOWED_ORIGINS in your .env to restrict in production.
# ---------------------------------------------------------------------------
allowed_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers — each file mirrors one group of Next.js API routes
# ---------------------------------------------------------------------------
app.include_router(cases.router,  prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(chat.router,   prefix="/api")
app.include_router(pdf.router,    prefix="/api")
app.include_router(voice.router,     prefix="/api")
app.include_router(tags.router,      prefix="/api")
app.include_router(deadlines.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/")
async def root():
    return {"status": "LegalEase AI Backend running ✓"}


@app.get("/health")
async def health():
    return {"status": "ok"}
