# Procfile for Heroku deployment
release: test -n "$JWT_SECRET" || (echo "JWT_SECRET environment variable not set" && exit 1)
web: python production_backend.py
