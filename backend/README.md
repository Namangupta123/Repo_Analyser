# SystemLab Backend

FastAPI API and durable Supabase Queue worker for the SystemLab repository analyzer.

## Local setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
cp .env.example .env
```

Set the real Supabase publishable key, pooled Postgres connection URL, and a random application secret in `.env`. Never commit `.env`.

For local HTTP development, keep `COOKIE_SECURE=false`. Set it to `true` behind HTTPS. `DATABASE_URL`, `APP_SECRET_KEY`, and any future secret key are backend-only values.

Run the API and worker in separate terminals:

```bash
systemlab-api
systemlab-worker
```

The API is available at `http://localhost:8000` with OpenAPI documentation at `/docs`.

Run the suites from the monorepo root:

```bash
backend/.venv/bin/pytest backend/tests analyzer/tests
```

## Supabase Auth

Enable the GitHub provider in the SystemLab Supabase project and allow these redirects:

```text
http://localhost:8000/api/v1/auth/callback
http://localhost:5173/auth/callback
```

In the GitHub OAuth App, use Supabase's provider callback:

```text
https://ieaodvyszjslropphvxe.supabase.co/auth/v1/callback
```

Then add the backend and frontend URLs above to the Supabase Auth redirect allow list. The GitHub client secret stays in the Supabase dashboard and must not be placed in this repository.

The backend requests only GitHub identity/email scopes. Repository analysis accepts public GitHub URLs and does not request the GitHub `repo` scope.

## API surface

- `GET /health` and `GET /ready`
- `GET /api/v1/auth/github`, `GET /api/v1/auth/callback`
- `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/me`
- `POST /api/v1/analyses`, `GET /api/v1/analyses`
- `GET`/`DELETE /api/v1/analyses/{id}`
- `GET /api/v1/analyses/{id}/{graph|report|errors}`

The API and worker use a direct server-only Postgres connection. The `analyses` and `analysis_artifacts` tables intentionally have RLS enabled with no client Data API policies.

