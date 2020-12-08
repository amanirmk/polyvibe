import json
import requests
import io
import base64
import numpy as np
from urllib.parse import quote
import matplotlib.pyplot as plt
from collections import Counter

base = "https://api.spotify.com/v1"
colors = ['#8D7EF2', '#6DBFF2', '#E9A7F2', '#f64360', '#3f2ff5', '#fa05f2', '#10d0de']

def analyze_spotify(access_token):
    auth_header = {"Authorization": "Bearer " + access_token}
    
    incompleteData = False

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

    plot_data = {
        "incomplete_data":incompleteData,
        "top_artists_img":top_artists(l_a_names, m_a_names, s_a_names),
        "top_genres_img": top_genres(artists),
        "all_genres": genres(all_artists),
        "features_imgs":features(all_tracks)
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
    global colors
    plot_colors = colors
    while len(colors) < len(artist_set):
        plot_colors += colors
    colorIter = iter(plot_colors)
    for artist in artist_set:
        plt.plot(places_dict[artist], color=next(colorIter))
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
    plt.savefig(img, format='png')
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
    all_genres_list.reverse()
    plt.figure(figsize=(10, 6))
    plt.set_cmap(plt.cm.tab20)
    # plt.gca().set_prop_cycle('color', [colormap(i) for i in np.linspace(0, 1, len(all_genres_list))])
    plt.stackplot([0,1,2], *genre_props, labels=all_genres_list)
    plt.yticks(list(range(0,100+1, 10)), [str(num)+"%" for num in range(0,100+1,10)])
    plt.gca().yaxis.tick_right()
    plt.xticks([-0.75, 0,1,2],["", "Long Term", "Medium Term", "Short Term"])
    plt.gca().set_ylim([0,1])
    handles, labels = plt.gca().get_legend_handles_labels()
    plt.gca().legend(handles[::-1], labels[::-1], loc='center left', fontsize=8)
    img = io.BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    genres_stack_plot = quote(base64.b64encode(img.read()).decode())
    return genres_stack_plot


    

def genres(artists_dict):
    ...

def features(tracks_dict):
    ...






    #note that lengths may be less than limit

    #artists over various terms
    #can get genres associated with artists
    #can get songs in playlists / saved
    #recommendations


    #line graph of top 25 artists (short, med, long)
    #stack plot of genres calculated from artists (short, med, long)
    #distributions of song features for all tracks (with standard next to them)
    #recommendations based on song features





    # plt.savefig(img, format='png')
    # plt.close()
    # img.seek(0)

    # image_urls[feature] = quote(base64.b64encode(img.read()).decode())