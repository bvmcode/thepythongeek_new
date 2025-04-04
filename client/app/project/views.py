import json
import math
import os
from datetime import datetime, timedelta
import pytz
import time

import boto3
# from app import cache
from botocore.exceptions import ClientError
from flask import Blueprint, render_template, make_response, jsonify
from flask_restx import Api, Resource
import psycopg2 as pg2
import pandas as pd
import plotly
import plotly.express as px
import s3fs

project_bp = Blueprint("project", __name__, url_prefix="/project")
api = Api(project_bp)


# def get_data(date):
#     s3 = boto3.resource("s3")
#     try:
#         content_object = s3.Object("artist-followers", f"{date}.json")
#         file_content = content_object.get()["Body"].read().decode("utf-8")
#         return json.loads(file_content)
#     except ClientError:
#         return None


# @project_bp.route("/")
# def project():
#     return render_template(
#         "project.html", title="\\\\sample_project\\\\", title_img="project.png"
#     )

# @project_bp.route("/music")
# def project2():
#     return render_template(
#         "project2.html", title="\\\\sample_project\\\\", title_img="project2.jpg"
#     )


# @api.route("/api/artists/<artist>/weekly")
# class ArtistApi(Resource):
#     @cache.cached(timeout=1000, query_string=True)
#     def get(self, artist):
#         # hard code due to twitter API now chargin
#         start = datetime(2023, 1, 1)
#         end = datetime(2023, 1, 7)
#         data = {}
#         while start <= end:
#             date = start.strftime("%Y%m%d")
#             json_data = get_data(date)
#             if json_data:
#                 data[date] = json_data[artist]
#             start = start + timedelta(days=1)
#         return data

    
class Database:
  def __init__(self):
    self.host = os.getenv("DB_HOST")
    self.db = os.getenv("DB_NAME")
    self.username = os.getenv("DB_USER")
    self.password = os.getenv("DB_PASS")
    self.port = os.getenv("DB_PORT")
    self.cur = None
    self.conn = None

  def get_data(self):
    engine = pg2.connect(f"dbname='{self.db}' user='{self.username}' host='{self.host}' port='{self.port}' password='{self.password}'")
    query = """
            SELECT *
            FROM public.weather
            order by api_datetime desc
            limit 156
            """
    df = pd.read_sql(query, con=engine)
    df["api_datetime"] = df["api_datetime"].dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
    engine.close()
    return df
  
  def get_current_max_temp(self, date):
    engine = pg2.connect(f"dbname='{self.db}' user='{self.username}' host='{self.host}' port='{self.port}' password='{self.password}'")
    query = f"""
            SELECT api_datetime, temp_f
            FROM public.weather
            order by api_datetime desc
            limit 500
            """
    df = pd.read_sql(query, con=engine)
    df["date"] = df["api_datetime"].dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
    engine.close()
    df = df[df['date'].dt.date == date]
    return df.temp_f.max()
  
  def get_latest_temp(self):
    engine = pg2.connect(f"dbname='{self.db}' user='{self.username}' host='{self.host}' port='{self.port}' password='{self.password}'")
    query = """
            SELECT temp_f
            FROM public.weather
            order by api_datetime desc
            limit 1
            """
    df = pd.read_sql(query, con=engine)
    engine.close()
    return df.temp_f.values[0]


def get_wind_direction_string(degrees):
    val = int((degrees/22.5)+.5)
    arr = ["N","NNE","NE","ENE","E","ESE", "SE", "SSE","S","SSW","SW","WSW","W","WNW","NW","NNW"]
    return arr[(val % 16)]

def get_plot(df, field, unit):
    if field == "temperature":
        y = f'temp_{unit}'
    if field == "dew point":
        y = f'dew_point_{unit}'
    if field == "wind":
        y = f'wind_speed_{unit}'
    if field == "pressure":
        y = f'barometric_pressure_{unit}'
    if field == "hourly rain":
        y = f'hourly_rain_{unit}'
    title = f"{field.upper()} {unit.upper()}"
    fig = px.line(df, x='api_datetime', y=y, title=title)
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

