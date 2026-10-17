# IncomeGen

IncomeGen is a private, mobile-friendly opportunity discovery workspace for an experienced AI, software development, database, and healthcare IT professional.

Live app: https://derickglanville.github.io/IncomeGen/

## Architecture

- Static HTML, CSS, and JavaScript hosted by GitHub Pages.
- Google sign-in restricted to `dglanville@gmail.com`.
- Firebase Firestore REST storage in the isolated `incomegen/workspace` document.
- Responsive iPhone layout with safe-area spacing and an installable web-app manifest.
- No Flask server, SQLite database, administrative API keys, or stored passwords.

The Firebase web API key in `docs/app.js` identifies the existing `glanville-issue-tracker` project; it is not an administrative credential. Authentication and Firestore Security Rules enforce access. IncomeGen does not read or modify Solar, Food Tracking, or Theodore collections.

## Features

- Cloud-synchronized professional profile and income preferences.
- 25 dated, official-source Mercor and Outlier recommendations.
- Search and filtering by platform and profile-fit score.
- Personal opportunity pipeline with add, edit, delete, status, compensation, source, and notes.
- Registry of 13 platforms with honest automation limitations.
- Firestore concurrency protection to avoid silently overwriting another device.
- Mobile bottom navigation and Add to Home Screen support on iPhone.

Recommended jobs are a dated shortlist, not guaranteed openings. Confirm availability, eligibility, compensation, and assessment rules on the linked provider page.

## Firestore rules

Merge `firestore.rules.fragment` inside the existing `match /databases/{database}/documents` block and publish it without replacing existing rules. It permits only the authorized verified Google account to use the single IncomeGen workspace document.

## Local preview

```powershell
python -m http.server 5051 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:5051`. Firebase Authentication must list `localhost` as an authorized domain for local sign-in.

## iPhone

Open the live URL in Safari and sign in with the authorized Google account. Use Safari Share → **Add to Home Screen** for an app-like shortcut. The app talks directly to Firebase, so the Windows computer does not need to stay on.

## Verification

```powershell
node --check docs/app.js
node tests/static.test.mjs
```

