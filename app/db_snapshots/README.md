# DB Snapshots

This folder contains point-in-time SQL dumps of `template_store.sqlite3`.

## Snapshots

- `builder_beta_clean_2026-08-20.sql` — clean state after fixing versioning bugs, before pruning old versions (2.2 MB)
- `builder_beta_pruned_2026-08-20.sql` — current live state with old template versions removed (894 KB)

## Restore

To restore the **pruned** (current) state:

```bash
cd /path/to/QM_web_app/app
./db_snapshots/restore_pruned_state.sh
```

To restore the **clean pre-prune** state:

```bash
cd /path/to/QM_web_app/app
./db_snapshots/restore_clean_state.sh
```

Both scripts back up the live DB to `template_store.sqlite3.bak` before restoring.

**Note:** Restoring will overwrite all current data. Make sure you have a backup.
