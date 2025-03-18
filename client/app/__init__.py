import os

from flask import Flask, render_template
from flask_caching import Cache
from flask_cors import CORS
from redis import Redis

redis = Redis(host="redis", port=6379)
cache = Cache()


def create_app():
    """Create application."""
    app = Flask(__name__, static_url_path="/static")
    app_settings = os.getenv("APP_SETTINGS")
    app.config.from_object(app_settings)
    CORS(app)
    cache.init_app(app)

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

    @project_bp.after_request
    def add_no_cache_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    
    return app
