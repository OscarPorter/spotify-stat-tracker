import sqlalchemy as db
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship, sessionmaker
from datetime import datetime, date

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    streams: Mapped[list['Stream']] = relationship()

    username = db.Column(db.String(255), unique=True)
    spotify_id = db.Column(db.String(255), unique=True)

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

    album_id: Mapped[int] = mapped_column(db.ForeignKey('albums.id'), nullable=True)
    album: Mapped['Album'] = relationship(back_populates='tracks')

    streams: Mapped[list['Stream']] = relationship()

    artists = relationship('Artist', secondary='track_artists', back_populates='tracks')

    name = db.Column(db.String(255), nullable=True)
    disc_number = db.Column(db.Integer, nullable=True)
    track_number = db.Column(db.Integer, nullable=True)
    spotify_id = db.Column(db.String(255), unique=True)

class Album(Base):
    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)

    tracks: Mapped[list['Track']] = relationship()

    artists = relationship('Artist', secondary='album_artists', back_populates='albums')

    name = db.Column(db.String(255))
    album_type = db.Column(db.String(50), nullable=True)
    release_date = db.Column(db.Date)
    icon_uri = db.Column(db.String(255))
    spotify_id = db.Column(db.String(255), unique=True)

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

engine = db.create_engine("sqlite:///stat_tracker.db", echo=False)

Session = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)
    album_columns = {column['name'] for column in db.inspect(engine).get_columns('albums')}
    if 'album_type' not in album_columns:
        with engine.begin() as connection:
            connection.execute(db.text(
                'ALTER TABLE albums ADD COLUMN album_type VARCHAR(50)'
            ))

def import_listen_history(data,user_id=1):
    with Session.begin() as session:
        for history_file in data:
            for stream in history_file:

                spotify_id = str(stream['spotify_track_uri']).rsplit(':')[-1]

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
                Track.album_id.is_(None),
                Track.disc_number.is_(None),
                Track.track_number.is_(None),
            )
        ).all()

    for track_id, spotify_id in tracks:
        with Session.begin() as track_session:
            track_record = track_session.query(Track).filter_by(id=track_id).one()

            track_data = dict(fetch_track(spotify_id)) # Explicit dict typing for type hints

            if 'error' in track_data:
                status = track_data['error']['status']
                print('Track successfully fetched!')
                if status in (401, 403):
                    raise Exception('Bad/expired token or bad OAuth request.')
                elif status == 429:
                    raise Exception('The app has exceeded its rate limits.')
                continue
            else:
                print('Track successfully fetched!')

            track_record.name = track_data.get('name') or track_record.name
            track_record.disc_number = track_data.get('disc_number', track_record.disc_number)
            track_record.track_number = track_data.get('track_number', track_record.track_number)

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
