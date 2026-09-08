# Frontend

A single page: drag-and-drop upload + a document list that polls for status
and shows extraction results.

## Setup

```bash
cd frontend
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to localhost:8000
npm run dev
```

Requires the backend running (see the root `README.md`) — CORS on the API
is already configured for `http://localhost:3000`.

## What it does

- Drag-and-drop (or click to browse) uploads one or more files to
  `POST /documents/upload`.
- The document list polls `GET /documents` every 3s, so status changes
  (`uploaded` → `processing` → `processed`/`failed`) show up without a
  refresh.
- Click a row to expand it and fetch `GET /documents/{id}/extractions` —
  shows the structured fields, `needs_review` flags, and any error message.

No state is held beyond what the API returns; there's no separate frontend
data layer to keep in sync.
