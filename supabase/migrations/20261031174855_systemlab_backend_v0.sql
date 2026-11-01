-- SystemLab Backend v0: server-owned analysis metadata, artifacts, and queue.

create extension if not exists pgmq;

create table public.analyses (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    repository_url text not null check (char_length(repository_url) between 1 and 2048),
    commit_sha text,
    analyzer_version text,
    schema_version text,
    status text not null default 'QUEUED' check (
        status in (
            'QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL_SUCCESS',
            'LOW_CONFIDENCE', 'FAILED', 'TIMEOUT', 'UNSUPPORTED'
        )
    ),
    metrics jsonb not null default '{}'::jsonb check (jsonb_typeof(metrics) = 'object'),
    attempt_count integer not null default 0 check (attempt_count >= 0),
    failure_message text,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    completed_at timestamptz,
    updated_at timestamptz not null default now()
);

create table public.analysis_artifacts (
    analysis_id uuid primary key references public.analyses(id) on delete cascade,
    graph jsonb not null check (jsonb_typeof(graph) = 'object'),
    report jsonb not null check (jsonb_typeof(report) = 'object'),
    errors jsonb not null check (jsonb_typeof(errors) = 'object'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index analyses_user_created_at_idx
    on public.analyses (user_id, created_at desc);

create index analyses_status_idx
    on public.analyses (status);

create unique index analyses_one_active_per_user_idx
    on public.analyses (user_id)
    where status in ('QUEUED', 'RUNNING');

alter table public.analyses enable row level security;
alter table public.analysis_artifacts enable row level security;

-- Backend v0 intentionally has no Data API policies. Only the direct, server-only
-- Postgres connection can access these tables.
revoke all on table public.analyses from anon, authenticated;
revoke all on table public.analysis_artifacts from anon, authenticated;

do $$
begin
    if not exists (select 1 from pgmq.meta where queue_name = 'analysis_jobs') then
        perform pgmq.create('analysis_jobs');
    end if;
end
$$;

-- Retain the existing event trigger while removing client-callable access to its
-- security-definer helper. The conditional keeps fresh local databases portable.
do $$
begin
    if to_regprocedure('public.rls_auto_enable()') is not null then
        execute 'revoke execute on function public.rls_auto_enable() from public, anon, authenticated';
    end if;
end
$$;
