from flask import Flask, render_template, redirect, request, jsonify, session
from markupsafe import Markup, escape

import os
from dotenv import load_dotenv

import json, urllib, uuid, requests, time

from models import init_db, import_listen_history, fetch_all_missing_data, get_completed_albums, get_overview

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

init_db()

MAX_FILES = 50
MAX_FILE_SIZE = 200 * 1024**2 #200mb

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE


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


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login/spotify')
def login_spotify_request():
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


def get_user():
    #TODO: Make this return the user_id tied to the spotify_id given by https://api.spotify.com/v1/me
    return 1


@app.route('/callback')
def callback():
  
    code = request.args.get('code')
    try:
        credentials = get_access_token(code)
    except:
        return redirect('/login')
    session['token'] = credentials['access_token']
    return redirect('/1')


@app.route('/settings')
def settings():
    return redirect('/settings/profile')


@app.route('/settings/profile')
def profile():
    return render_template('settings/profile.html')


@app.route('/settings/overrides')
def overrides():
    return render_template('settings/overrides.html')


@app.route('/settings/imports', methods=['GET'])
def imports_get():
    return render_template('settings/imports.html')


@app.route('/settings/imports', methods=['POST'])
def imports_post():
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
    

@app.route('/<user>')
def stats(user):
    sort_order = request.args.get('sort-order', 'date-released')
    group_by = request.args.get('group-by', 'decade')

    if sort_order == 'date-completed':
        completed_albums = get_completed_albums(user, sort_by='completion_date')
        sort_key = 'completion_date'
    else:
        completed_albums = get_completed_albums(user, sort_by='release_date')
        sort_key = 'release_date'

    return render_template(
        'stats.html',
        overview_section=Markup(_render_overview()),
        album_sections=Markup(_render_album_sections(completed_albums, group_by=group_by, sort_key=sort_key))
    )


@app.route('/exceptions', methods=['POST'])
def add_exception():
    album_id = request.form.get('album_id')
    print(album_id)
    return redirect(request.referrer or '/')

def _group_label(item_date, group_by='decade'):
    if item_date is None:
        return 'Unknown'

    if group_by == 'decade':
        return f'{(item_date.year // 10) * 10}s'

    elif group_by == 'year':
        return str(item_date.year)

    elif group_by == 'month':
        return item_date.strftime('%B %Y')

    elif group_by == 'day':
        return item_date.strftime('%A, %B %d, %Y')

    else:
        return f'{(item_date.year // 10) * 10}s'


def _render_album_sections(completed_albums, group_by='decade', sort_key='release_date'):
    if not completed_albums:
        return '<p>No content to show</p>'

    content = ''
    current_label = None
    for album, completion_date in completed_albums:
        artists = ', '.join([artist.name for artist in album.artists])
        group_date = album.release_date if sort_key == 'release_date' else completion_date
        label = _group_label(group_date, group_by)

        if current_label is None:
            current_label = label
            content += f"""
                <section>
                    <button type="button" class="collapsible"><h2>{label}</h2></button>
                    <div class="albums-grid open">
                """

        elif current_label != label:
            current_label = label
            content += f"""
                    </div>
                </section>
                <hr>
                <section>
                    <button type="button" class="collapsible"><h2>{label}</h2></button>
                    <div class="albums-grid open">
                """

        content += f"""
                        <article class="album">
                            <div class="album-image">
                                <img src="{escape(album.icon_uri)}" alt="Album cover for {escape(album.name)}" width="200" height="200">

                                <form method="post" action="/exceptions">
                                    <input type="hidden" name="album_id" value="{escape(album.id)}">
                                    <button type="submit" class="album-button" title="Add album to exceptions">
                                        ⚙︎
                                    </button>
                                </form>
                            </div>
                            <h3 class="album-name">{escape(album.name)}</h3>
                            <h4 class="album-artists">{escape(artists)}</h4>
                        </article>
        """

    content += """
                    </div>
                </section>
    """
    return content


def _render_overview():
    d = get_overview()
    return f'''
        <div class='overview-grid'>
        <div><h2>{format(d['streams'], ',')}</h2><h3>streams</h3></div>
        <div><h2>{format(d['ms_played']//3600_000, ',')}</h2><h3>hours streamed</h3></div>
        </div>

        <div class='overview-grid'>
        <div><h2>{format(d['tracks'], ',')}</h2><h3>tracks</h3></div>
        <div><h2>{format(d['albums'], ',')}</h2><h3>albums</h3></div>
        <div><h2>{format(d['artists'], ',')}</h2><h3>artists</h3></div>
        </div>
    '''


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