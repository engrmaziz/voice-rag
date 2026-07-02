#!/bin/bash
# entrypoint.sh

# 1. Run migrations
python manage.py migrate --noinput

# 2. Automatically create superuser using the Secrets we just added
if [ "$DJANGO_SUPERUSER_USERNAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput --username "$DJANGO_SUPERUSER_USERNAME" --email "$DJANGO_SUPERUSER_EMAIL"
    echo "Superuser created."
else
    echo "No superuser credentials found in secrets. Skipping creation."
fi

# 3. Start the server
exec daphne -b 0.0.0.0 -p 7860 core.asgi:application
