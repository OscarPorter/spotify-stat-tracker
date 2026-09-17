import sqlalchemy as db
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship, sessionmaker, contains_eager, joinedload
from datetime import datetime, date
from itertools import groupby

import secrets
import string

ALLOWED = string.ascii_letters + string.digits

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    streams = relationship('Stream', back_populates='user')
    album_overrides = relationship('AlbumOverride', back_populates='user')

    spotify_id = db.Column(db.String(255), unique=True)
    spotify_display_name = db.Column(db.String(255))
    spotify_icon_url = db.Column(db.String(255))

    custom_url = db.Column(db.String(30), unique=True)
    bio = db.Column(db.String(512))


class Stream(Base):
    __tablename__ = 'streams'

    id = db.Column(db.Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'))
    user: Mapped['User'] = relationship(back_populates='streams')
    
    track_id: Mapped[int] = mapped_column(db.ForeignKey('tracks.id'))
    track: Mapped['Track'] = relationship(back_populates='streams')

    timestamp = db.Column(db.DateTime)
    ms_played = db.Column(db.Integer)
    platform = db.Column(db.String(50))
    country = db.Column(db.String(2))
    skipped = db.Column(db.Boolean)
    reason_start = db.Column(db.String(50))
    reason_end = db.Column(db.String(50))
    incognito_mode = db.Column(db.Boolean)


class Track(Base):
    # Largely nullable - except for ID and Spotify ID. The rest will be filled out after the Spotify API calls.
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)

    album_id: Mapped[int] = mapped_column(db.ForeignKey('albums.id'))
    album: Mapped['Album'] = relationship(back_populates='tracks')

    streams: Mapped[list['Stream']] = relationship()

    artists = relationship('Artist', secondary='track_artists', back_populates='tracks')

    name = db.Column(db.String(255))
    duration_ms = db.Column(db.Integer)
    disc_number = db.Column(db.Integer)
    track_number = db.Column(db.Integer)
    explicit = db.Column(db.Boolean)
    spotify_id = db.Column(db.String(255), unique=True)


class Album(Base):
    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)

    tracks: Mapped[list['Track']] = relationship()

    artists = relationship('Artist', secondary='album_artists', back_populates='albums')

    name = db.Column(db.String(255))
    album_type = db.Column(db.String(50))
    total_tracks = db.Column(db.Integer)
    release_date = db.Column(db.Date)
    icon_uri = db.Column(db.String(255))
    spotify_id = db.Column(db.String(255), unique=True)

    album_overrides = relationship('AlbumOverride', back_populates='album')


class Artist(Base):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)

    tracks = relationship('Track', secondary='track_artists', back_populates='artists')
    albums = relationship('Album', secondary='album_artists', back_populates='artists')

    name = db.Column(db.String(255))
    spotify_id = db.Column(db.String(255), unique=True)


class TrackArtists(Base):
    __tablename__ = 'track_artists'

    id = db.Column(db.Integer, primary_key=True)

    track_id = db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'))
    artist_id = db.Column('artist_id', db.Integer, db.ForeignKey('artists.id'))


class AlbumArtists(Base):
    __tablename__ = 'album_artists'

    id = db.Column(db.Integer, primary_key=True)

    album_id = db.Column('album_id', db.Integer, db.ForeignKey('albums.id'))
    artist_id = db.Column('artist_id', db.Integer, db.ForeignKey('artists.id'))


class AlbumOverride(Base):
    __tablename__ = 'album_overrides'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    album_id = db.Column(db.Integer, db.ForeignKey('albums.id'))

    user = relationship('User', back_populates='album_overrides')
    album = relationship('Album', back_populates='album_overrides')

    release_date = db.Column(db.Date)
    completion_date = db.Column(db.DateTime)
    hidden = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'album_id', name='uq_user_album_override'),
    )

engine = db.create_engine("sqlite:///stat_tracker.db", echo=False)

Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)
    album_columns = {column['name'] for column in db.inspect(engine).get_columns('albums')}


def import_listen_history(data, user_id):
    with Session.begin() as session:
        session.query(Stream).filter(Stream.user_id == user_id).delete(
            synchronize_session=False
        )
        
        for history_file in data:
            for stream in history_file:

                required_keys = (
                    'spotify_track_uri', 'ts', 'ms_played', 'platform',
                    'conn_country', 'skipped', 'reason_start', 'reason_end',
                    'incognito_mode'
                )
                if any(
                    key not in stream or stream[key] is None
                    for key in required_keys
                ):
                    continue

                spotify_id = str(stream['spotify_track_uri']).rsplit(':')[-1]
                if not spotify_id:
                    continue

                # Check if track exists. If it doesn't, add the Spotify ID to the Tracks table.
                track = session.query(Track).filter(
                    Track.spotify_id == spotify_id
                ).first()

                if not track:
                    track = Track(spotify_id=spotify_id)
                    session.add(track)
                    session.flush()

                stream_entry = Stream(
                user_id=user_id,
                track_id=track.id,
                timestamp=datetime.fromisoformat(stream['ts']),
                ms_played=stream['ms_played'],
                platform=stream['platform'],
                country=stream['conn_country'],
                skipped=stream['skipped'],
                reason_start=stream['reason_start'],
                reason_end=stream['reason_end'],
                incognito_mode=stream['incognito_mode']
                )
                session.add(stream_entry)


