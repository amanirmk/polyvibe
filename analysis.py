import json
import requests
import io
import base64
import numpy as np
import time
from urllib.parse import quote
import matplotlib.pyplot as plt
from collections import Counter

plt.switch_backend('Agg')

time_limit = 20 #need to avoid 30 sec timeout on heroku

base = "https://api.spotify.com/v1"

def collect_top(method_data, plot_data):
    
    auth_header = method_data["auth_header"]
    incomplete_data = False

    all_tracks = {}
    all_artists = {}

    long_term_tracks = []
    medium_term_tracks = []
    short_term_tracks = []
    tracks = [long_term_tracks, medium_term_tracks, short_term_tracks]

    long_term_artists = []
    medium_term_artists = []
    short_term_artists = []
    artists = [long_term_artists, medium_term_artists, short_term_artists]

    #get user info
    user_name, user_image, inc_data1 = get_user_info(incomplete_data, auth_header)
    #get top tracks
    track_names, inc_data2 = get_top_tracks(tracks, all_tracks, incomplete_data, auth_header)
    #get top artists
    artist_names, inc_data3 = get_top_artists(artists, all_artists, incomplete_data, auth_header)
    incomplete_data == (inc_data1 or inc_data2 or inc_data3)

    plot_data["user_name"] = user_name
    plot_data["user_image"] = user_image
    plot_data["top_tracks"] = track_names

    method_data["incomplete_data_status"] = incomplete_data
    method_data["all_tracks"] = all_tracks
    method_data["tracks"] =  tracks
    method_data["artists"] = artists
    method_data["all_artists"] = all_artists
    method_data["artist_names"] = artist_names




def get_user_info(incomplete_data, auth_header):
    user_name = "username"
    user_image = "../static/media/blank_profile.png"
    # get user info
    response = requests.get(base + "/me", headers=auth_header)
    if response.status_code == requests.codes.ok:
        user = json.loads(response.text)
        if user["display_name"]:
                user_name = user["display_name"]
        try:
            if user["images"][0]:
                user_image = user["images"][0]["url"]
        except:
            print("User profile image unavailable")
    else:
        print("Failed to retrieve user profile data")
        incomplete_data = True
    return user_name, user_image, incomplete_data




