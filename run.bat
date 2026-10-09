@echo off
.\venv\Scripts\python -m waitress --listen=localhost:8000 wsgi:app
pause