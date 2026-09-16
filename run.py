import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = app.config.get("HOST", "0.0.0.0")
    port = int(app.config.get("PORT", 8000))
    debug = app.config.get("DEBUG", False)

    if os.name == "nt":
        from waitress import serve
        serve(app, host=host, port=port)
    else:
        app.run(debug=debug, host=host, port=port)
