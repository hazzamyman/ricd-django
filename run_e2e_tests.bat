@echo off
start "Django Server" cmd /c "python manage.py runserver"
timeout /t 3 /nobreak >nul
python -m pytest tests/test_e2e_home.py -v