import json
from datetime import datetime, timedelta

import boto3
from app import cache
from botocore.exceptions import ClientError
from flask import Blueprint, render_template
from flask_restx import Api, Resource

project_bp = Blueprint("project", __name__, url_prefix="/project")
api = Api(project_bp)


def get_data(date):
    s3 = boto3.resource("s3")
    try:
        content_object = s3.Object("artist-followers", f"{date}.json")
        file_content = content_object.get()["Body"].read().decode("utf-8")
        return json.loads(file_content)
    except ClientError:
        return None


@project_bp.route("/")
def project():
    return render_template(
        "project.html", title="\\\\sample_project\\\\", title_img="project.jpg"
    )


@api.route("/api/artists/<artist>/weekly")
class ArtistApi(Resource):
    @cache.cached(timeout=1000, query_string=True)
    def get(self, artist):
        start = datetime.now() + timedelta(days=-7)
        end = datetime.now()
        data = {}
        while start <= end:
            date = start.strftime("%Y%m%d")
            json_data = get_data(date)
            if json_data:
                data[date] = json_data[artist]
            start = start + timedelta(days=1)
        return data
