-- Initialize database with schemas and roles for ClearSight Dashboard

-- Create reporting schema
CREATE SCHEMA IF NOT EXISTS rpt;

-- Create roles
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE ROLE readonly_user WITH LOGIN PASSWORD 'readonly_pass';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'reporting_user') THEN
        CREATE ROLE reporting_user WITH LOGIN PASSWORD 'reporting_pass';
    END IF;
END
$$;

-- Grant permissions: readonly_user can read public schema
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- Grant permissions: reporting_user has full access to rpt schema + read on public
GRANT USAGE ON SCHEMA public TO reporting_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO reporting_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO reporting_user;

GRANT ALL ON SCHEMA rpt TO reporting_user;
GRANT ALL ON ALL TABLES IN SCHEMA rpt TO reporting_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA rpt TO reporting_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA rpt GRANT ALL ON TABLES TO reporting_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA rpt GRANT ALL ON SEQUENCES TO reporting_user;
