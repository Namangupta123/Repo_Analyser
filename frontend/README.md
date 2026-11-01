# SystemLab Frontend

React and React Flow frontend for submitting repository analyses and exploring their deterministic dependency graphs.

## Requirements

- Node.js 22.22.2, or Node.js 24.15 and newer
- The SystemLab API running at `http://localhost:8000`
- GitHub OAuth configured in Supabase

## Setup

```bash
cd frontend
npm ci
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`. The frontend communicates only with FastAPI; it never reads Supabase tables directly.

## Commands

```bash
npm run dev
npm run build
npm test
```

The access token is held in memory. The rotated refresh token remains in the backend-issued HttpOnly cookie and is never written to local storage.
