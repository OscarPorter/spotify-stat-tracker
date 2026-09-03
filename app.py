from flask import Flask, render_template, redirect, request, jsonify, session
from markupsafe import Markup

import os
from dotenv import load_dotenv

import json, urllib, uuid, requests, time

from models import init_db, import_listen_history, fetch_all_missing_data, get_completed_albums

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

init_db()

MAX_FILES = 50
MAX_FILE_SIZE = 200 * 1024**2 #200mb

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


@app.route('/')
def index_get(): 
    return render_template('index.html')

def write_json_to_db():
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
    session['token'] = credentials['access_token']
    return redirect('/import_history')


@app.route('/import_history', methods=['GET'])
def import_history_get():
    return render_template('import_history.html')

    
@app.route('/import_history', methods=['POST'])
def import_history_post():
    action = request.form.get('submit_action')

    if action == 'upload_history':
        write_json_to_db()
        return '<p>Files imported</p>'

    elif action == 'fetch_spotify_data':
        try:
            fetch_all_missing_data(fetch_track)
        except Exception as error:
            return f'<p>{error}</p>'
        return '<p>All done!</p>'


@app.route('/stats')
def stats():
    completed_albums = get_completed_albums()
    content = ''
    for album in completed_albums:
        artists = ', '.join([artist.name for artist in album.artists])
        content += f"""
        <div>
            <img src="{album.icon_uri}" width="250" height="250">
            <p style="width: 250px; overflow-wrap: break-word;">{album.name} • {artists}</p>
        </div>
        """

    return render_template('stats.html', data=Markup(content))


def fetch_track(id):
    track_url = f'https://api.spotify.com/v1/tracks/{id}'
    headers = {'Authorization': f'Bearer {session.get('token')}'}
    response = requests.get(track_url, headers=headers)
    time.sleep(0.5)
    return response.json()


def fetch_profile():
    url = 'https://api.spotify.com/v1/me'
    headers = {'Authorization': f'Bearer {session.get('token')}'}
    response = requests.get(url, headers=headers)
    return response.json()

    
if __name__ == '__main__':
   app.run(debug=True)