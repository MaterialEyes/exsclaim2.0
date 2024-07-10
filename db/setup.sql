-- CREATE DATABASE exsclaim;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE save_extensions AS ENUM('zip', 'tar.gz', '7z');

CREATE TABLE results(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_time TIME DEFAULT NOW(),
    search_query JSONB NOT NULL,
    extension save_extensions NOT NULL default 'tar.gz'::save_extensions
);
