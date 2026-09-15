from flask import Flask, render_template, redirect, request, jsonify, session
from markupsafe import Markup, escape

import os
from datetime import date, datetime, time as datetime_time
from dotenv import load_dotenv

import json, urllib, uuid, requests, time

from models import (init_db, import_listen_history, fetch_all_missing_data, get_completed_albums, 
                    get_listening_stats, spotify_login, update_profile_content, delete_account, 
                    get_profile_content, url_to_id, id_to_url, add_override, get_overrides,
                    edit_override, delete_override
)

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

    import_listen_history(data, session['user_id'])
    
    
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


def fetch_current_user_data():
    url = 'https://api.spotify.com/v1/me'
    headers = {'Authorization': f'Bearer {session.get('token')}'}
    response = requests.get(url, headers=headers)
    data = response.json()
    if data.get('error'):
        raise Exception ('Failed to obtain user data')
    return data


@app.route('/callback')
def callback():
  
    code = request.args.get('code')
    try:
        credentials = get_access_token(code)
    except:
        return redirect('/login')
    session['token'] = credentials['access_token']

    try:
        user_data = fetch_current_user_data()
    except:
        return redirect('/logout')

    session['user_id'] = spotify_login(user_data)
    session['display_name'] = user_data['display_name']
    session['profile_image'] = user_data['images'][0]['url']

    return redirect(f'/stats')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/settings')
def settings():
    return redirect('/settings/profile')


@app.route('/settings/profile', methods=['GET'])
def profile_get():
    if not session.get('user_id'):
        return redirect('/login')

    _, custom_url, bio, _ = get_profile_content(session['user_id'])
    return render_template(
        'settings/profile.html',
        custom_url = custom_url,
        bio = bio
    )


@app.route('/settings/profile', methods=['POST'])
def profile_post():
    action = request.form.get('submit_action')
    if action == 'update_details':
        update_profile_content(
            session['user_id'],
            request.form.get('custom-url'),
            request.form.get('bio')
        )
        return redirect('/settings/profile')
    
    elif action == 'delete_account':
        delete_account(
            session['user_id']
        )
        return redirect('/logout')
    

@app.route('/settings/overrides', methods=['GET'])
def overrides_get():
    if not session.get('user_id'):
        return redirect('/login')

    overrides = get_overrides(session['user_id'])
    return render_template('settings/overrides.html', override_options=Markup(_render_overrides(overrides)))


@app.route('/settings/overrides', methods=['POST'])
def overrides_post():
    action = request.form.get('submit_action')
    override_id = request.form.get('override_id')

    if action == 'edit_override':
        release_value = request.form.get('release')
        completion_value = request.form.get('completion')
        release_date = date.fromisoformat(release_value) if release_value else None
        completion_date = (
            datetime.combine(date.fromisoformat(completion_value), datetime_time.min)
            if completion_value else None
        )
        hidden = request.form.get('hidden') == 'true'
        edit_override(
            override_id,
            release_date=release_date, 
            completion_date=completion_date, 
            hidden=hidden
        )
        
    elif action == 'delete_override':
        delete_override(
            override_id
        )

    return redirect('/settings/overrides')


def _render_overrides(overrides):
    content = '<hr>'
    for override in overrides:
        content += f'''
            <div>
                <form style="display: inline-block;" action="/settings/overrides" method="post">
                    <input type="hidden" name="submit_action" value="edit_override">
                    <input type="hidden" name="override_id" value="{override.id}">

                    <img src="{escape(override.album.icon_uri)}" alt="Album cover for {escape(override.album.name)}" width="65" height="65">

                    <label for="release-{override.id}">Release date: </label>
                    <input type="date" id="release-{override.id}" name="release" value="{_format_date_input(override.release_date)}">

                    <label for="completion-{override.id}">Completion date: </label>
                    <input type="date" id="completion-{override.id}" name="completion" value="{_format_date_input(override.completion_date)}">
        
                    <label for="hidden-{override.id}">Hidden: </label>
                    <input style="display: inline-block;" type="checkbox" id="hidden-{override.id}" name="hidden" value="true" {'checked' if override.hidden else ''}>

                    <button type="submit">Update</button>
                </form>
                <form style="display: inline-block;" action="/settings/overrides" method="post">
                    <input type="hidden" name="submit_action" value="delete_override">
                    <input type="hidden" name="override_id" value="{override.id}">
                    <button type="submit">Delete</button>
                </form>
                <hr>
            </div>

        '''
    return content


def _format_date_input(value):
    if value is None:
        return ''
    if isinstance(value, datetime):
        value = value.date()
    return value.isoformat()


@app.route('/settings/imports', methods=['GET'])
def imports_get():
    if not session.get('user_id'):
        return redirect('/login')
    return render_template('settings/imports.html')


@app.route('/settings/imports', methods=['POST'])
def imports_post():
    action = request.form.get('submit_action')

    if action == 'upload_history':
        write_json_to_db()
        return redirect('/settings/imports')

    elif action == 'fetch_spotify_data':
        try:
            fetch_all_missing_data(fetch_track)
        except Exception as error:
            return f'<p>{error}</p>'
        return redirect('/settings/imports')
    

@app.route('/stats')
def my_stats():
    url = id_to_url(session['user_id'])
    return redirect(f'stats/{url}')


@app.route('/stats/<url>')
def stats(url):
    try:
        user = url_to_id(url)
    except AttributeError:
        return redirect('/')
    
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
        profile_section=Markup(_render_profile(user)),
        overview_section=Markup(_render_overview(user)),
        album_sections=Markup(_render_album_sections(completed_albums, group_by=group_by, sort_key=sort_key))
    )


@app.route('/exceptions', methods=['POST'])
def add_exception():
    album_id = request.form.get('album_id')
    try:
        add_override(session['user_id'], album_id)
    except:
        return redirect(request.referrer or '/')

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
                <hr>
    """
    return content


def _render_overview(user):
    stats = get_listening_stats(user)
    return f'''
        <div class='overview-grid'>
        <div><h2>{format(stats['streams'], ',')}</h2><h3>streams</h3></div>
        <div><h2>{format(stats['ms_played']//3600_000, ',')}</h2><h3>hours streamed</h3></div>
        </div>

        <div class='overview-grid'>
        <div><h2>{format(stats['tracks'], ',')}</h2><h3>tracks</h3></div>
        <div><h2>{format(stats['albums'], ',')}</h2><h3>albums</h3></div>
        <div><h2>{format(stats['artists'], ',')}</h2><h3>artists</h3></div>
        </div>
    '''


def _render_profile(user):
    name, _, bio, icon_url = get_profile_content(user)
    return f'''
    <img class="profile-image" src="{icon_url}" width="250" height="250">
    <div class="profile-text">
    <h1 class="title-text">{name}'s Albums</h1>
    <p>{bio}</p>
    </div>
    '''


def fetch_track(id):
    track_url = f'https://api.spotify.com/v1/tracks/{id}'
    headers = {'Authorization': f'Bearer {session.get('token')}'}
    response = requests.get(track_url, headers=headers)
    time.sleep(0.5)
    return response.json()
    
    
if __name__ == '__main__':
   app.run(debug=True)