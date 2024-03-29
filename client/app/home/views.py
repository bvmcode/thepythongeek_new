"""Home."""
from flask import Blueprint, render_template

home_bp = Blueprint("home", __name__)


@home_bp.route("/")
def home():
    """Home view."""
    return render_template(
        "home.html", title="\\\\barry_v_martin\\\\", title_img="me.jpg"
    )
