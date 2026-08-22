from flask import Flask, render_template, redirect, request, jsonify

import os
from dotenv import load_dotenv

import zipfile,json

load_dotenv()
CLIENT_ID = os.environ.get("CLIENT_ID")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET")

app = Flask(__name__)

@app.route('/',methods=['GET'])
def page_name_get(): 
    return """<form action="." method="post" enctype=multipart/form-data>
      <input type="file" accept="application/zip" name="data_zip_file" accept="application/zip" required>
      <button type="submit">Send zip file!</button>
      </form>"""

@app.route('/',methods=['POST'])
def page_name_post():
    file = request.files['data_zip_file']  
    file_like_object = file.stream._file  
    zipfile_ob = zipfile.ZipFile(file_like_object)
    file_names = zipfile_ob.namelist()

    file_start, file_end = 'Spotify Extended Streaming History/Streaming_History_Audio', '.json'
    file_names = [file_name for file_name in file_names if (file_name.startswith(file_start) and file_name.endswith(file_end))]
    files = [
        (json.loads(zipfile_ob.read(name).decode("utf-8")), name)
        for name in file_names
    ]
    return jsonify(files)

@app.route('/callback')
def callback():
   return "<p>Hi</p>"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['username']
        print("POST request!")
        return f"Hello {name}, POST request received"
    if request.method == 'GET':
      print("GET request!")
      return render_template('name.html')

if __name__ == '__main__':
   app.run(debug=True)