def get_top_tracks(tracks, all_tracks, incomplete_data, auth_header):
    #get top tracks
    for i,term in enumerate(["long_term", "medium_term", "short_term"]):
        response = requests.get(base + "/me/top/tracks", params={"time_range":term, "limit":25}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            tracks_data = json.loads(response.text)["items"]
            tracks[i].extend([{track["name"]:track} for track in tracks_data])
            for track in tracks[i]:
                all_tracks.update(track)
        else:
            print("Failed to retrieve {} top tracks".format(term))
            incomplete_data = True 
    l_t_names = [list(track.keys())[0] for track in tracks[0]]
    m_t_names = [list(track.keys())[0] for track in tracks[1]]
    s_t_names = [list(track.keys())[0] for track in tracks[2]]
    track_names = [l_t_names, m_t_names, s_t_names]
    return track_names, incomplete_data




def get_top_artists(artists, all_artists, incomplete_data, auth_header):
    for i,term in enumerate(["long_term", "medium_term", "short_term"]):
        response = requests.get(base + "/me/top/artists", params={"time_range":term, "limit":10}, headers=auth_header)
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




def collect_library(method_data):
    
    global time_limit
    start_time = time.time()

    auth_header = method_data["auth_header"]
    incomplete_data = method_data["incomplete_data_status"]
    all_artists = method_data["all_artists"]
    all_tracks = method_data["all_tracks"]

    collected = 0
    try:
        collected = method_data["num_tracks_collected"]
    except:
        pass

    #get all saved tracks in library
    collected_library = False
    while not collected_library:
        if (time.time() - start_time) > time_limit:
            method_data["num_tracks_collected"] = collected
            break
        response = requests.get(base + "/me/tracks", params={"limit":50, "offset":collected}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            tracks_json = json.loads(response.text)
            tracks_data = [track["track"] for track in tracks_json["items"]]
            success = update_all_from_tracks(all_artists, all_tracks, tracks_data, auth_header)
            if not success:
                print("Failed to retrieve artists of saved tracks on batch {}".format(collected // 50))
                incomplete_data = True
            new = len(tracks_data)
            collected += new
            collected_library = new < 50
        else:
            print("Failed to retrieve saved tracks on batch {}".format(collected // 50))
            incomplete_data = True
            collected_library = True #don't want to get stuck

    method_data["incomplete_data_status"] = incomplete_data
    method_data["all_artists"] = all_artists
    method_data["all_tracks"] = all_tracks
    method_data["collected_library"] = collected_library


def update_all_from_tracks(all_artists, all_tracks, tracks_data, auth_header):
    #if not tracks, do nothing
    if not tracks_data:
        return True
    #add tracks to tracks collection
    [all_tracks.update({track["name"]:track}) for track in tracks_data]
    #add track authors to artist collection
    artist_ids = []
    success = True
    for track in tracks_data:
        artist_data = track["artists"]
        artist_ids.extend([artist["id"] for artist in artist_data])
    #get full artist object (because genres aren't included in simple)
    while artist_ids:
        #can only request 50 at a time
        artist_ids_str = str(artist_ids[:50]).replace(" ", "").replace("'","")[1:-1]
        artist_ids = artist_ids[50:]
        artist_response = requests.get(base + "/artists", params={"ids":artist_ids_str}, headers=auth_header)
        if artist_response.status_code == requests.codes.ok:
            artist_data = json.loads(artist_response.text)["artists"]
            for artist in artist_data:
                if artist:
                    all_artists.update({artist["name"]:artist})
        else:
            success = False
    return success




def collect_playlists(method_data):
    
    global time_limit
    start_time = time.time()

    auth_header = method_data["auth_header"]
    incomplete_data = method_data["incomplete_data_status"]
    all_artists = method_data["all_artists"]
    all_tracks = method_data["all_tracks"]

    collected = 0
    try:
        collected = method_data["num_playlists_collected"]
    except:
        pass

    collected_playlists = False
    try:
        collected_playlists = method_data["collected_playlists"]
    except:
        pass

    playlist_data = []
    try:
        playlist_data = method_data["playlist_data"]
    except:
        pass

    while not collected_playlists:
        if (time.time() - start_time) > time_limit:
            method_data["num_playlists_collected"] = collected
            break
        response = requests.get(base + "/me/playlists", params={"limit":50, "offset":collected}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            new_playlist_data = json.loads(response.text)["items"]
            playlist_data.extend(new_playlist_data)
            new = len(new_playlist_data)
            collected += new
            collected_playlists = new < 50
        else:
            print("Failed to retrieve a playlist")
            incomplete_data = True
            collected_playlists = True #don't want to get stuck

    collected_tracks = True #if wrongfully true, then collected_playlists is false
    if collected_playlists:

        i_playlist = 0
        incomplete_playlist = False
        try:
            i_playlist = method_data["i_playlist"]
            incomplete_playlist = True
        except:
            pass
        
        for playlist in playlist_data[i_playlist:]:
            href = playlist["tracks"]["href"]
            if incomplete_playlist:
                href = method_data["next_href"]
                incomplete_playlist = False
            while href:
                if (time.time() - start_time) > time_limit:
                    method_data["next_href"] = href
                    method_data["i_playlist"] = i_playlist
                    collected_tracks = False
                    break
                tracks_response = requests.get(href, headers=auth_header)
                if tracks_response.status_code == requests.codes.ok:
                    tracks_json = json.loads(tracks_response.text)
                    href = tracks_json["next"]
                    tracks_data = [track["track"] for track in tracks_json["items"]]
                    success = update_all_from_tracks(all_artists, all_tracks, tracks_data, auth_header)
                    if not success:
                        print("Failed to retrieve artists from some tracks")
                        incomplete_data = True
                else:
                    print("Failed to retrieve additional tracks from playlist")
                    incomplete_data = True
            if not collected_tracks:
                break
            i_playlist += 1
    
    method_data["incomplete_data_status"] = incomplete_data
    method_data["all_artists"] = all_artists
    method_data["all_tracks"] = all_tracks
    method_data["collected_tracks"] = collected_tracks
    method_data["collected_playlists"] = collected_playlists
    method_data["playlist_data"] = playlist_data




def top_artists(method_data, plot_data):
    l_a_names, m_a_names, s_a_names = method_data["artist_names"]
    plt.style.use('ggplot')
    plt.rc("font", family="serif")
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




def top_genres(method_data, plot_data):
    artists_terms_list = method_data["artists"]
    term_genres = [Counter(), Counter(), Counter()] #long, med, short
    for i,term in enumerate(artists_terms_list):
        for artist in term:
            term_genres[i].update(artist[list(artist.keys())[0]]["genres"])
    total_counts = [0,0,0]
    all_genres = set()
    for i,genre_counter in enumerate(term_genres):
        for genre in genre_counter:
            total_counts[i] += genre_counter[genre]
            all_genres.add(genre)
    all_genres_list = list(all_genres)
    genre_props = []
    for genre in all_genres_list:
        props = []
        for i in range(3):
            props.append(term_genres[i][genre]/total_counts[i])
        genre_props.append(props)
    all_genres_list, genre_props = list(zip(*sorted(list(zip(all_genres_list, genre_props)), key=(lambda pair: pair[1][::-1]))))
    plt.figure(figsize=(10, 6))
    plt.gca().set_prop_cycle('color', [plt.cm.tab20(i) for i in np.linspace(0,1,20)])
    plt.stackplot([0,1,2], *genre_props, labels=all_genres_list)
    plt.gca().yaxis.tick_right()
    plt.yticks([num/100 for num in range(0,100+1, 10)], [str(num)+"%" for num in range(0,100+1,10)])
    plt.xticks([-0.75, 0,1,2],["", "Long Term", "Medium Term", "Short Term"])
    plt.gca().set_ylim([0,1])
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.gca().legend(handles[::-1][:29], labels[::-1][:29], loc='center left', fontsize=8)
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close()
    img.seek(0)
    genres_stack_plot = quote(base64.b64encode(img.read()).decode())
    plot_data["top_genres_img"] = genres_stack_plot




def genre_diversity(method_data, plot_data):
    artists_dict = method_data["all_artists"]
    genre_counts = Counter()
    for artist_name in artists_dict:
        artist = artists_dict[artist_name]
        genre_counts.update(artist["genres"])
    total = sum(genre_counts.values())
    labels, counts = list(zip(*[(genre, count) if count/total > 0.015 else ("", count) for genre, count in genre_counts.most_common()]))
    plt.figure(figsize=(10, 6))
    plt.gca().set_prop_cycle('color', [plt.cm.tab20(i) for i in np.linspace(0,1,20)])
    plt.pie(counts, explode=[0.1]+[0]*(len(counts)-1), labels=labels, textprops={'fontsize': 9}, startangle=110)
    plt.legend(fontsize=7, labels=["{}.  {} ({}%)".format(i+1, item[0], round(100*item[1]/total, 2)) for i,item in enumerate(genre_counts.most_common(30))], loc="upper right")
    plt.gca().axis('equal')
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close()
    img.seek(0)
    genres_pie_chart = quote(base64.b64encode(img.read()).decode())
    plot_data["genres_pie_chart"] = genres_pie_chart




def artist_diversity(method_data, plot_data):
    tracks_dict = method_data["all_tracks"]
    artist_counts = Counter()
    for track_name in tracks_dict:
        track = tracks_dict[track_name]
        artist_counts.update([artist["name"] for artist in track["artists"]])
    total = sum(artist_counts.values())
    labels, counts = list(zip(*[(genre, count) if count/total > 0.015 else ("", count) for genre, count in artist_counts.most_common()]))
    plt.figure(figsize=(10, 6))
    plt.gca().set_prop_cycle('color', [plt.cm.tab20(i) for i in np.linspace(0,1,20)])
    plt.pie(counts, explode=[0.1]+[0]*(len(counts)-1), labels=labels, textprops={'fontsize': 9}, startangle=110)
    plt.legend(fontsize=7, labels=["{}.  {} ({}%)".format(i+1, item[0], round(100*item[1]/total, 2)) for i,item in enumerate(artist_counts.most_common(30))], loc="upper right")
    plt.gca().axis('equal')
    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight')
    plt.close()
    img.seek(0)
    artists_pie_chart = quote(base64.b64encode(img.read()).decode())
    plot_data["artists_pie_chart"] = artists_pie_chart




def features(method_data, plot_data):

    tracks_dict = method_data["all_tracks"]
    incomplete_data = method_data["incomplete_data_status"]
    auth_header = method_data["auth_header"]

    valence = []
    energy = []
    danceability = []
    popularity = []
    ids_for_features = []
    for track_name in tracks_dict:
        track = tracks_dict[track_name]
        popularity.append(track["popularity"]/100)
        ids_for_features.append(track["id"])
    #get features, 100 at a time
    for i in range(0, len(ids_for_features), 100):
        ids_str = str(ids_for_features[i:i+100]).replace(" ", "").replace("'","")[1:-1]
        response = requests.get(base + "/audio-features", params={"ids":ids_str}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            features = json.loads(response.text)["audio_features"]
            for audio_object in features:
                if audio_object:
                    valence.append(audio_object["valence"])
                    energy.append(audio_object["energy"])
                    danceability.append(audio_object["danceability"])
        else:
            incomplete_data = True
            print("Failed to retrieve features on batch " + str(i//100))
    imgs = []
    means = []
    #make histograms
    for category in [valence, energy, danceability, popularity]:
        plt.figure(figsize=(10, 6))
        plt.hist(category, range=(0,1), bins=20, color='#8D7EF2')
        img = io.BytesIO()
        plt.savefig(img, format='png', bbox_inches='tight')
        plt.close()
        img.seek(0)
        imgs.append(quote(base64.b64encode(img.read()).decode()))
        means.append(round(sum(category)/len(category), 2))

    plot_data["features_imgs"] = imgs
    plot_data["feature_means"] = means
    method_data["incomplete_data_status"] = incomplete_data




def recommendations(method_data, plot_data):

    artists = method_data["artists"]
    auth_header = method_data["auth_header"]
    means = plot_data["feature_means"]

    #top 5 artists, short term prioritized
    artists = artists[2]+artists[1]+artists[0]
    artists = [artist[list(artist.keys())[0]]["id"] for artist in artists]
    seed_artists = sorted(list(set(artists)), key=(lambda artist:artists.index(artist)))[:5]
    params = {
        "seed_artists" :seed_artists,
        "target_valence" : means[0],
        "target_energy" : means[1],
        "target_danceability" : means[2],
    }
    plot_data["recommendations"] = []
    response = requests.get(base + "/recommendations", params=params, headers=auth_header)
    if response.status_code == requests.codes.ok:
        tracks = json.loads(response.text)["tracks"]
        plot_data["recommendations"] =  [[track["name"], ", ".join([artist["name"] for artist in track["artists"]])] for track in tracks]
