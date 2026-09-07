# Frontend (Slice 1, next step)

Not scaffolded yet — build this after the backend upload/list API is
confirmed working locally. Suggested setup:

```bash
npx create-next-app@latest . --typescript --tailwind --app
```

Then a single page that:
1. Posts a file to `POST /documents/upload`
2. Lists documents from `GET /documents` in a table with status badges
