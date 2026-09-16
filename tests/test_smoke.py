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
    assert b'code-nova-pages-v1' in response.data

    manifest = client.get('/static/manifest.webmanifest')
    assert manifest.status_code == 200
    assert b'CODE-NOVA CMS' in manifest.data


def test_secure_cookie_setting_is_environment_driven(monkeypatch):
    monkeypatch.setenv('SESSION_COOKIE_SECURE', '0')
    app = create_app()
    assert app.config['SESSION_COOKIE_SECURE'] is False
