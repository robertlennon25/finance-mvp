alter table public.pipeline_runs
  add column if not exists job_id text unique,
  add column if not exists progress integer not null default 0,
  add column if not exists updated_at timestamptz not null default timezone('utc', now());

drop trigger if exists pipeline_runs_set_updated_at on public.pipeline_runs;
create trigger pipeline_runs_set_updated_at
before update on public.pipeline_runs
for each row
execute function public.set_updated_at();
