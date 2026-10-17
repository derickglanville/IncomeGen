# IncomeGen

IncomeGen is a local, private opportunity-discovery and matching dashboard for flexible AI, software, and healthcare IT work. This repository implements the complete Phase 1 MVP from the supplied SRS.

The visual system and lightweight frontend follow the Theodore Glanville project's successful pattern: responsive navy/mint dashboard, card-based metrics, vanilla HTML/CSS/JavaScript, no frontend build step, and direct automated tests. IncomeGen uses Flask and relational SQLite storage rather than Theodore's Firebase document because this project requires source provenance, deduplication, search audit records, and future schema growth.

## Phase 1 features

- Persistent editable professional profile and income preferences.
- Extensible registry for all requested platforms, including honest automation limitations.
- Manual opportunity import with explicit source and unknown-value handling.
- Curated, dated recommendations for 25 currently listed Mercor and Outlier roles, linked to official sources.
- One real permitted integration: Remotive's official public API.
- SHA-256 deduplication using normalized company, title, and canonical application URL.
- Explainable 0–100 matching with the requested weights and geographic hard checks.
- Dashboard, filters, opportunity details, source provenance, platform registry, and search audit log.
- Dark/light theme, responsive layouts, accessible controls, and safe text rendering.
- SQLite database backups and critical unit/integration tests.

No sample or fabricated jobs are inserted. The database begins empty.

## Windows installation

1. Install Python 3.12 or newer from python.org and enable the Python launcher (`py`).
2. Open PowerShell in this folder.
3. Run `Set-ExecutionPolicy -Scope Process Bypass` if local scripts are blocked.
4. Run `./launch.ps1`.
5. Open `http://127.0.0.1:5051`.

Manual setup alternative:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

The database is created at `instance/incomegen.db`. Copy `.env.example` to `.env` only if you want custom values; environment variables can also be set directly in PowerShell. The app does not store account passwords.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Tests cover matching, hard geographic requirements, text sanitization, canonical fingerprints, dashboard startup, manual entry, persistence, scoring, and duplicate handling. Live API calls are intentionally excluded from repeatable tests.

## External-source limitations

- Remotive is accessed through its official public API. Its terms require attribution and links back to Remotive; IncomeGen preserves both. Public results may be delayed.
- Mercor, Outlier, DataAnnotation, Alignerr, Turing, Upwork, Braintrust, Contra, Freelancer, LinkedIn, Wellfound, and direct healthcare consulting are registered as manual or browser-assisted sources. IncomeGen does not scrape protected pages, bypass access controls, or claim those searches succeeded.
- Compensation from Remotive is retained as source-provided text when it cannot be safely normalized. Unknown numeric compensation remains unknown and receives a neutral score.
- Internet access and source availability are external dependencies. Failures appear in Search History.

## Remaining work

Phase 2: application, assessment, interview, and follow-up tracking. Phase 3: projects, timers, earnings, payments, goals, and exports. Phase 4: consent-based configurable LLM assistance. Phase 5: scheduled searches, notifications, automated reports, and recovery tooling. These are intentionally not implemented until Phase 1 is verified.

## Data and scoring definitions

Scores use technical skills 30%, professional experience 20%, compensation 20%, flexibility 15%, remote compatibility 10%, and application effort 5%. Unknown compensation is neutral. Explicit incompatible geography caps a listing at 35. Recommendations are algorithmic opinions and are labeled separately from verified listing facts.

