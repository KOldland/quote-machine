#!/bin/bash
set -e
cd "$(dirname "$0")/.."
echo "Backing up current DB to template_store.sqlite3.bak ..."
cp template_store.sqlite3 template_store.sqlite3.bak
echo "Restoring clean state from db_snapshots/builder_beta_clean_2026-08-20.sql ..."
sqlite3 template_store.sqlite3 < db_snapshots/builder_beta_clean_2026-08-20.sql
echo "Restore complete. Original DB backed up to template_store.sqlite3.bak"
