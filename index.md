## How to Make a Simple Spotify Web App Using Python, Flask, and Heroku

If you're both a programmer and a music enthusiast like me, odds are that you've considered making something with the Spotify API. If that sounds about right, then here's some help getting started. I'll be walking you through my process in creating my Spotify Web App, polyvibe. You can check it out [here](polyvibe.herokuapp.com)! It's not perfect, but if it seems along the lines of what you'd like to make — keep reading!

### Obtaining Spotify API credentials

In order to interact with the Spotify API, we're required to have some credentials. Thankfully, all we need is a Spotify account. Visit [the developer dashboard](https://developer.spotify.com/dashboard) and log in. On the [applications page](https://developer.spotify.com/dashboard/applications), create a new app and give it whatever name and description you'd like — you can always change it later.

Once you've created your application, there are a couple of important things to make note of on the following page. First are your **Client ID** and **Client Secret**. These are what we'll use to make requests to the Spotify API. Next, in _edit settings_, you'll find **Redirect URIs**. These are where your users will be redirected after logging in to Spotify. We will later set this to use the domain associated with your web app, but set it to `http://localhost:8888/callback` for now.

### Creating the App

Alright, now it's time to jump into the code. I personally used the following imports, you can delete whatever you don't use later.
 ```
 import json
 import requests
 from flask_session import Session
 from flask import Flask, request, redirect, render_template, url_for, session
 ```
Then create the app and give it a secret key. I also needed to store data larger than 4kb in the session object, so I set the type to `filesystem`.
```
app = Flask(__name__)
app.config["SECRET_KEY"] = "this is going on github anyways"
app.config['SESSION_TYPE'] = 'filesystem'
app.config.from_object(__name__)
Session(app)
```
Then add the following to start the app when the file runs.
```
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8888, debug=True)
```
Once we switch from testing, we'll come back and change this line.

### Adding the Website Logic

Okay so now we have an app technically, but it doesn't do anything! Let's start laying out what I call the 'logic' of the app — referring to how the various pages go to one another. 

#### Index

Most importantly, we have the landing page of the web app. All we need to do is render an HTML page that you can work on later.

```
@app.route("/")
def index():
    session.pop("access_key", None)
    session.pop("method_data", None)
    session.pop("plot_data", None)
    return render_template("index.html")
```
The `@app.route("/")` tells the app to run this code whenever the url is at "/", which is the root of the website. Hold on a second! Didn't I say all we need to do is render? Well, I'm jumping ahead a bit here. In later parts of the code, I save some data in the session object of the app. What I am doing here is clearing out any possible data that could be currently held. This is particularly important to do since I'm storing a reasonable amount of data as a file.

#### Authorization

Now we have to get permission to access the user's Spotify account.

```
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
```
So here, when we send our webpage to "/authorization", this redirects to the Spotify Login page, which is located at `https://accounts.spotify.com/authorize/` and needs several queries which we give in `auth_params`. The `show_dialog` option refers to whether the user has to log in every time, or if the login can be remembered. I've set this to true because I noticed one of my HTML pages wouldn't always load properly if it skipped the log in page. We are using `http://localhost:8888/callback` as the `redirect_uri` for now, but remember that it must match what you earlier gave to Spotify. The `client_id` is what was in your Spotify application page.

#### Callback

```
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
        session["access_token"] = json.loads(response.text)["access_token"]
        return render_template("loading.html", action="/loading1", msg="Collecting your top songs...")
    except:
        return render_template("error.html")
```
