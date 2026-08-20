# DB Snapshots

This folder contains point-in-time SQL dumps of `template_store.sqlite3`.

## Restore

To restore `builder_beta_clean_2026-08-20.sql` to the live DB:

```bash
cd /path/to/QM_web_app/app
cp template_store.sqlite3 template_store.sqlite3.bak   # backup first
sqlite3 template_store.sqlite3 < db_snapshots/builder_beta_clean_2026-08-20.sql
```

**Note:** Restoring will overwrite all current data. Make sure you have a backup.