def generate_unique_custom_url(session, length=30):
    while True:
        code = ''.join(secrets.choice(ALLOWED) for _ in range(length))
        existing = session.query(User).filter(User.custom_url == code).first()
        if not existing:
            return code


def spotify_login(data):
    with Session.begin() as session:
        user = session.query(User).filter(User.spotify_id == data['account_id']).first()
        if user:
            user.spotify_display_name = data['display_name']
            user.spotify_icon_url = data['images'][0]['url']
            return user.id
        
        user = User(
            spotify_id = data['account_id'],
            spotify_display_name = data['display_name'],
            spotify_icon_url = data['images'][0]['url'],
            custom_url = generate_unique_custom_url(session, 30),
            bio = None
        )

        session.add(user)
        session.flush()
        return user.id


def update_profile_content(user_id, custom_url, bio):
    with Session.begin() as session:
        user = session.query(User).filter(User.id == user_id).first()
        user.custom_url = custom_url
        user.bio = bio


def get_profile_content(user_id):
    with Session.begin() as session:
        user = session.query(User).filter(User.id == user_id).first()
        return user.spotify_display_name, user.custom_url, user.bio, user.spotify_icon_url


def url_to_id(url):
    with Session.begin() as session:
        user = session.query(User).filter(User.custom_url == url).first()
        return user.id


def id_to_url(id):
    with Session.begin() as session:
        user = session.query(User).filter(User.id == id).first()
        return user.custom_url


def delete_account(user_id):
    with Session.begin() as session:
        session.query(Stream).filter(Stream.user_id == user_id).delete(
            synchronize_session=False
        )
        user = session.query(User).filter(User.id == user_id).first()
        if user:
            session.delete(user)


def parse_release_date(value):
    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def get_or_create_album(session, album_data):
    if not album_data or not album_data.get('id'):
        return None

    album = session.query(Album).filter(Album.spotify_id == album_data['id']).first()
    if not album:
        album = Album(spotify_id=album_data['id'])
        session.add(album)
        session.flush()

    album.name = album_data.get('name') or album.name
    album.album_type = album_data.get('album_type') or album.album_type
    album.total_tracks = album_data.get('total_tracks') or album.total_tracks
    album.release_date = parse_release_date(album_data.get('release_date')) or album.release_date

    images = album_data.get('images') or []
    if images and images[0].get('url'):
        album.icon_uri = images[0]['url']

    return album


def get_or_create_artist(session, artist_data):
    spotify_id = artist_data.get('id')
    if not spotify_id:
        return None

    artist = session.query(Artist).filter(Artist.spotify_id == spotify_id).first()
    if not artist:
        artist = Artist(spotify_id=spotify_id)
        session.add(artist)
        session.flush()

    artist.name = artist_data.get('name') or artist.name

    images = artist_data.get('images') or []
    if images and images[0].get('url'):
        artist.icon_uri = images[0]['url']

    return artist


def fetch_all_missing_data(fetch_track):
    with Session() as session:
        tracks = session.query(Track.id, Track.spotify_id).filter(
            db.or_(
                Track.name.is_(None),
                Track.duration_ms.is_(None),
                Track.album_id.is_(None),
                Track.disc_number.is_(None),
                Track.track_number.is_(None),
                Track.explicit.is_(None)
            )
        ).all()

    for track_id, spotify_id in tracks:
        with Session.begin() as track_session:
            track_record = track_session.query(Track).filter_by(id=track_id).one()

            track_data = dict(fetch_track(spotify_id)) # Explicit dict typing for type hints

            if 'error' in track_data:
                status = track_data['error']['status']
                if status in (401, 403):
                    raise Exception('Bad/expired token or bad OAuth request.')
                elif status == 429:
                    raise Exception('The app has exceeded its rate limits.')
                continue
            else:
                print('Track successfully fetched!')

            track_record.name = track_data.get('name', track_record.name)
            track_record.duration_ms = track_data.get('duration_ms', track_record.duration_ms)
            track_record.disc_number = track_data.get('disc_number', track_record.disc_number)
            track_record.track_number = track_data.get('track_number', track_record.track_number)
            track_record.explicit = track_data.get('explicit', track_record.explicit)

            album_data = track_data.get('album')
            if album_data:
                album = get_or_create_album(track_session, album_data)
                if album:
                    track_record.album_id = album.id

                    for artist_data in album_data.get('artists', []):
                        artist = get_or_create_artist(track_session, artist_data)
                        if artist and not track_session.query(AlbumArtists).filter_by(
                            album_id=album.id,
                            artist_id=artist.id
                        ).first():
                            track_session.add(AlbumArtists(album_id=album.id, artist_id=artist.id))
                            track_session.flush()

            for artist_data in track_data.get('artists', []):
                artist = get_or_create_artist(track_session, artist_data)
                if artist and not track_session.query(TrackArtists).filter_by(
                    track_id=track_record.id,
                    artist_id=artist.id
                ).first():
                    track_session.add(TrackArtists(track_id=track_record.id, artist_id=artist.id))
                    track_session.flush()

            track_session.flush()


