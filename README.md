### Spotify Extended History & Decade Analyser
A full-stack, data-engineered web application built using Python, Flask, and SQLAlchemy that parses, aggregates, and visualises lifelong personal music streaming data. This application processes a local relational database and hydrates missing metadata dynamically via the Spotify Web API. I made this to track what decades I have listened to the most albums from, as well as tracking when I finished listening to an album.

Watch a demonstration [here.](https://www.youtube.com/watch?v=ZAQNj6CZdGI)

### Key Features
- OAuth 2.0 Authentication: Secure user verification directly through Spotify Accounts Service using raw server-side HTTP exchanges.
- Large Dataset Aggregation: High-efficiency SQL grouping that handles 50,000+ data rows at the database layer using SQLAlchemy func.count.
- Analytics Dashboard: Interactive data filtering mapping user listening trends dynamically across days, months, years, and decades. Alternative sorting modes by date of listen and date of release.
- Full CRUD Functionality: Custom visitor profiles with active fields for editable bios, hidden track flags, and record overrides.
- API Rate-Limit Resilience: Throttled network updates featuring autonomous HTTP 429 headers to maintain platform quota compliance.

### The Tech Stack
- Backend: Python 3.13.8, Flask
- Database / ORM: SQLite, SQLAlchemy
- Frontend: HTML5, CSS3, Vanilla JavaScript
- Networking: Python requests library (Native integration without third-party API wrappers)

### How to run the app locally
### 1. Run the following command in the app directory:
```bash
run pip install -r requirements.txt
```
### 2. Developer Dashboard Setup
Create a Developer Application on the [Spotify Developer Dashboard](https://developer.spotify.com/). Register your redirect URI as http://localhost:5000/callback.

### 3. Environment Setup
Create a .env file containing the CLIENT_ID, CLIENT_SECRET, and REDIRECT_URI, as well as a randomly generated SECRET_KEY.

### 4. Initialize and Execute
Run the Flask server locally:
```bash
python app.py
```
Open your browser and navigate to http://localhost:5000 to interact with the environment.
