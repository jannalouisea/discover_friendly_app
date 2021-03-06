from flask import Flask, render_template, redirect, request, session
import pandas as pd
import spotipy 
from spotipy.oauth2 import SpotifyClientCredentials
import requests
from generate_playlist import gen_playlist
import time

app = Flask(__name__) # Turn this file into a web app (create app object)
app.secret_key = "APP SECRET KEY"
app.static_folder = 'static'

API_BASE = 'https://accounts.spotify.com'
REDIRECT_URI = "https://discover-friendly.herokuapp.com/api_callback"
SCOPE = 'playlist-modify-private,playlist-modify-public,user-top-read, user-library-read'
SHOW_DIALOG = True # False later

CLI_ID = "CLI_ID"
CLI_SEC = "CLI_SEC"



@app.route("/")
def welcome():
    return render_template('index.html')


@app.route("/pick_prefs")
def pick_prefs():
    return render_template('pick_prefs.html')

# (1) -- authorization-code-flow: 
#           - Have your application request authorization
#           - The user logs in and authorizes access
@app.route("/verify")
def verify():
    auth_url = f'{API_BASE}/authorize?client_id={CLI_ID}&response_type=code&redirect_uri={REDIRECT_URI}&scope={SCOPE}&show_dialog={SHOW_DIALOG}'
    print(auth_url)
    return redirect(auth_url)


# (2) -- authorization-code-flow:
#           - Have your application request refresh and access tokens
#           - Spotify returns refresh and access tokens
@app.route("/api_callback")
def api_callback():
    session.clear()
    code = request.args.get('code')

    auth_token_url = f"{API_BASE}/api/token"
    res = requests.post(auth_token_url, data={
        "grant_type":"authorization_code",
        "code":code,
        "redirect_uri":"https://discover-friendly.herokuapp.com/api_callback",
        "client_id":CLI_ID,
        "client_secret":CLI_SEC
        })

    res_body = res.json()
    print(res.json())
    session["toke"] = res_body.get("access_token")

    return redirect("pick_prefs")


# (3) -- authorization-code-flow:
#           - Use the access token to access the Spotify Web API
#           - Spotify returns requested data
@app.route("/go", methods=['POST'])
def go():
    if request.method == 'POST': 
        try: 
            mood = request.form['mood']
        except:
            mood = ''
        genres = request.form.getlist('genres')
        thresh = request.form['prob-thresh']

        #if request.form["sub_but"] == "Generate a playlist from Janna's music!":

        df = pd.read_csv('final_rec_df.csv')
        df.drop(columns=['Unnamed: 0'])
        final_df = gen_playlist(df, mood, genres, thresh)

        uris = final_df['uri'].tolist()
        ids = []

        for uri in uris:
            ids.append(uri[14:])

        session['uris'] = uris
        session['ids'] = ids
        session['mood'] = mood
        session['genres'] = genres
        session['thresh'] = thresh

        return render_template('display_playlist.html', mood=mood, genres=genres, uris=uris, ids=ids, thresh=thresh)            


@app.route("/save_playlist", methods=["POST"])
def save_playlist():
    sp = spotipy.Spotify(auth=session['toke'])

    user = sp.current_user()
    uid = user['id']
    
    pl_created = sp.user_playlist_create(uid, "Discover Friendly Playlist", public=True, 
    description="A playlist made with the Discover Friendly app. These songs are recommendended based on Antoine's music taste.")

    pid = pl_created['id']
    pl_tracks_added = sp.user_playlist_add_tracks(uid, pid, session['uris'])

    return render_template('display_playlist.html', pl_saved = True, mood=session['mood'], genres=session['genres'], uris=session['uris'], ids=session['ids'], thresh=session['thresh'])




if __name__=='__main__':
    app.debug = True
    app.run()
