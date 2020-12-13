import json
import requests
from analysis import *
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
    global data
    data = {} #restart
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
        return render_template("loading.html", action="/loading1", msg="Collecting your top songs...")
    except:
        return render_template("error.html")

# i split analysis into several 
# sections as to avoid response 
# timeout. each acts as a loop 
# and will call itself until 
# it is entirely complete
@app.route("/loading1")
def loading1():
    global data
    try:
        data["plot_data"] = {}
        data["method_data"] = {"auth_header" : {"Authorization" : "Bearer " + data["access_token"]}}
        collect_top(data["method_data"], data["plot_data"])
    except Exception as error:
        print(type(error))
        print(error.args)
        print(error)
        return render_template("error.html")
    return render_template("loading.html", action="/loading2", msg="Collecting your saved tracks...")

@app.route("/loading2")
def loading2():
    global data
    try:
        collect_library(data["method_data"])
        if data["method_data"]["collected_library"]:
            return render_template("loading.html", action="/loading3", msg="Collecting your playlists...")
        else:
            return redirect(url_for("loading2"))
    except Exception as error:
        print(type(error))
        print(error.args)
        print(error)
        return render_template("error.html")

@app.route("/loading3")
def loading3():
    global data
    try:
        collect_playlists(data["method_data"])
        if data["method_data"]["collected_playlists"] and data["method_data"]["collected_tracks"]:
            return render_template("loading.html", action="/loading4", msg="Analyzing your artists and genres...")
        else:
            return redirect(url_for("loading3"))
    except Exception as error:
        print(type(error))
        print(error.args)
        print(error)
        return render_template("error.html")

@app.route("/loading4")
def loading4():
    global data
    try:
        top_artists(data["method_data"], data["plot_data"])
        top_genres(data["method_data"], data["plot_data"])
        artist_diversity(data["method_data"], data["plot_data"])
        genre_diversity(data["method_data"], data["plot_data"])
    except Exception as error:
        print(type(error))
        print(error.args)
        print(error)
        return render_template("error.html")
    return render_template("loading.html", action="/loading5", msg="Analyzing your tracks...")

@app.route("/loading5")
def loading5():
    global data
    try:
        features(data["method_data"], data["plot_data"])
        recommendations(data["method_data"], data["plot_data"])
    except Exception as error:
        print(type(error))
        print(error.args)
        print(error)
        return render_template("error.html")
    return redirect(url_for("display"))

@app.route("/display")
def display():
    if data["method_data"]["incomplete_data_status"]:
        data["plot_data"]["incomplete_data_msg"] = "Note: We encountered issues when collecting your data. The quality of this report may have been impacted."
    else:
        data["plot_data"]["incomplete_data_msg"] = ""
    return render_template("analysis.html", info=data["plot_data"])

if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)