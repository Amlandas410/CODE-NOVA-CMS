import os

from app import create_app


def test_app_starts():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()
    response = client.get('/login')
    assert response.status_code == 200
    assert b'Welcome back' in response.data


def test_deployment_configuration_is_environment_driven(monkeypatch):
    monkeypatch.setenv('FLASK_DEBUG', '0')
    monkeypatch.setenv('HOST', '0.0.0.0')
    monkeypatch.setenv('PORT', '8080')
    monkeypatch.setenv('MYSQL_HOST', 'db.internal')
    monkeypatch.setenv('MYSQL_PORT', '3307')
    monkeypatch.setenv('MYSQL_DATABASE', 'code_nova_cms_prod')
    monkeypatch.setenv('MYSQL_USER', 'app_user')
    monkeypatch.setenv('MYSQL_PASSWORD', 'secret')

    app = create_app()

    assert app.config['DEBUG'] is False
    assert app.config['HOST'] == '0.0.0.0'
    assert app.config['PORT'] == 8080
    assert app.config['MYSQL_HOST'] == 'db.internal'
    assert app.config['MYSQL_PORT'] == 3307


def test_offline_assets_are_available():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    response = client.get('/service-worker.js')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-cache, max-age=0, must-revalidate'
    assert b'code-nova-pages-v1' in response.data
    assert b'code-nova-shell-v2' in response.data
    assert b'async function staticAssetRequest' in response.data

    manifest = client.get('/static/manifest.webmanifest')
    assert manifest.status_code == 200
    assert manifest.cache_control.max_age == 0
    assert b'CODE-NOVA CMS' in manifest.data


def test_secure_cookie_setting_is_environment_driven(monkeypatch):
    monkeypatch.setenv('SESSION_COOKIE_SECURE', '0')
    app = create_app()
    assert app.config['SESSION_COOKIE_SECURE'] is False


def test_admin_request_and_complaint_pages_render_without_database(monkeypatch):
    import app.admin as admin_module

    def fake_query(sql, params=(), one=False, dictionary=True):
        return {'id': 1} if one else []

    monkeypatch.setattr(admin_module, 'query', fake_query)
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    with client.session_transaction() as session:
        session['role'] = 'admin'
        session['user_id'] = 1

    assert client.get('/admin/requests').status_code == 200
    assert client.get('/admin/complaints').status_code == 200


def test_student_dashboard_shows_assigned_room_and_assets(monkeypatch):
    import app.student as student_module
    from datetime import date

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 6)

    student = {
        'id': 1,
        'name': 'Test Student',
        'hostel': 'Boys Hostel A',
        'room_no': 'A-204',
        'batch': '2023-27',
        'branch': 'CSE',
        'year': 3,
    }
    room = [{
        'hostel': 'Boys Hostel A',
        'room_no': 'A-204',
        'floor': '2',
        'capacity': 3,
        'warden_name': 'Test Warden',
        'asset_name': 'Ceiling Fan',
        'asset_code': 'A204-01',
        'quantity': 1,
        'condition_status': 'good',
    }]

    def fake_query(sql, params=(), one=False, dictionary=True):
        if 'FROM users' in sql:
            return student
        if 'FROM rooms r LEFT JOIN assets' in sql:
            return room
        if 'COUNT(*) AS c' in sql:
            return {'c': 0}
        return None if one else []

    monkeypatch.setattr(student_module, 'query', fake_query)
    monkeypatch.setattr(student_module, 'date', FixedDate)
    monkeypatch.setattr(student_module, 'execute', lambda *args, **kwargs: None)
    monkeypatch.setattr(student_module, 'refresh_aging_complaints', lambda: None)
    monkeypatch.setattr(student_module, 'attendance_data', lambda student_id: ([], 0))

    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    with client.session_transaction() as session:
        session['role'] = 'student'
        session['user_id'] = student['id']

    response = client.get('/student/dashboard')

    assert response.status_code == 200
    assert b'TUESDAY' in response.data
    assert b'CAMPUS OVERVIEW' in response.data
    assert b'Room &amp; assets' in response.data
    assert b'Boys Hostel A' in response.data
    assert b'A-204' in response.data
    assert b'Ceiling Fan' in response.data
    assert b'A204-01' in response.data
