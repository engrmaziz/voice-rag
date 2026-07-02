#!/bin/bash
# 1. Run migrations to create tables in the /data bucket
python manage.py migrate --noinput

# 2. Start the application
exec daphne -b 0.0.0.0 -p 7860 core.asgi:application