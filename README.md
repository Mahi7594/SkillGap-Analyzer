# Skill Gap Analyzer

Django app for tracking role skill benchmarks against employee skill levels and
reporting the gap between them.

## Setup

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# local dev only: enables Django's debug pages
$env:DJANGO_DEBUG = "True"

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

`DJANGO_DEBUG` defaults to `False`. In production, also set `DJANGO_SECRET_KEY` and
`DJANGO_ALLOWED_HOSTS` (comma-separated) as environment variables — the app refuses to start
with `DEBUG=False` and no `DJANGO_SECRET_KEY` set.

## Access model

Every page requires login.

- **Staff** (`is_staff=True`, e.g. anyone created via `createsuperuser`) — full access:
  create/edit/delete employees, skills, roles, and benchmarks; bulk skill updates; inline
  skill-level edits.
- **Any other logged-in user** — read-only: dashboard, employee list/profile/card, skill search.
