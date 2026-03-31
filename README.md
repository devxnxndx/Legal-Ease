# LegalEase AI

AI-powered legal document analysis — RAG chatbot with Gemini + Supabase + Next.js.

## Architecture

```
Browser (Next.js 15)
  └─ /api/* → proxied by next.config.ts →
       FastAPI (Python) on :8000
         ├─ Gemini (chat, embeddings, TTS, STT)
         └─ Supabase (Postgres + pgvector + Storage)
```

## Quick Start

### 1. Supabase setup

Create a project at https://supabase.com and run the SQL schema (see `schema.sql`).
Enable the `vector` extension in your project's SQL editor:
```sql
create extension if not exists vector;
```

### 2. Python backend

```bash
cd legalease-python-backend
cp .env.example .env   # already copied — fill in your keys
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Fill in `.env`:
- `GEMINI_API_KEY` — from https://aistudio.google.com/app/apikey
- `NEXT_PUBLIC_SUPABASE_URL` — your project URL from Supabase Settings → API
- `SUPABASE_SERVICE_ROLE_KEY` — service_role secret from Supabase Settings → API

### 3. Next.js frontend

```bash
cd final_project
npm install
npm run dev
```

Open http://localhost:3000

## API Routes (all proxied to Python)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cases` | List all cases |
| DELETE | `/api/cases/:id` | Delete a case |
| POST | `/api/cases/upload` | Create case + upload first PDF |
| POST | `/api/cases/upload-doc` | Add PDF to existing case |
| POST | `/api/cases/:id/chat` | Streaming SSE chat |
| GET | `/api/cases/:id/chat` | Fetch chat history |
| GET | `/api/cases/:id/pdf` | Get signed PDF URL |
| POST | `/api/voice/transcribe` | Audio → text (STT) |
| POST | `/api/voice/speak` | Text → WAV audio (TTS) |

## Supabase Schema (required tables)

```sql
-- Cases
create table cases (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  status text not null default 'processing',
  created_at timestamptz default now()
);

-- Documents
create table documents (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references cases(id) on delete cascade,
  name text not null,
  storage_path text not null,
  page_count int,
  created_at timestamptz default now()
);

-- Chunks with pgvector embeddings
create table document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid references documents(id) on delete cascade,
  case_id uuid references cases(id) on delete cascade,
  content text not null,
  page_number int,
  chunk_index int,
  embedding vector(768),
  created_at timestamptz default now()
);

-- Chat messages
create table chat_messages (
  id uuid primary key default gen_random_uuid(),
  case_id uuid references cases(id) on delete cascade,
  role text not null,
  content text not null,
  sources jsonb,
  created_at timestamptz default now()
);

-- Vector similarity search function
create or replace function match_document_chunks(
  query_embedding vector(768),
  match_case_id uuid,
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  page_number int,
  similarity float
)
language sql stable as $$
  select
    id, document_id, content, page_number,
    1 - (embedding <=> query_embedding) as similarity
  from document_chunks
  where case_id = match_case_id
    and 1 - (embedding <=> query_embedding) > match_threshold
  order by embedding <=> query_embedding
  limit match_count;
$$;

-- Storage bucket
insert into storage.buckets (id, name, public)
values ('legal-documents', 'legal-documents', false)
on conflict do nothing;
```
