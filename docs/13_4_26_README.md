# Quote Machine Web App

Flask-based internal quote generation app with Google Sheets-driven line-item logic and Google Docs production output.

## Current Source Of Truth

- Main app: `app/QMapp.py`
- Templates: `app/templates/`
- Static assets: `app/static/`
- Production script: `app/scripts/QM_Production.py`

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r app/requirements.txt
```

3. Configure environment variables (copy from `.env.example`).
4. Start the app from the app directory:

```bash
cd app
python3 QMapp.py
```

For production-style startup:

```bash
cd app
gunicorn QMapp:app
```

## Smoke Check

After starting the app, run the route smoke check:

```bash
python3 app/scripts/smoke_routes.py --base-url http://127.0.0.1:5001
```

Run submit-to-production smoke validation:

```bash
python3 app/scripts/smoke_submit.py --base-url http://127.0.0.1:5001
```

## Required Environment Variables

- `QM_SECRET_KEY`: Flask secret key for sessions/CSRF.
- `QM_CREDENTIALS_PATH`: Absolute or relative path to Google service account JSON.
- `QM_SPREADSHEET_ID`: Target Google Sheet ID for quote data.
- `FLASK_DEBUG`: Optional. Set to `1`, `true`, `yes`, or `on` for debug mode.
- `PORT`: Optional local app port (default `5000`). Use `5001` on macOS where port `5000` may be occupied.
- `QM_TEST_MODE`: Optional. Set to `1` for local smoke tests without live Google credentials.

## Credential Rotation Workflow

1. Revoke and rotate the old Google service account key in Google Cloud IAM.
2. Create a new key and store it outside version control.
3. Update `QM_CREDENTIALS_PATH` in your environment to the new key path.
4. Confirm `app/QM_credentials.json` is not present and remains ignored.
5. Run route and submit smoke checks before deployment.

## Primary User Flow

1. Project details
2. Special notes
3. Summary and scope pages
4. Image upload/template selection
5. Review
6. Submit data
7. Trigger production document generation

## Notes

- Session files are filesystem-backed and should not be committed.
- Uploaded/generated files under `app/static/uploads/` should not be committed.
- Legacy folders in the repository are archival and not used by the active app runtime.
