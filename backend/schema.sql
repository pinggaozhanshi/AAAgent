-- AAAgent SQLite schema for professional mode v0.1.3.
-- Run this schema through backend/database.py. Do not store raw API keys here.

PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;

CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_profiles (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL COLLATE NOCASE,
  role TEXT NOT NULL CHECK (role IN ('planner', 'executor', 'both')),
  provider TEXT NOT NULL,
  base_url TEXT NOT NULL,
  model TEXT NOT NULL,
  parameters_json TEXT NOT NULL DEFAULT '{}',
  credential_ref TEXT NOT NULL,
  is_archived INTEGER NOT NULL DEFAULT 0 CHECK (is_archived IN (0, 1)),
  last_verified_at TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(name)
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  mode TEXT NOT NULL DEFAULT 'casual' CHECK (mode IN ('casual', 'professional')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  archived_at TEXT
);

CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
  content TEXT NOT NULL,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  user_message_id TEXT REFERENCES messages(id) ON DELETE SET NULL,
  mode TEXT NOT NULL CHECK (mode IN ('casual', 'professional')),
  status TEXT NOT NULL CHECK (status IN ('planning', 'awaiting_approval', 'running', 'completed', 'failed', 'cancelled', 'budget_exhausted')),
  planner_profile_id TEXT REFERENCES api_profiles(id) ON DELETE SET NULL,
  executor_profile_id TEXT REFERENCES api_profiles(id) ON DELETE SET NULL,
  planner_profile_snapshot_json TEXT,
  executor_profile_snapshot_json TEXT,
  token_budget INTEGER CHECK (token_budget IS NULL OR token_budget >= 0),
  cost_budget_microunits INTEGER CHECK (cost_budget_microunits IS NULL OR cost_budget_microunits >= 0),
  timeout_seconds INTEGER CHECK (timeout_seconds IS NULL OR timeout_seconds > 0),
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  cancel_requested_at TEXT,
  error_summary TEXT
);

CREATE TABLE IF NOT EXISTS task_graphs (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL UNIQUE REFERENCES runs(id) ON DELETE CASCADE,
  graph_version TEXT NOT NULL DEFAULT '1.0',
  graph_json TEXT NOT NULL,
  readable_plan_markdown TEXT,
  validation_result_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  parent_task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  sequence_hint INTEGER,
  title TEXT NOT NULL,
  instruction TEXT NOT NULL,
  acceptance_criteria_json TEXT NOT NULL DEFAULT '[]',
  expected_output TEXT NOT NULL CHECK (expected_output IN ('text', 'markdown', 'file', 'structured_data')),
  risk_level TEXT NOT NULL DEFAULT 'read_only' CHECK (risk_level IN ('read_only', 'confirm_before_write', 'dangerous')),
  status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'ready', 'running', 'completed', 'failed', 'blocked', 'cancelled')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  max_attempts INTEGER NOT NULL DEFAULT 2 CHECK (max_attempts BETWEEN 0 AND 5),
  input_summary TEXT,
  output_summary TEXT,
  error_summary TEXT,
  started_at TEXT,
  finished_at TEXT,
  duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_dependencies (
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  prerequisite_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (task_id, prerequisite_task_id),
  CHECK (task_id <> prerequisite_task_id)
);

CREATE TABLE IF NOT EXISTS task_artifacts (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  kind TEXT NOT NULL CHECK (kind IN ('text', 'markdown', 'file', 'structured_data', 'tool_result')),
  storage_ref TEXT,
  content_text TEXT,
  summary TEXT NOT NULL,
  checksum TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (storage_ref IS NOT NULL OR content_text IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS usage_records (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  usage_role TEXT NOT NULL CHECK (usage_role IN ('planner', 'executor', 'chat', 'repair')),
  provider TEXT NOT NULL,
  model TEXT NOT NULL,
  input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
  output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
  total_tokens INTEGER CHECK (total_tokens IS NULL OR total_tokens >= 0),
  usage_source TEXT NOT NULL CHECK (usage_source IN ('provider_reported', 'estimated')),
  currency TEXT NOT NULL DEFAULT 'USD',
  cost_microunits INTEGER CHECK (cost_microunits IS NULL OR cost_microunits >= 0),
  price_table_version TEXT,
  latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
  provider_request_id TEXT,
  completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run_events (
  id TEXT PRIMARY KEY,
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('run_started', 'plan_created', 'plan_invalid', 'task_ready', 'task_started', 'task_completed', 'task_failed', 'task_blocked', 'task_cancelled', 'approval_requested', 'approval_granted', 'approval_rejected', 'usage_recorded', 'run_completed', 'run_failed', 'run_cancelled', 'budget_exhausted')),
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_session_created ON messages(session_id, created_at);
CREATE INDEX IF NOT EXISTS idx_runs_session_started ON runs(session_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_tasks_run_status ON tasks(run_id, status);
CREATE INDEX IF NOT EXISTS idx_task_dependencies_prerequisite ON task_dependencies(prerequisite_task_id, task_id);
CREATE INDEX IF NOT EXISTS idx_usage_run_completed ON usage_records(run_id, completed_at);
CREATE INDEX IF NOT EXISTS idx_events_run_created ON run_events(run_id, created_at);

INSERT OR IGNORE INTO schema_migrations(version, name) VALUES (1, 'professional_mode_v0_1_3');