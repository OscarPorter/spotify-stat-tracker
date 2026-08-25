from flask import Flask, render_template, redirect, request, jsonify

import os
from dotenv import load_dotenv

import json

from models import import_listen_history, init_db

load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

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

if __name__ == '__main__':
   app.run(debug=True)