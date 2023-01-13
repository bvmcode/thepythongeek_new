from flask import Blueprint, render_template

resume_bp = Blueprint("resume", __name__, url_prefix="/resume")


@resume_bp.route("/")
def resume():
    return render_template(
        "resume.html", title="\\\\resume\\\\", title_img="resume.jpg"
    )
