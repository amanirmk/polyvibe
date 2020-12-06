import json
import requests
from analysis import analyze_spotify
from urllib.parse import quote
from flask import Flask, request, redirect, render_template, url_for, session

app = Flask(__name__)
app.secret_key = "doesn't really matter"

client_id = "69707b9e5dbd449c827fa51833cb8d0a"
secret_id = "e4dfa6dc0c844256b57b3c2bc73176ea"
redirect_uri = "http://localhost:8888/callback" #change later
scope = "user-top-read playlist-read-private playlist-read-collaborative user-library-read"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/authorization")
def authorize():
    auth_params = {
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": scope,
        "show_dialog": "false",
        "client_id": client_id
    }
    url_args = "&".join(["{}={}".format(key, quote(val)) for key, val in auth_params.items()])
    auth_url = "{}/?{}".format("https://accounts.spotify.com/authorize", url_args)
    return redirect(auth_url)

@app.route("/callback")
def getInfo():
    try:
        code = request.args['code']
        post_data = {
            "grant_type": "authorization_code",
            "code": str(code),
            "redirect_uri": redirect_uri,
            'client_id': client_id,
            'client_secret': secret_id,
        }
        response = requests.post("https://accounts.spotify.com/api/token", data=post_data)
        response_data = json.loads(response.text)
        session["access_token"] = response_data["access_token"]
        return render_template("loading.html")
    except:
        return render_template("error.html")

@app.route("/loading")
def loading():
    session["data"] = analyze_spotify(session["access_token"])
    return redirect(url_for("display"))

@app.route("/display")
def display():
    return render_template("analysis.html")

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8888, debug=True)