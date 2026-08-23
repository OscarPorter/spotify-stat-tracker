import sqlalchemy as db
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship, sessionmaker
from datetime import datetime

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
    user: Mapped["User"] = relationship(back_populates='streams')
    #track_id = db.Column(db.Integer, db.ForeignKey('tracks.id'), nullable=False, index=True)

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
    #album_id

    name = db.Column(db.String(255))
    spotify_id = db.Column(db.String(255), unique=True)


class Album(Base):
    __tablename__ = 'albums'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255))
    spotify_id = db.Column(db.String(255), unique=True)
    icon = db.Column(db.String(255))


class Artist(Base):
    __tablename__ = 'artists'

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(255))
    spotify_id = db.Column(db.String(255), unique=True)
    icon = db.Column(db.String(255))

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()

def seed_data():
    if session.query(User).count() < 1:
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

        stream1 = Stream(
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
            timestamp=datetime(2025, 1, 16, 9, 45, 0),
            ms_played=185410,
            platform='Web Player',
            country='GB',
            skipped=True,
            reason_start='fwdbtn',
            reason_end='trackdone',
            incognito_mode=True
        )

        user1.streams.extend([stream1])
        user2.streams.extend([stream2,stream3])
        session.add_all([user1, user2, stream1, stream2, stream3])
        session.commit()

seed_data()

stream1 = session.query(Stream).first()
user1, user2 = session.query(User).limit(2).all()

print(f'stream1:  {stream1.user.username}')
print(f'user1:    {user1.streams = }')
print(f'user2:    {user2.streams = }')
print(f'country:  {user2.streams[0].country}')