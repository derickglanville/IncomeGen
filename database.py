import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS user_profile (
  id INTEGER PRIMARY KEY CHECK (id = 1), full_name TEXT NOT NULL DEFAULT 'Derick Glanville',
  headline TEXT NOT NULL DEFAULT 'Experienced AI, software development, and healthcare IT professional',
  education TEXT NOT NULL DEFAULT 'Master''s degree in Natural Language Processing',
  experience TEXT NOT NULL DEFAULT 'Healthcare IT, enterprise applications, database development, systems integration, business process automation, AI and chatbot development',
  skills TEXT NOT NULL DEFAULT 'Python,C#,VB.NET,Java,SQL Server,T-SQL,ASP.NET,MVC,Angular,React,NLP,LLMs,Chatbot Development,Pandas,Excel,OpenPyXL,Playwright,Plotly,scikit-learn,Informatica,ETL,Healthcare IT',
  work_location TEXT NOT NULL DEFAULT 'Remote — United States', contract_types TEXT NOT NULL DEFAULT 'Independent contractor,Freelance,Part-time,Project-based',
  minimum_hourly_rate NUMERIC NOT NULL DEFAULT 25, preferred_hourly_rate_min NUMERIC NOT NULL DEFAULT 40,
  preferred_hourly_rate_max NUMERIC NOT NULL DEFAULT 75, weekly_hours_min INTEGER NOT NULL DEFAULT 5,
  weekly_hours_max INTEGER NOT NULL DEFAULT 20, monthly_income_goal NUMERIC NOT NULL DEFAULT 1500,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS platforms (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, official_url TEXT NOT NULL, category TEXT NOT NULL,
  priority TEXT NOT NULL CHECK(priority IN ('High','Medium','Low')), access_method TEXT NOT NULL,
  automation_status TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1, notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS opportunities (
  id INTEGER PRIMARY KEY, external_id TEXT, platform_id INTEGER NOT NULL REFERENCES platforms(id),
  company TEXT NOT NULL, title TEXT NOT NULL, description TEXT NOT NULL, required_skills TEXT NOT NULL DEFAULT '',
  preferred_skills TEXT NOT NULL DEFAULT '', compensation_min NUMERIC, compensation_max NUMERIC,
  compensation_period TEXT, currency TEXT NOT NULL DEFAULT 'USD', estimated_hours REAL,
  remote_eligibility TEXT NOT NULL DEFAULT 'Unknown', geographic_restrictions TEXT NOT NULL DEFAULT 'Unknown',
  contract_type TEXT NOT NULL DEFAULT 'Unknown', application_url TEXT NOT NULL, source_url TEXT NOT NULL,
  posting_date TEXT, application_deadline TEXT, status TEXT NOT NULL DEFAULT 'Discovered',
  application_requirements TEXT NOT NULL DEFAULT '', screening_requirements TEXT NOT NULL DEFAULT '',
  payment_arrangements TEXT NOT NULL DEFAULT 'Unknown', discovered_at TEXT NOT NULL,
  last_verified_at TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE, is_available INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
  UNIQUE(platform_id, external_id)
);
CREATE TABLE IF NOT EXISTS opportunity_sources (
  id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL REFERENCES opportunities(id) ON DELETE CASCADE,
  platform_id INTEGER NOT NULL REFERENCES platforms(id), source_url TEXT NOT NULL,
  external_id TEXT, discovered_at TEXT NOT NULL, UNIQUE(opportunity_id, source_url)
);
CREATE TABLE IF NOT EXISTS opportunity_matches (
  id INTEGER PRIMARY KEY, opportunity_id INTEGER NOT NULL UNIQUE REFERENCES opportunities(id) ON DELETE CASCADE,
  score INTEGER NOT NULL, recommendation TEXT NOT NULL, explanation TEXT NOT NULL,
  skill_score REAL NOT NULL, experience_score REAL NOT NULL, compensation_score REAL NOT NULL,
  flexibility_score REAL NOT NULL, remote_score REAL NOT NULL, effort_score REAL NOT NULL,
  hard_requirement_passed INTEGER NOT NULL, evaluated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_configurations (
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, keywords TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'Remotive',
  enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_executions (
  id INTEGER PRIMARY KEY, source TEXT NOT NULL, started_at TEXT NOT NULL, completed_at TEXT,
  status TEXT NOT NULL, found_count INTEGER NOT NULL DEFAULT 0, new_count INTEGER NOT NULL DEFAULT 0,
  duplicate_count INTEGER NOT NULL DEFAULT 0, error_message TEXT, duration_ms INTEGER
);
CREATE TABLE IF NOT EXISTS activity_logs (
  id INTEGER PRIMARY KEY, event_type TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opportunity_status ON opportunities(status);
CREATE INDEX IF NOT EXISTS idx_opportunity_discovered ON opportunities(discovered_at DESC);
CREATE INDEX IF NOT EXISTS idx_match_score ON opportunity_matches(score DESC);
"""


PLATFORMS = [
    ("Remotive", "https://remotive.com", "Remote technology jobs", "High", "Official public API", "Automated", "Listings are delayed; attribution and source links are required."),
    ("Mercor", "https://mercor.com", "AI expert contracting", "High", "Manual/browser-assisted", "Manual only", "No supported public discovery API configured."),
    ("Outlier AI", "https://outlier.ai", "AI model training and evaluation", "High", "Manual/browser-assisted", "Manual only", "Account-gated opportunities."),
    ("DataAnnotation", "https://dataannotation.tech", "AI evaluation and coding", "High", "Manual/browser-assisted", "Manual only", "Account-gated opportunities."),
    ("Alignerr", "https://alignerr.com", "AI expert evaluation", "High", "Manual/browser-assisted", "Manual only", "No supported public API configured."),
    ("Turing", "https://www.turing.com", "Remote software development / AI", "High", "Manual/browser-assisted", "Manual only", "No supported public API configured."),
    ("Upwork", "https://www.upwork.com", "Freelance IT projects", "High", "Manual/browser-assisted", "Manual only", "Automated collection requires approved API access."),
    ("Direct healthcare consulting", "https://www.linkedin.com", "Healthcare IT consulting", "High", "Manual entry", "Manual only", "Use employer or consulting-network source URL."),
    ("Braintrust", "https://www.usebraintrust.com", "Technical consulting", "Medium", "Manual/browser-assisted", "Manual only", "No supported public API configured."),
    ("Contra", "https://contra.com", "Independent freelance projects", "Medium", "Manual/browser-assisted", "Manual only", "No supported public API configured."),
    ("Freelancer", "https://www.freelancer.com", "Project assignments", "Medium", "Manual/browser-assisted", "Manual only", "No supported public API configured."),
    ("LinkedIn", "https://www.linkedin.com/jobs", "Remote IT contract opportunities", "Medium", "Manual/browser-assisted", "Manual only", "Automated scraping is not used."),
    ("Wellfound", "https://wellfound.com/jobs", "Startup technology opportunities", "Medium", "Manual/browser-assisted", "Manual only", "No supported public API configured."),
]


class Database:
    def __init__(self, path):
        self.path = str(path)

    @contextmanager
    def connect(self):
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        now = utcnow()
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.execute("INSERT OR IGNORE INTO user_profile(id, created_at, updated_at) VALUES(1, ?, ?)", (now, now))
            for row in PLATFORMS:
                conn.execute("""INSERT OR IGNORE INTO platforms
                  (name, official_url, category, priority, access_method, automation_status, notes, created_at, updated_at)
                  VALUES(?,?,?,?,?,?,?,?,?)""", (*row, now, now))
            conn.execute("""INSERT OR IGNORE INTO search_configurations
              (name,keywords,source,created_at,updated_at) VALUES(?,?,?,?,?)""",
              ("AI, software, and healthcare IT", "AI,LLM,Python,NLP,SQL,.NET,ETL,automation,healthcare,data", "Remotive", now, now))

    def all(self, query, params=()):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def one(self, query, params=()):
        with self.connect() as conn:
            row = conn.execute(query, params).fetchone()
            return dict(row) if row else None

    def execute(self, query, params=()):
        with self.connect() as conn:
            cur = conn.execute(query, params)
            return cur.lastrowid