def get_current_weather(df):
    df = df.head(1)
    wind_dir = get_wind_direction_string(df.wind_dir.values[0])
    return {
        "Timestamp": df.api_datetime.dt.strftime('%Y-%m-%d %I:%M %p EST').values[0],
        "Temperature": {"F": math.ceil(df.temp_f.values[0]), "C": math.ceil(df.temp_c.values[0])},
        "Dew Point": {"F": math.ceil(df.dew_point_f.values[0]), "C": math.ceil(df.dew_point_c.values[0])},
        "Humidity": math.ceil(df.humidity.values[0]),
        "Pressure": {"in": round(df.barometric_pressure_in.values[0],1), "mb": round(df.barometric_pressure_mb.values[0],1)},
        "Wind Speed": {"mph": round(df.wind_speed_mph.values[0],1), "kt": round(df.wind_speed_kt.values[0],1)},
        "Hourly Rain": {"in": round(df.hourly_rain_in.values[0],1), "cm": round(df.hourly_rain_cm.values[0],1)},
        "Wind Direction": wind_dir
    }

@project_bp.route("/wx")
def project3():
    db = Database()
    df = db.get_data()
    temp_f_fig = get_plot(df, 'temperature', 'f')
    temp_c_fig = get_plot(df, 'temperature', 'c')
    wind_mph_fig = get_plot(df, 'wind', 'mph')
    wind_kt_fig = get_plot(df, 'wind', 'kt')
    pressure_in_fig = get_plot(df, 'pressure', 'in')
    pressure_mb_fig = get_plot(df, 'pressure', 'mb')
    dew_point_f_fig = get_plot(df, 'dew point', 'f')
    dew_point_c_fig = get_plot(df, 'dew point', 'c')
    hourly_rain_in_fig = get_plot(df, 'hourly rain', 'in')
    hourly_rain_cm_fig = get_plot(df, 'hourly rain', 'cm')

    current_wx = get_current_weather(df)
    return render_template(
        "project3.html", title="\\\\Weather Station\\\\", title_img="weather.jpg",
        current_wx=current_wx,
        temp_f_fig=temp_f_fig,
        temp_c_fig=temp_c_fig,
        wind_mph_fig=wind_mph_fig,
        wind_kt_fig=wind_kt_fig,
        pressure_in_fig=pressure_in_fig,
        pressure_mb_fig=pressure_mb_fig,
        dew_point_f_fig=dew_point_f_fig,
        dew_point_c_fig=dew_point_c_fig,
        hourly_rain_in_fig=hourly_rain_in_fig,
        hourly_rain_cm_fig=hourly_rain_cm_fig
    )


def get_value(date, value_type):
    if value_type == 'prediction':
        key = f"{date.year}/{date.month}/{date.day}/prediction.txt"
    if value_type == 'actual':
        key = f"{date.year}/{date.month}/{date.day}/max_temp.txt"
    s3 = boto3.client('s3')
    try:
        obj = s3.get_object(Bucket="weather-bvmcode", Key=key)
    except ClientError:
        return None
    return round(float(obj['Body'].read().decode('utf-8')),1)


def date_range():
    utc_date = datetime.utcnow().replace(tzinfo=pytz.utc)
    dt_now = utc_date.astimezone(pytz.timezone('US/Eastern')).date()
    dt_14 = dt_now + timedelta(days=-15)
    dates = [dt_14]
    while True:
        if dt_14 >= dt_now:
            break
        else:
            dt_14 = dt_14 + timedelta(days=1)
            dates.append(dt_14)
    return dates


