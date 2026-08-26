from flask import Flask, render_template, redirect, request, jsonify

import os
from dotenv import load_dotenv

import json, urllib, uuid, requests

from models import import_listen_history, init_db

load_dotenv()

app = Flask(__name__)

init_db()

MAX_FILES = 50
MAX_FILE_SIZE = 200 * 1024**2 #200mb

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

@app.route('/',methods=['GET'])
def page_name_get(): 
    return render_template('index.html')

@app.route('/', methods=['POST'])
def page_name_post():
    uploaded_files = request.files.getlist('data_json_files')

    if not uploaded_files or len(uploaded_files) > MAX_FILES:
        return jsonify(error='Invalid number of files'), 400
    
    data = []
    
    for file in uploaded_files:
        if not file.filename.lower().endswith('.json'):
            return jsonify(error="Only JSON files are accepted"), 400
        try:
            data.append(json.loads(file.read()))
        except (TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return jsonify(error="Only JSON files are accepted"), 400

    import_listen_history(data)
    return jsonify(data)

@app.route('/login')
def login():
    authentication_request_params = {
    'response_type': 'code',
    'client_id': os.getenv('CLIENT_ID'),
    'redirect_uri': os.getenv('REDIRECT_URI'),
    'scope': 'user-read-email user-read-private user-top-read',
    'state': str(uuid.uuid4()),
    'show_dialog': 'true'
    }
    auth_url = 'https://accounts.spotify.com/authorize/?' + urllib.parse.urlencode(authentication_request_params)
    return redirect(auth_url)

def get_access_token(authorization_code:str):
    spotify_request_access_token_url = 'https://accounts.spotify.com/api/token/?'
    body = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'client_id' : os.getenv('CLIENT_ID'),
        'client_secret': os.getenv('CLIENT_SECRET'),
        'redirect_uri': os.getenv('REDIRECT_URI')
    }
    response = requests.post(spotify_request_access_token_url, data = body)
    if response.status_code == 200:
        return response.json()
    raise Exception ('Failed to obtain Access token')

@app.route('/callback')
def callback():
  
    code = request.args.get('code')
    credentials = get_access_token(code)
    os.environ['token'] = credentials['access_token']
    return redirect('/your-music')

@app.route('/your-music')
def your_music():
    user_profile_url = 'https://api.spotify.com/v1/me?'
    user_top_items_url = 'https://api.spotify.com/v1/me/top/'
    audio_features_url = 'https://api.spotify.com/v1/audio-features/'
    limit_tracks = 18
    # NB: Add the access token to the request header
    headers = {
    'Authorization': f'Bearer {os.getenv("token")}'
    }
    request_params_artists = {
    'limit':18
    }
    request_params_tracks = {
    'limit': 18
    }
    #Retrieving User details via GET request to user profile endpoint
    user_profile = requests.get(user_profile_url, headers=headers)
    if user_profile.status_code == 200:
        user_profile = user_profile.json()
        display_name = user_profile['display_name']
        #Retrieving top Artists details via GET request to top artists endpoint
        top_artists_url = user_top_items_url + 'artists?' + urllib.parse.urlencode(request_params_artists)
        artists = requests.get(top_artists_url, headers=headers)
    if artists.status_code == 200:
        artists = artists.json()
        artists = artists['items']
    return jsonify(artists)

if __name__ == '__main__':
   app.run(debug=True)