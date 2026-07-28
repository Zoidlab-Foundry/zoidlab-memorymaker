-- Foundry local-dev database roles (§3.2 per-tenant RLS).
--
-- The postgres image runs this once, on first init, as POSTGRES_USER (foundry).
-- foundry owns the schema and bypasses RLS by design -- it is what
-- DATABASE_URL_ADMIN points at, and what creates the tables.
--
-- app_rls is the role every request runs as. FORCE ROW LEVEL SECURITY policies key
-- on the `app.current_owner` setting, so this role must stay NOSUPERUSER /
-- NOBYPASSRLS and must never own the tables, or the policies would not apply.

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_rls') THEN
    CREATE ROLE app_rls LOGIN PASSWORD 'app_rls'
      NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS NOINHERIT;
  END IF;
END
$$;

DO $$
BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO app_rls', current_database());
END
$$;

GRANT USAGE ON SCHEMA public TO app_rls;

-- Tables and sequences are created later, at backend startup, over DATABASE_URL_ADMIN
-- (foundry). These default privileges make each new object reachable by app_rls without
-- another grant -- the RLS policies, not the grants, are what isolate tenants.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rls;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO app_rls;

-- ...and cover anything that already exists in a re-used volume.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_rls;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_rls;
