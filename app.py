import json
import requests
from analysis import analyze_spotify
from urllib.parse import quote
from flask import Flask, request, redirect, render_template, url_for

app = Flask(__name__)

client_id = "69707b9e5dbd449c827fa51833cb8d0a"
secret_id = "e4dfa6dc0c844256b57b3c2bc73176ea"
redirect_uri = "https://polyvibe.herokuapp.com/callback"
scope = "user-top-read playlist-read-private playlist-read-collaborative user-library-read"

data = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/authorization")
def authorize():
    auth_params = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "show_dialog": "true",
        "client_id": client_id
    }
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_params.items()])
    auth_url = "{}/?{}".format("https://accounts.spotify.com/authorize", url_args)
    return redirect(auth_url)

@app.route("/callback")
def getInfo():
    try:
        global data
        code = request.args['code']
        post_data = {
            "grant_type": "authorization_code",
            "code": str(code),
            "redirect_uri": redirect_uri,
            'client_id': client_id,
            'client_secret': secret_id,
        }
        response = requests.post("https://accounts.spotify.com/api/token", data=post_data)
        data["access_token"] = json.loads(response.text)["access_token"]
        return render_template("loading.html")
    except:
        return render_template("error.html")

@app.route("/loading")
def loading():
    try:
        global data
        data["plots"] = analyze_spotify(data["access_token"])
    except Exception as error:
        print(type(error))
        print(error.args)
        print(error)
        return render_template("error.html")
    return redirect(url_for("display"))

@app.route("/display")
def display():
    return render_template("analysis.html", info=data["plots"])

def run_app():
    app.run(debug=True, use_reloader=True)