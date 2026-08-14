from flask import Flask, render_template

import os
from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

sp = spotipy.Spotify(
   auth_manager=SpotifyOAuth(
      client_id=CLIENT_ID,
      client_secret=CLIENT_SECRET,
      redirect_uri="http://127.0.0.1:5000",
      scope="user-library-read"))

taylor_uri = 'spotify:artist:06HL4z0CvFAxyc27GXpf02'
results = sp.artist_albums(taylor_uri, album_type='album')
albums = results['items']
while results['next']:
   results = sp.next(results)
   albums.extend(results['items'])

for album in albums:
   print(album['name'])

    
'''
app = Flask(__name__)

@app.route('/')
def home():
   return render_template('index.html')

if __name__ == '__main__':
   app.run()
'''