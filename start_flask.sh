#!/bin/bash
cd /Users/krisoldland/Documents/QM_web_app/app
export QM_TEST_MODE=0
export QM_DISABLE_SHEETS=1
export QM_CATALOG_SOURCE=db
export PORT=5003
export FLASK_DEBUG=0
export QM_ADMIN_PASSWORD=admin123
exec python3 QMapp.py
