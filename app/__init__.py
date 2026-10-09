import importlib

from flask import Flask
from dotenv import load_dotenv


def create_app():
    load_dotenv()
    import config as app_config
    importlib.reload(app_config)

    app = Flask(__name__)
    app.config.from_object(app_config.Config)

    from .db import init_app as init_db
    init_db(app)

    from .auth import bp as auth_bp
    from .student import bp as student_bp
    from .admin import bp as admin_bp
    from .teacher import bp as teacher_bp
    from .warden import bp as warden_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(teacher_bp)
    app.register_blueprint(warden_bp)

    @app.route("/service-worker.js")
    def service_worker():
        from flask import send_from_directory
        response = send_from_directory(
            app.static_folder, "service-worker.js", mimetype="application/javascript"
        )
        response.headers["Cache-Control"] = "no-cache, max-age=0, must-revalidate"
        return response

    @app.route("/")
    def index():
        from flask import redirect, url_for, session
        role=session.get('role')
        target={'student':'student.dashboard','admin':'admin.dashboard','teacher':'teacher.dashboard','warden':'warden.dashboard'}.get(role,'auth.login')
        return redirect(url_for(target))

    @app.context_processor
    def inject_globals():
        from .i18n import TRANSLATIONS
        return {"translations": TRANSLATIONS}

    return app
