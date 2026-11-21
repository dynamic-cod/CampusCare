#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Collect static files with WhiteNoise
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Create superadmin user (idempotent - skips if already exists)
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@campuscare.amu.ac.in', 'CampusAdmin@2026')
    print('Superuser admin created.')
else:
    u = User.objects.get(username='admin')
    u.set_password('CampusAdmin@2026')
    u.is_superuser = True
    u.is_staff = True
    u.is_active = True
    u.save()
    print('Superuser admin password reset.')
"

# Seed campus infrastructure, sub-admins, and demo complaints
python manage.py setup_amu_campus
python manage.py seed_subadmins
python manage.py seed_emergency_dept
python seed_237_realistic_complaints.py