def get_first_listens(session, user_id):
    first_listens = (
        session.query(
            Track.album_id.label('album_id'),
            Track.id.label('track_id'),
            db.func.min(Stream.timestamp).label('first_listened_at')
        )
        .join(Stream, Stream.track_id == Track.id)
        .filter(
            Stream.user_id == user_id,
            db.or_(
                    Stream.ms_played >= 30_000,
                    Stream.ms_played >= Track.duration_ms // 2
                )
        )
        .group_by(Track.album_id, Track.id)
        .subquery()
        )
    return first_listens


def get_album_completion_dates(session, user_id):
    first_listens = get_first_listens(session, user_id)

    return (
        session.query(
            first_listens.c.album_id,
            db.func.max(first_listens.c.first_listened_at).label('completed_at'),
            db.func.count(first_listens.c.track_id).label('listened_tracks')
        )
        .group_by(first_listens.c.album_id)
        .subquery()
    )


def get_album_overrides(session, user_id):
    return (
        session.query(
            AlbumOverride.album_id,
            AlbumOverride.release_date.label('override_release_date'),
            AlbumOverride.completion_date.label('override_completion_date'),
            AlbumOverride.hidden.label('override_hidden')
        )
        .filter(AlbumOverride.user_id == user_id)
        .subquery()
    )


def get_completed_albums(user_id, sort_by='release_date'):
    with Session() as session:
        completion_dates = get_album_completion_dates(session, user_id)
        overrides = get_album_overrides(session, user_id)

        effective_release_date = db.func.coalesce(
            overrides.c.override_release_date,
            Album.release_date
        )
        effective_completion_date = db.func.coalesce(
            overrides.c.override_completion_date,
            completion_dates.c.completed_at
        )

        sort_columns = {
            'release_date': effective_release_date,
            'completion_date': effective_completion_date,
        }
        order_column = sort_columns.get(sort_by, effective_release_date)

        return (
            session.query(
                Album,
                effective_completion_date.label('completed_at'),
                effective_release_date.label('effective_release_date')
            )
            .outerjoin(overrides, overrides.c.album_id == Album.id)
            .join(completion_dates, completion_dates.c.album_id == Album.id)
            .join(Album.artists)
            .options(contains_eager(Album.artists))
            .filter(
                Album.total_tracks.is_not(None),
                db.or_(
                    completion_dates.c.listened_tracks >= Album.total_tracks,
                    completion_dates.c.listened_tracks >= 5,
                ),
                Album.album_type.is_not('single'),
                db.or_(
                    overrides.c.override_hidden.is_(None),
                    overrides.c.override_hidden.is_(False)
                )
            )
            .order_by(order_column)
            .all()
        )


def get_total_ms_played(user_id):
    with Session() as session:
        total_ms = (
            session.query(db.func.sum(Stream.ms_played))
            .filter(Stream.user_id == user_id)
            .scalar()
        )
        return total_ms or 0


def get_total_streams(user_id):
    with Session() as session:
        total_ms = (
            session.query(db.func.count(Stream.id))
            .filter(Stream.user_id == user_id)
            .scalar()
        )
        return total_ms or 0


def get_total_albums(user_id):
    return len(get_completed_albums(user_id))


def get_total_artists(user_id):
    completed = get_completed_albums(user_id)
    artist_names = set()

    for album, _, _ in completed:
        for artist in album.artists:
            if artist.name:
                artist_names.add(artist.name)

    return len(artist_names)


def get_total_tracks(user_id):
    with Session() as session:
        first_listens = get_first_listens(session, user_id)
        total = (
            session.query(db.func.count(first_listens.c.track_id))
            .select_from(first_listens)
            .scalar()
        )
        return total or 0
    

def get_listening_stats(user_id):
    return {
        'ms_played': get_total_ms_played(user_id),
        'streams': get_total_streams(user_id),
        'albums': get_total_albums(user_id),
        'tracks': get_total_tracks(user_id),
        'artists': get_total_artists(user_id)
    }


def add_override(user_id, album_id):
    with Session.begin() as session:
        override = AlbumOverride(
            user_id = user_id,
            album_id = album_id
        )
        session.add(override)


def edit_override(override_id, release_date=None, completion_date=None, hidden=False):
    with Session.begin() as session:
        override = session.query(AlbumOverride).filter(AlbumOverride.id == override_id).first()
        override.release_date = release_date
        override.completion_date = completion_date
        override.hidden = hidden


def get_overrides(user_id):
    with Session() as session:
        return session.query(AlbumOverride).filter(
            AlbumOverride.user_id == user_id
        ).options(
            joinedload(AlbumOverride.album)
        ).all()


def delete_override(override_id):
    with Session.begin() as session:
        user = session.query(AlbumOverride).filter(AlbumOverride.id == override_id).first()
        if user:
            session.delete(user)
        
