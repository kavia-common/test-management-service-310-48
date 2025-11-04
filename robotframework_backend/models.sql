-- PostgreSQL schema for robot-runner service
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";


CREATE TABLE IF NOT EXISTS tests (
id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
name text NOT NULL,
description text,
variables jsonb DEFAULT '{}'::jsonb,
minio_key text NOT NULL,
filename text NOT NULL,
created_at timestamptz NOT NULL DEFAULT now(),
updated_at timestamptz NOT NULL DEFAULT now()
);


CREATE TYPE run_status AS ENUM ('queued','running','completed','failed');


CREATE TABLE IF NOT EXISTS runs (
id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
test_id uuid REFERENCES tests(id) ON DELETE CASCADE,
run_name text,
tags jsonb,
status run_status NOT NULL DEFAULT 'queued',
started_at timestamptz,
finished_at timestamptz,
summary jsonb,
created_at timestamptz NOT NULL DEFAULT now()
);


CREATE TABLE IF NOT EXISTS test_results (
id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
run_id uuid REFERENCES runs(id) ON DELETE CASCADE,
case_name text NOT NULL,
status text NOT NULL,
message text,
duration_ms integer
);


CREATE INDEX IF NOT EXISTS idx_runs_test_id ON runs(test_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_created_at ON runs(created_at);

ALTER TABLE runs
  ADD COLUMN IF NOT EXISTS variables jsonb,
  ADD COLUMN IF NOT EXISTS cases jsonb;

-- Add case_inputs column to tests table for storing extracted test case input variables
ALTER TABLE tests
  ADD COLUMN IF NOT EXISTS case_inputs jsonb DEFAULT '{}'::jsonb;

ALTER TABLE runs
  ADD COLUMN artifacts jsonb;