-- CREATE DATABASE exsclaim;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE save_extensions AS ENUM('zip', 'tar.gz', '7z');
CREATE TYPE STATUS AS ENUM('Running', 'Finished', 'Closed due to an error');

CREATE TABLE IF NOT EXISTS results(
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    start_time TIMESTAMP NOT NULL DEFAULT NOW(),
    end_time TIMESTAMP DEFAULT NULL,
    search_query JSONB NOT NULL,
    extension save_extensions NOT NULL default 'tar.gz'::save_extensions,
    status STATUS NOT NULL DEFAULT 'Running'::STATUS
);
