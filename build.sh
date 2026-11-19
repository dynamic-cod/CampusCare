#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Collect static files with WhiteNoise
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Seed campus infrastructure, sub-admins, and demo complaints
python manage.py setup_amu_campus
python manage.py seed_subadmins
python seed_237_realistic_complaints.py
