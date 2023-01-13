import json
import os
import re
from datetime import datetime

import boto3
import requests
import tweepy

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
ARTISTS = [
    "Dream Theater",
    "Queensryche",
    "Vola",
    "Katatonia",
    "Saint Asonia",
    "Josh Garrels",
    "Gunship",
    "Helloween",
    "Light The Torch",
    "Rend Collective",
]


def get_spotify_headers():
    AUTH_URL = "https://accounts.spotify.com/api/token"
    auth_response = requests.post(
        AUTH_URL,
        {
            "grant_type": "client_credentials",
            "client_id": SPOTIFY_CLIENT_ID,
            "client_secret": SPOTIFY_CLIENT_SECRET,
        },
    )
    auth_response_data = auth_response.json()
    access_token = auth_response_data["access_token"]
    return {"Authorization": "Bearer {token}".format(token=access_token)}


def get_twitter_id_from_spotify(url):
    headers = get_spotify_headers()
    r = requests.get(url, headers=headers)
    text = r.content.decode("utf-8")
    match = re.search(r'href="https://twitter.com/([A-Za-z0-9_]+)"', text)
    try:
        return match.group(1)
    except AttributeError:
        return None


def get_spotify_artist(name):
    url = (
        f"https://api.spotify.com/v1/search?q={name}&type=artist&include_external=audio"
    )
    headers = get_spotify_headers()
    response = requests.get(url, headers=headers)
    data = response.json()
    for artist in data["artists"]["items"]:
        if name.lower() == artist["name"].lower():
            return artist
    return data["artists"]["items"][0]


def get_spotify_artist_link(artist):
    return artist["external_urls"]["spotify"]


def get_spotify_follower_count(artist):
    return artist["followers"]["total"]


def get_twitter_follower_count(twitter_id):
    auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
    auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    user = api.get_user(screen_name=twitter_id)
    return user.followers_count


def write_to_s3(data):
    filename = f"{datetime.now().strftime('%Y%m%d')}.json"
    s3 = boto3.resource("s3")
    s3object = s3.Object("artist-followers", filename)
    data_json = json.dumps(data, indent=2)
    s3object.put(Body=(bytes(data_json.encode("UTF-8"))))


def lambda_handler(event, context):
    data = {}
    for artist in ARTISTS:
        spotify_artist = get_spotify_artist(artist)
        spotify_link = get_spotify_artist_link(spotify_artist)
        spotify_follower_count = get_spotify_follower_count(spotify_artist)
        twitter_id = get_twitter_id_from_spotify(spotify_link)
        twitter_follower_count = get_twitter_follower_count(twitter_id)
        data[artist] = {
            "spotify": spotify_follower_count,
            "twitter": twitter_follower_count,
        }
    write_to_s3(data)
