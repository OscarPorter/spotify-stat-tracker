import sqlalchemy as db
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship, sessionmaker
from datetime import datetime, date

engine = db.create_engine("sqlite:///stat_tracker.db", echo=False)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    streams: Mapped[list['Stream']] = relationship()

    username = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
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
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)

    album_id: Mapped[int] = mapped_column(db.ForeignKey('albums.id'))
    album: Mapped['Album'] = relationship(back_populates='tracks')

    streams: Mapped[list['Stream']] = relationship()

    artists = relationship('Artist', secondary='track_artists', back_populates='tracks')

    name = db.Column(db.String(255))
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
    
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def seed_data():
    if session.query(User).count() < 1:
        artist1 = Artist(
            name='The Weeknd',
            spotify_id='spotify_artist_1',
            icon_uri='https://example.com/the-weeknd.jpg'
        )
        artist2 = Artist(
            name='Harry Styles',
            spotify_id='spotify_artist_2',
            icon_uri='https://example.com/harry-styles.jpg'
        )
        artist3 = Artist(
            name='Olivia Rodrigo',
            spotify_id='spotify_artist_3',
            icon_uri='https://example.com/olivia-rodrigo.jpg'
        )

        album1 = Album(
            name='After Hours',
            spotify_id='spotify_album_1',
            icon_uri='https://example.com/after-hours.jpg',
            release_date=date(2021,5,21)
        )
        album2 = Album(
            name='Harrys House',
            spotify_id='spotify_album_2',
            icon_uri='https://example.com/as-it-was.jpg',
            release_date=date(2022,5,20)
        )
        album3 = Album(
            name='SOUR',
            spotify_id='spotify_album_3',
            icon_uri='https://example.com/sour.jpg',
            release_date=date(2020,3,20)
        )

        track1 = Track(
            name='Blinding Lights',
            spotify_id='spotify_track_1',
            album=album1
        )
        track2 = Track(
            name='As It Was',
            spotify_id='spotify_track_2',
            album=album2
        )
        track3 = Track(
            name='Good 4 U',
            spotify_id='spotify_track_3',
            album=album3
        )

        user1 = User(
            username='john_doe',
            email='john@example.com',
            spotify_id='spotify_user_1'
        )
        user2 = User(
            username='jane_smith',
            email='jane@example.com',
            spotify_id='spotify_user_2'
        )
        user3 = User(
            username='alex_morgan',
            email='alex@example.com',
            spotify_id='spotify_user_3'
        )

        stream1 = Stream(
            user=user1,
            track=track1,
            timestamp=datetime(2019, 7, 14, 22, 45, 30),
            ms_played=180000,
            platform='Spotify',
            country='US',
            skipped=False,
            reason_start='trackdone',
            reason_end='trackdone',
            incognito_mode=False
        )
        stream2 = Stream(
            user=user2,
            track=track2,
            timestamp=datetime(2024, 1, 16, 9, 45, 0),
            ms_played=240000,
            platform='Web Player',
            country='GB',
            skipped=True,
            reason_start='fwdbtn',
            reason_end='trackdone',
            incognito_mode=True
        )
        stream3 = Stream(
            user=user2,
            track=track3,
            timestamp=datetime(2025, 1, 16, 9, 45, 0),
            ms_played=185410,
            platform='Web Player',
            country='GB',
            skipped=True,
            reason_start='fwdbtn',
            reason_end='trackdone',
            incognito_mode=True
        )
        stream4 = Stream(
            user=user3,
            track=track1,
            timestamp=datetime(2025, 2, 3, 18, 20, 0),
            ms_played=210000,
            platform='Mobile',
            country='CA',
            skipped=False,
            reason_start='playbtn',
            reason_end='trackdone',
            incognito_mode=False
        )
        stream5 = Stream(
            user=user3,
            track=track2,
            timestamp=datetime(2025, 2, 4, 7, 15, 0),
            ms_played=95000,
            platform='Spotify',
            country='CA',
            skipped=True,
            reason_start='trackdone',
            reason_end='fwdbtn',
            incognito_mode=False
        )

        user1.streams.extend([stream1])
        user2.streams.extend([stream2, stream3])
        user3.streams.extend([stream4, stream5])

        session.add_all([
            user1, user2, user3,
            artist1, artist2, artist3,
            album1, album2, album3,
            track1, track2, track3,
            stream1, stream2, stream3, stream4, stream5
        ])
        session.flush()

        track_artist1 = TrackArtists(track_id=track1.id, artist_id=artist1.id)
        track_artist2 = TrackArtists(track_id=track2.id, artist_id=artist2.id)
        track_artist3 = TrackArtists(track_id=track3.id, artist_id=artist3.id)
        album_artist1 = AlbumArtists(album_id=album1.id, artist_id=artist1.id)
        album_artist2 = AlbumArtists(album_id=album2.id, artist_id=artist2.id)
        album_artist3 = AlbumArtists(album_id=album3.id, artist_id=artist3.id)

        session.add_all([
            track_artist1, track_artist2, track_artist3,
            album_artist1, album_artist2, album_artist3
        ])
        session.commit()

    if not session.query(Track).filter_by(spotify_id='spotify_track_4').first():
        gorillaz = Artist(
            name='Gorillaz',
            spotify_id='spotify_artist_4',
            icon_uri='https://example.com/gorillaz.jpg'
        )
        mf_doom = Artist(
            name='MF DOOM',
            spotify_id='spotify_artist_5',
            icon_uri='https://example.com/mf-doom.jpg'
        )
        demon_days = Album(
            name='Demon Days',
            spotify_id='spotify_album_4',
            icon_uri='https://example.com/demon-days.jpg',
            release_date=date(2005, 5, 23)
        )
        november_has_come = Track(
            name='November Has Come',
            spotify_id='spotify_track_4',
            album=demon_days
        )
        example_stream = Stream(
            user=session.query(User).first(),
            track=november_has_come,
            timestamp=datetime(2025, 2, 5, 20, 30, 0),
            ms_played=160000,
            platform='Spotify',
            country='US',
            skipped=False,
            reason_start='playbtn',
            reason_end='trackdone',
            incognito_mode=False
        )

        session.add_all([gorillaz, mf_doom, demon_days, november_has_come, example_stream])
        session.flush()
        session.add_all([
            TrackArtists(track_id=november_has_come.id, artist_id=gorillaz.id),
            TrackArtists(track_id=november_has_come.id, artist_id=mf_doom.id),
            AlbumArtists(album_id=demon_days.id, artist_id=gorillaz.id)
        ])
        session.commit()

seed_data()


user2 = session.query(User).offset(1).first()

album = (
    session.query(Album)
    .filter_by(name='Demon Days')
    .first()
)

print(f'User 2s first stream!: {user2.streams[0].track.name} from {user2.streams[0].track.album.name} released on {user2.streams[0].track.album.release_date.strftime('%d %B %Y')} by {user2.streams[0].track.artists[0].name}')

print(f'{album.artists[0].name}')
print(f'{[artist.name for artist in album.tracks[0].artists]}')