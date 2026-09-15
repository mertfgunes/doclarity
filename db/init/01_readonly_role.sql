-- Least-privilege role for LLM-generated SQL (Slice 4 - text-to-SQL analytics).
-- Runs automatically on first container init (mounted into
-- /docker-entrypoint-initdb.d/ by docker-compose.yml). Only ever grants
-- SELECT - this is the "can't write even if the generated SQL tries to"
-- guardrail; which specific tables a query may touch is a separate,
-- app-level check (see app/services/sql_guard.py).
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'doclarity_readonly') THEN
        CREATE ROLE doclarity_readonly LOGIN PASSWORD 'doclarity_readonly';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE doclarity TO doclarity_readonly;
GRANT USAGE ON SCHEMA public TO doclarity_readonly;

-- Covers tables that already exist at the time this runs.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO doclarity_readonly;

-- Covers tables the app creates later (SQLAlchemy's create_all, run by the
-- `doclarity` app user) - without this, new tables would default to no
-- access for the readonly role.
ALTER DEFAULT PRIVILEGES FOR ROLE doclarity IN SCHEMA public GRANT SELECT ON TABLES TO doclarity_readonly;
