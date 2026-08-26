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
    release_date = db.Column(db.Date)
    icon_uri = db.Column(db.String(255))
    spotify_id = db.Column(db.String(255), unique=True)

class Artist(Base):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)

    tracks = relationship('Track', secondary='track_artists', back_populates='artists')
    albums = relationship('Album', secondary='album_artists', back_populates='artists')

    name = db.Column(db.String(255))
    icon_uri = db.Column(db.String(255))
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

def update_track(data,spotify_id):
    with Session.begin() as session:
        pass
        
        

def create_test_user():
    with Session.begin() as session:
        user = session.query(User).filter(
            User.id == 1
        ).first()

        if not user:
            user_entry = User(
                username = 'Test User',
                spotify_id = 'testid12345'            
            )
            session.add(user_entry)