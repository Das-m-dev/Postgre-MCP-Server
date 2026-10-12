-- Run this using a PostgreSQL administrator account.

CREATE USER mcp_readonly
WITH PASSWORD 'CHANGE_ME';


-- Allow the user to connect
GRANT CONNECT
ON DATABASE my_database
TO mcp_readonly;


-- Allow access to public schema
GRANT USAGE
ON SCHEMA public
TO mcp_readonly;


-- Existing tables
GRANT SELECT
ON ALL TABLES
IN SCHEMA public
TO mcp_readonly;


-- Existing sequences
GRANT SELECT
ON ALL SEQUENCES
IN SCHEMA public
TO mcp_readonly;


-- Automatically give SELECT permission
-- to tables created in the future.
ALTER DEFAULT PRIVILEGES
IN SCHEMA public
GRANT SELECT
ON TABLES
TO mcp_readonly;