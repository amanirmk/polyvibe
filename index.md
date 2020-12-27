# How to Make a Spotify Web App 

If you're both a programmer and a music enthusiast like me, odds are that you've considered making something with the Spotify API. If that sounds about right, then here's some help getting started. I'll be walking you through my process in creating my Spotify web app, [**polyvibe**](https://polyvibe.herokuapp.com), using Python, Flask, and Heroku. It's not a perfect app, but if it seems along the lines of what you'd like to make — keep on reading! I also recommend following along in the actual GitHub repository to help fill in any details I leave out.

## Obtaining Spotify API credentials

In order to interact with the Spotify API, you're required to have some credentials. Thankfully, all you need is a Spotify account. Visit [the developer dashboard](https://developer.spotify.com/dashboard) and log in. On the [applications page](https://developer.spotify.com/dashboard/applications), create a new app and give it whatever name and description you'd like — you can always change it later.

Once you've created your application, there are a couple of important things to make note of on the following page. First are your **Client ID** and **Client Secret**. These are what you'll use to make requests to the Spotify API. Next, in _edit settings_, you'll find **Redirect URIs**. This is where your users will be redirected after logging in to Spotify. We will later set this to use the domain associated with your web app, but set it to `http://localhost:8888/callback` for now.

## Creating the App

Alright, now it's time to jump into the code. Put this all in a file called `app.py`. I personally used the following imports, but you can always delete whatever you don't use later.
 ```python
 import json
 import requests
 from flask_session import Session
 from flask import Flask, request, redirect, render_template, url_for, session
 ```
Then create the app and give it a secret key. I also needed to store data larger than 4kb in the session object, so I set the type to `filesystem`.
```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "this is going on github anyways"
app.config['SESSION_TYPE'] = 'filesystem'
app.config.from_object(__name__)
Session(app)
```
Then add the following to start the app when the file runs.
```python
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8888, debug=True)
```
Once we switch from testing, we'll come back and change this line.

## Adding the Website Logic

Okay so now we have an app technically, but it doesn't do anything! Let's start laying out what I call the "logic" of the app — referring to how the various pages go to one another. 

### Index

Most importantly, we have the landing page of the web app. All we need to do is render an HTML page that you can work on later.
```python
@app.route("/")
def index():
    session.pop("access_key", None)
    session.pop("method_data", None)
    session.pop("plot_data", None)
    return render_template("index.html")
```
The `@app.route("/")` tells the app to run this code whenever the url is at "/", which is the root of the website. But hold on a second! Didn't I say all we need to do is render the HTML page? What are those extra lines doing there?! Well, I'm jumping a bit ahead here. In later parts of the code, I save some data in the session object of the app. What I am doing with `session.pop()` is clearing out any possible data that could be currently held. This is particularly important to do since I'm storing a reasonable amount of data as a file.

### Authorization

Next, we have to get permission to access the user's Spotify account.
```python
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
So here, when we send our webpage to "/authorization", this redirects to the Spotify login page, which is located at `https://accounts.spotify.com/authorize/` and requires several queries which we give in `auth_params`. The `show_dialog` option refers to whether the user has to log in every time, or if the login can be remembered. I've set this to true because I noticed one of my HTML pages wouldn't always load properly if it skipped the login page. We are using `http://localhost:8888/callback` as the `redirect_uri` for now, but remember that **it must match what you earlier gave to Spotify**. The `client_id` is what was in your Spotify application page. Most important here is the `scope`. This defines what we get access to. The full range of scopes is [here](https://developer.spotify.com/documentation/general/guides/scopes/), but I used `scope = "user-top-read playlist-read-private playlist-read-collaborative user-library-read"`.

### Callback

Once the user logs in, Spotify will redirect back to the `redirect_uri` that we gave it, and our app will then call this code.
```python
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
        return render_template("loading.html", action="/loading1", 
            msg="Collecting your top songs...")
    except:
        return render_template("error.html")
```
Let's break this down. First, we use `request.args` to get the authorization code from Spotify and send it back to get the access token which we will later use to make requests to the API. I save it in the session object for easy access later and render my next page. I believe it is good practice to set up an error page as well and let any errors redirect there, hence the try and except. However, assuming all things go well, we next begin the process of collecting and analyzing data. 

It is simplest to call your methods for data processing and then just redirect to the display page. This is what I recommend doing. However, unfortunately for me, Heroku only allows 30 seconds without hearing back from you. While my program doesn't usually take that long, it definitely can. So I have set up a rather complicated method to retrieve all of the necessary data. First, I split each step of the loading process into different flask redirects, which each have their own message to display to the screen. And then, in each of those, I have my methods abort their processes and save their current data if a timer reaches 20 seconds, and have them resume after another page redirect. There are likely many better ways to do this, and you also may not have to deal with this issue, so I will not go step by step through that here. All of this code is on GitHub however, so feel free to take a look if this sounds like something you need.

### Display

The final step of the web app's redirect logic, the display page.
```python
@app.route("/display")
def display():
    if session["method_data"]["incomplete_data_status"]:
        session["plot_data"]["incomplete_data_msg"] = \
            "Note: We encountered issues when collecting your data. The quality of this report may have been impacted."
    else:
        session["plot_data"]["incomplete_data_msg"] = ""
    return render_template("analysis.html", info=session["plot_data"])
```
Honestly, there's not much to see here. At each step of the data collection and analysis, I save the results to the session object. We can now pass this in the ``render_template`` method and access it in the HTML template.

## Collecting From the Spotify API

Okay, so we've finally finished the web logic. I'm not writing this post in the same order that I coded the app, so I apologize if things are a little confusing. I hope by the end of this all, everything will make sense — but if not, remember that the source code is available for your inspection.

**Note:** I recommend using a separate file for your collection and analysis so that your code doesn't get too messy. You can import the methods you need from that file to `app.py`.

All requests to the Spotify API will go to the base of `https://api.spotify.com/`, with extensions for the specific request. I set a variable `base = https://api.spotify.com/v1` because all of the requests begin with `v1` as well. In almost all cases, you will also need a header containing your authorization, which has the key `Authorization` and the value `Bearer ACCESS_TOKEN`. If you've stored it like me, the creation of the header is like this: 
```python
{"Authorization" : "Bearer " + session["access_token"]}
``` 
I have a lot of convoluted collection methods to obtain the user's personal info, top tracks, top artists, entire library, and their playlists. I'll show one of the simpler ones here, for collecting the top artists.
```python
def get_top_artists(artists, all_artists, incomplete_data, auth_header):
    for i,term in enumerate(["long_term", "medium_term", "short_term"]):
        response = requests.get(base + "/me/top/artists", 
            params={"time_range":term, "limit":10}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            artist_data = json.loads(response.text)["items"]
            artists[i].extend([{artist["name"]:artist} for artist in artist_data])
            for artist in artists[i]:
                all_artists.update(artist)
        else:
            print("Failed to retrieve {} top artists".format(term))
            incomplete_data = True 
    l_a_names = [list(artist.keys())[0] for artist in artists[0]]
    m_a_names = [list(artist.keys())[0] for artist in artists[1]]
    s_a_names = [list(artist.keys())[0] for artist in artists[2]]
    artist_names = [l_a_names, m_a_names, s_a_names]
    return artist_names, incomplete_data
 ```
Let's break this down. The request allows us to specify the term for the top artists: long, medium, and short. I, of course, want all of them. So I enumerate through the options, and send a request to `https://api.spotify.com/v1/me/top/artists` for 10 artists of the specified term. If the request goes through, then I load the items and iterate through the artist objects. I have decided to store them all in a dictionary for their term with their name as the key. And each term is in a list called `artists`. I then add them to a collective dictionary of all of the artists. Finally, for convenience, I make lists of the top 10 artists' names.

Spotify is quite good about [documenting](https://developer.spotify.com/documentation/web-api/reference/) what API requests should look like and the type of objects they return. It's the first place to look for assistance when making your collection methods.

## Analyzing the Data

Well now that we have all the information that we want, we need to do something with it! For my needs, simple graphs suffice and so I use Matplotlib to generate some plots. **If you use Matplotlib**, you need to set `plt.switch_backend('Agg')` or it won't run properly on Heroku. Here's a method involving the data I collected in the previous step. Note the additional imports needed for this.
```python
import io, base64
from urllib.parse import quote
import matplotlib.pyplot as plt

def top_artists(method_data, plot_data):
    plt.style.use('ggplot')
    plt.rc("font", family="serif")
    l_a_names, m_a_names, s_a_names = method_data["artist_names"]
    artist_set = set()
    artist_set.update(l_a_names)
    artist_set.update(m_a_names)
    artist_set.update(s_a_names)
    places_dict = {}
    count = max(len(l_a_names), len(m_a_names), len(s_a_names))
    for artist in artist_set:
        places = []
        for l in [l_a_names, m_a_names, s_a_names]:
            try:
                places.append(l.index(artist)+1)
            except:
                places.append(count+1)
        places_dict[artist] = places
    ha = {
        0:"left",
        1:"center",
        2:"right"
    }
    plt.figure(figsize=(10, 6))
    plt.gca().set_prop_cycle('color', [plt.cm.tab20(i) for i in np.linspace(0,1,20)])
    for artist in artist_set:
        plt.plot(places_dict[artist])
        for i,place in enumerate(places_dict[artist][::-1]):
            if place <= count:
                plt.annotate(artist, (2-i,place), ha=ha[2-i])
                break
    plt.yticks(list(range(1,count+1)))
    plt.gca().yaxis.tick_right()
    plt.xticks([0,1,2],["Long Term", "Medium Term", "Short Term"])
    plt.gca().set_ylim([0.5,count+0.5])
    plt.gca().invert_yaxis()
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close()
    img.seek(0)
    artists_pic = quote(base64.b64encode(img.read()).decode())
    plot_data["top_artists_img"] = artists_pic
 ```
Okay, so what's the objective of this method. The final result is a line graph that shows how artists' rankings rise and fall over the three terms. Now let's break it down. First thing I do is set some styling — ggplot looks great and even better with a serif font in my opinion. Then I get a set of all of the artists that comprise the top ten for these terms. Then I go through the terms and get the artist's ranking. If they aren't in the top ten, I put them at rank 11. 

Then it's time to start the actual plotting. I set the figure, the colors, and start plotting the rankings as lines. For each artist, I then annotate at the point closest to the end of the graph, where the artist is actually on the board. I also defined a `ha` dictionary for horizontal alignment, so that it changes depending on which point they're at. Next I set some labels and bounds on the graph, invert the y-axis so that it looks like an actual ranking, and save the plot as an encoded png.

## The HTML (Kinda, it's mostly up to you)

Well, now it's time to make everything look nice. Make a folder called `templates` where you'll put the HTML files. From there, it's about the same as making anything else with HTML. However, for CSS, you'll want to put those files in a folder called `static` (and for organizational purposes, a subfolder called `css`) and access them like this:
```html
{% raw %}
<link rel="stylesheet" href="{{ url_for('static', filename='css/index.css') }}">
{% endraw %}
```
To send your user to the login page, simply place a button with `href="/authorization"` and our existing web app logic will do the rest.

And of course, we'll want to display the graphs we make. Anything we pass in the `render_template` method will be available to use in your HTML file. If you followed along, we send a dictionary called `info`, from which we can access values like one would a normal dictionary. However, remember to use double braces around any variable, like `{% raw %}{{ info['user_name'] }}{% endraw %}`. 

For full HTML examples, check out the code on GitHub.

## Hosting Your Web App

We're almost done! Assuming your app works as intented when hosted locally, it's now time to put it on Heroku.

You'll need to install [Heroku](https://devcenter.heroku.com/articles/getting-started-with-python#set-up) and log in or make an account.

Next, `cd` into the folder where you wrote your app and [create it on Heroku](https://devcenter.heroku.com/articles/getting-started-with-python#deploy-the-app)
```shell
$ heroku create <name>
$ git push heroku HEAD:master
```
Where `<name>` is of course the name of your web app. 
(You can also link Heroku to a GitHub repository from the [Heroku website](https://dashboard.heroku.com/apps).)

Some of these files may have been created automatically, but if not then

- Create a `Procfile` and paste in the following:

```
web: gunicorn app:app --log-file=-
heroku ps:scale web=1
```

 - Create a `requirements.txt` and paste in any libraries you require. For me, this was:

```
Flask
flask_session
matplotlib
requests
numpy
gunicorn
```

 - And to be safe, create a `runtime.txt` and specify your version of Python, i.e `python-3.8.6`.

Make sure to push your changes to Heroku again. 

If this worked, then you should be able to visit your web app with `heroku open` or with the link `https://<name>.herokuapp.com`.

I remember encountering a lot of trouble here, so you may have to check out other sources to assist with getting the app properly hosted.

Assuming that you've successfuly hosted your app, there are two final changes to make. You need to **change the `redirect_uri`** to `https://<name>.herokuapp.com/callback` and add it to your accepted redirects on Spotify. Then you need to the **change the initialization** of your app from
```python
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8888, debug=True)
```
to
```python
if __name__ == '__main__':
    app.run(debug=True, use_reloader=True)
```
And with this, your app should be ready to use! 

But of course, there's almost always going to be a debugging process. If you use `print` statements in your code, you can look at the output with `heroku logs --tail`. 

**Thanks for reading, I wish you the best of luck!**

