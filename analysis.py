import json
import requests
import io
import base64
import numpy as np
from urllib.parse import quote
import matplotlib.pyplot as plt
from collections import Counter

plt.switch_backend('Agg')

base = "https://api.spotify.com/v1"

def analyze_spotify(access_token):
    auth_header = {"Authorization": "Bearer " + access_token}

    incompleteData = False

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
        incompleteData = True
    
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
            incompleteData = True 
    l_t_names = [list(track.keys())[0] for track in long_term_tracks]
    m_t_names = [list(track.keys())[0] for track in medium_term_tracks]
    s_t_names = [list(track.keys())[0] for track in short_term_tracks]
    track_names = [l_t_names, m_t_names, s_t_names]
    
    #get top artists
    for i,term in enumerate(["long_term", "medium_term", "short_term"]):
        response = requests.get(base + "/me/top/artists", params={"time_range":term, "limit":10}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            artist_data = json.loads(response.text)["items"]
            artists[i].extend([{artist["name"]:artist} for artist in artist_data])
            for artist in artists[i]:
                all_artists.update(artist)
        else:
            print("Failed to retrieve {} top artists".format(term))
            incompleteData = True 
    l_a_names = [list(artist.keys())[0] for artist in long_term_artists]
    m_a_names = [list(artist.keys())[0] for artist in medium_term_artists]
    s_a_names = [list(artist.keys())[0] for artist in short_term_artists]

    #get all saved tracks in library
    collectedLibrary = False
    collected = 0
    while not collectedLibrary:
        response = requests.get(base + "/me/tracks", params={"limit":50, "offset":collected}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            tracks_data = json.loads(response.text)["items"]
            success = updateAllFromTracks(all_artists, all_tracks, tracks_data, auth_header)
            if not success:
                print("Failed to retrieve artists of saved tracks on batch {}".format(collected // 50))
                incompleteData = True
            new = len(tracks_data)
            collected += new
            collectedLibrary = new < 50
        else:
            print("Failed to retrieve saved tracks on batch {}".format(collected // 50))
            incompleteData = True
            collectedLibrary = True #don't want to get stuck

    #get all playlists
    collectedPlaylists = False
    collected = 0
    while not collectedPlaylists:
        response = requests.get(base + "/me/playlists", params={"limit":50, "offset":collected}, headers=auth_header)
        if response.status_code == requests.codes.ok:
            playlist_data = json.loads(response.text)["items"]
            for playlist in playlist_data:
                tracks_response = requests.get(playlist["tracks"]["href"], headers=auth_header)
                if tracks_response.status_code == requests.codes.ok:
                    tracks_json = json.loads(tracks_response.text)
                    tracks_data = tracks_json["items"]
                    while tracks_json["next"]:
                        tracks_response = requests.get(tracks_json["next"], headers=auth_header)
                        if tracks_response.status_code == requests.codes.ok:
                            tracks_json = json.loads(tracks_response.text)
                            tracks_data.extend(tracks_json["items"])
                        else:
                            print("Failed to retrieve additional tracks from playlist")
                            incompleteData = True
                    tracks_data = [track["track"] for track in tracks_data]
                    success = updateAllFromTracks(all_artists, all_tracks, tracks_data, auth_header)
                    if not success:
                        print("Failed to retrieve artists of saved tracks from playlist")
                        incompleteData = True
                else:
                    print("Failed to retrieve any tracks from the playlist")
                    incompleteData = True
            new = len(playlist_data)
            collected += new
            collectedPlaylists = new < 50
        else:
            print("Failed to retrieve a playlist")
            incompleteData = True
            collectedPlaylists = True #don't want to get stuck

    feature_graphs, means, success = features(all_tracks, auth_header)
    if not success:
        incompleteData = True

    if incompleteData:
        incompleteData = "Note: We encountered issues when collecting your data. The quality of this report may have been impacted."
    else:
        incompleteData = ""

    plot_data = {
        "incomplete_data" : incompleteData,
        "user_name" : user_name,
        "user_image" : user_image,
        "top_tracks" : track_names,
        "top_artists_img" : top_artists(l_a_names, m_a_names, s_a_names),
        "artists_pie_chart": artist_diversity(all_tracks),
        "top_genres_img" : top_genres(artists),
        "genres_pie_chart": genre_diversity(all_artists),
        "features_imgs" : feature_graphs,
        "feature_means" : means,
        "recommendations" : recommendations(artists, means, auth_header)
    }
    return plot_data 

def updateAllFromTracks(all_artists, all_tracks, tracks_data, auth_header):
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

def top_artists(l_a_names, m_a_names, s_a_names):
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
    return artists_pic

def top_genres(artists_terms_list):
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
    return genres_stack_plot

def genre_diversity(artists_dict):
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
    return genres_pie_chart

def artist_diversity(tracks_dict):
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
    artist_pie_chart = quote(base64.b64encode(img.read()).decode())
    return artist_pie_chart
    
def features(tracks_dict, auth_header):
    success = True
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
            success = False
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
    
    return imgs, means, success

def recommendations(artists, means, auth_header):
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
    response = requests.get(base + "/recommendations", params=params, headers=auth_header)
    if response.status_code == requests.codes.ok:
        tracks = json.loads(response.text)["tracks"]
        return [[track["name"], ", ".join([artist["name"] for artist in track["artists"]])] for track in tracks]
    return []