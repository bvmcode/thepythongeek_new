import os

from flask import Flask, render_template
# from flask_caching import Cache
from flask_cors import CORS
from redis import Redis

redis = Redis(host="redis", port=6379)
# cache = Cache()


def create_app():
    """Create application."""
    app = Flask(__name__, static_url_path="/static")
    app_settings = os.getenv("APP_SETTINGS")
    app.config.from_object(app_settings)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    CORS(app)
    # cache.init_app(app)

    from app.home.views import home_bp
    from app.project.views import project_bp
    from app.resume.views import resume_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(project_bp)
    app.register_blueprint(resume_bp)

    @app.errorhandler(404)
    def page_not_found(e):
        return (
            render_template(
                "404.html", title="\\\\404 Not Found\\\\", title_img="404.png"
            ),
            404,
        )
    
    return app
