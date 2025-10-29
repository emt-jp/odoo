-- Initialize Odoo database
CREATE DATABASE odoo;
CREATE DATABASE odoo_test;

-- Create extensions
\c odoo;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "ltree";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\c odoo_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS "ltree";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone
\c odoo;
SET timezone = 'UTC';

\c odoo_test;
SET timezone = 'UTC';




