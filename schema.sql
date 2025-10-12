PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  telegram_id INTEGER NOT NULL UNIQUE,
  name TEXT,
  tz TEXT DEFAULT 'Europe/Zurich',
  xp_total REAL DEFAULT 0,
  level INTEGER DEFAULT 1,
  digest_hour INTEGER DEFAULT 9,
  notifications_enabled INTEGER DEFAULT 1,
  last_daily_digest TEXT,
  last_weekly_digest TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS domains (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  weight_bias REAL DEFAULT 1.0
);

INSERT OR IGNORE INTO domains (name, weight_bias)
VALUES ('coding',1.0),('research',1.0),('admin',1.0),('creative',1.0),('health',1.0),('recreation',1.0);

CREATE TABLE IF NOT EXISTS tasks (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  domain_id INTEGER REFERENCES domains(id),
  time_horizon TEXT CHECK(time_horizon IN ('now','short','mid','long')) DEFAULT 'short',
  energy TEXT CHECK(energy IN ('low','medium','high')) DEFAULT 'medium',
  priority TEXT CHECK(priority IN ('must','should','nice')) DEFAULT 'should',
  base_weight INTEGER DEFAULT 2,
  recurrence TEXT,
  due_at TEXT,
  status TEXT CHECK(status IN ('active','waiting','archived')) DEFAULT 'active',
  blocked INTEGER DEFAULT 0,
  novelty_bonus INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_at);

CREATE TABLE IF NOT EXISTS subtasks (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  order_idx INTEGER DEFAULT 0,
  done INTEGER DEFAULT 0,
  done_at TEXT
);

CREATE TABLE IF NOT EXISTS completions (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  completed_at TEXT NOT NULL,
  xp_earned REAL NOT NULL,
  streak_after INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS streaks (
  id INTEGER PRIMARY KEY,
  task_id INTEGER NOT NULL UNIQUE REFERENCES tasks(id) ON DELETE CASCADE,
  current_streak INTEGER DEFAULT 0,
  longest_streak INTEGER DEFAULT 0,
  last_completed_at TEXT
);

CREATE TABLE IF NOT EXISTS rewards (
  id INTEGER PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  xp_cost REAL DEFAULT 0,
  level_req INTEGER DEFAULT 1,
  claimed_at TEXT
);