@api.route("/api/predictions")
class PredictionApi(Resource):
    # @cache.cached(timeout=1000, query_string=True)
    def get(self):
        dates = date_range()
        predictions = []
        actuals = []
        dates_updated = []
        for date in dates:
            pred = get_value(date, 'prediction')
            actual = get_value(date, 'actual')
            if pred is not None and actual is not None:
                dates_updated.append(date.strftime("%Y-%m-%d"))
                predictions.append(pred)
                actuals.append(actual)
        data = {
            "dates": dates_updated,
            "predictions": predictions,
            "actuals": actuals
        }
        return data


@project_bp.route("/predict")
def project4():
    utc_date = datetime.utcnow().replace(tzinfo=pytz.utc)
    dt_time = utc_date.astimezone(pytz.timezone('US/Eastern'))
    dt = dt_time.date()
    dt_prev = dt + timedelta(days=-1)
    prediction = get_value(dt, 'prediction')
    prediction_prev_day = get_value(dt_prev, 'prediction')
    actual_prev_day = get_value(dt_prev, 'actual')
    db = Database()
    current_temp = db.get_latest_temp()
    current_temp_max = db.get_current_max_temp(dt)

    message_prev_day = None
    difference = None
    last_updated_prev_day = datetime(dt.year, dt.month, dt.day, 0, 0, 0).strftime('%Y-%m-%d %I:%M %p EST')
    if prediction_prev_day is None or actual_prev_day is None:
        message_prev_day = "Yesterday's data is not available till after 9 AM EST."
        if (dt_time.hour == 9 and dt_time.minute>=15) or (dt_time.hour>9):
            message_prev_day = "Yesterday's data is not available due to missing data."
    else:
        difference = round(abs(prediction_prev_day - actual_prev_day),1)
   

    message = None
    last_updated = datetime(dt.year, dt.month, dt.day, 9, 0, 0).strftime('%Y-%m-%d %I:%M %p EST')
    if prediction is None:
        message = "Today's prediction is not available till after 9 AM EST."
        if (dt_time.hour == 9 and dt_time.minute>=15) or (dt_time.hour>9):
            message = "Today's prediction is not available due to missing data."
    return render_template(
        "project4.html", title="\\\\Max Temperature AI Prediction\\\\",
        title_img="weather.png",
        prediction=prediction,
        prediction_prev_day=prediction_prev_day,
        actual_prev_day=actual_prev_day,
        difference=difference,
        current_temperature=current_temp,
        last_updated=last_updated,
        last_updated_prev_day=last_updated_prev_day,
        message_prev_day=message_prev_day,
        current_temp_max=current_temp_max,
        message=message,
        today = dt.strftime("%m/%d/%Y"),
        prev_day = dt_prev.strftime("%m/%d/%Y")
    )


def get_latest_run(bucket):
    s3 = s3fs.S3FileSystem()
    path = f"{bucket}/gfs_images"
    latest_date = max([int(f.split("/")[2]) for f in s3.ls(path, refresh=True)])
    latest_run = max([int(f.split("/")[3]) for f in s3.ls(f"{path}/{latest_date}", refresh=True)])
    return latest_date, str(latest_run).zfill(2)


@project_bp.route("/api/models_latest_run")
def models_latest_run():
    bucket = os.getenv("MODELS_BUCKET")
    latest_date, latest_run = get_latest_run(bucket)

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    response = make_response(jsonify({
        "latest_date": latest_date,
        "latest_run": latest_run,
        "timestamp": timestamp
    }))
    print(latest_date, latest_run, flush=True)
    # Prevent browser caching
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0, s-maxage=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["CF-Cache-Status"] = "DYNAMIC"
    
    return response


@project_bp.route("/wx-models")
def project5():
    bucket = os.getenv("MODELS_BUCKET")
    hours = [f"{i:03d}" for i in range(0, 121, 6)]
    return render_template(
        "project5.html", title="\\\\GFS Weather Models\\\\", title_img="gfs.png",
        bucket=bucket, hours=hours)
