import base64
import datetime
import os
import cv2
import numpy as np
from flask import Flask, request, jsonify, redirect, render_template,  session
import bcrypt
import string
import secrets
import face_recognition
import pickle
import json

camera = cv2.VideoCapture(0)
app = Flask(__name__)
app.config['SECRET_KEY'] = ''.join(secrets.choice(
    string.ascii_letters + string.digits) for _ in range(10))
app.config['UPLOAD_FOLDER'] = 'static/img'


# Create the users table if it doesn't exist
if not os.path.isfile(r'static\data.json'):
    data = {}
    with open(r'static\data.json', "w") as f:
        # write the python object as a json string
        json.dump(data, f)






@app.route("/signup", methods=['GET', 'POST'])
def signup():

    if request.method == 'POST':
        # Get the user input
        name = request.form['name']
        email = request.form['email']
        gender = request.form['gender']
        password = request.form['password'].encode('utf-8')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
        gender = request.form['gender']
        if name and gender and email and password:
            with open(r'static\data.json', 'r') as f:
                data = json.load(f)
            data[session.get("master_key")] = {
                'name': name, 'gender':gender,'email': email, 'password': hashed_password.decode('utf-8')}
            with open(r'static\data.json', "w") as f:
                json.dump(data, f)
            return redirect('/generated-master-key')
        else:
            return redirect('/signup')
    return render_template('register.html')


@app.route("/generated-master-key", methods=['GET', 'POST'])
def show_master_key():

    if request.method == 'POST':
        return redirect('/')
    return render_template('show_masterkey.html', mk=session.get("master_key"))


@app.route("/face-detection", methods=['GET', 'POST'])
def face_detection():
    return render_template("face_capture.html")


@app.route('/capture', methods=['POST'])
def capture():
    if not os.path.isfile(r'static\faces.pkl'):
        with open(r'static\faces.pkl', 'wb') as file:
            pickle.dump({'names': [], 'encodings': []}, file)
    with open(r'static\faces.pkl', 'rb') as f:
        data = pickle.load(f)
    encodings = data['encodings']
    names = data['names']
    # Capture image from data URL
    imageData = request.get_json()['image']

    imageData = imageData.replace('data:image/png;base64,', '')
    imageData = imageData.encode()
    nparr = np.frombuffer(base64.decodebytes(imageData), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    # Detect faces in image
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb)
    # Check that exactly one face was detected
    if len(face_locations) != 1:
        return jsonify({'status': 'error', 'message': 'Please capture an image with exactly one face.'})
    # Save image to file
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    cv2.imwrite(os.path.join(
        app.config['UPLOAD_FOLDER'], 'captured_image.png'), img)
    if recognize(r"static\img\captured_image.png") == 'Unknown':
        face_enc = face_recognition.face_encodings(rgb)[0]
        encodings.append(face_enc)
        master_key = ''.join(secrets.choice(
            string.ascii_letters + string.digits) for i in range(10))
        session['master_key'] = master_key
        names.append(master_key)
        with open(r'static\faces.pkl', 'wb') as f:
            pickle.dump({'names': names, 'encodings': encodings}, f)
        # Redirect to success page
        return jsonify({'status': 'success', 'message': 'Successfully Captured Image'})
    else:
        return jsonify({'status': 'member', 'message': 'Already Registered'})


def recognize(img):
    if not os.path.isfile(r'static\faces.pkl'):
        return 'File Not Exist'
    with open(r'static\faces.pkl', 'rb') as f:
        data = pickle.load(f)
    img = face_recognition.load_image_file(img)

    known_face_encodings = data['encodings']
    known_face_names = data['names']
    if not known_face_encodings or not known_face_encodings:
        name = "Unknown"
    else:
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb)
        if len(face_locations) != 1:
            return 'More than one face or no face'
        rgb_enc = face_recognition.face_encodings(rgb)[0]
        matches = face_recognition.compare_faces(known_face_encodings, rgb_enc)
        name = "Unknown"
        face_distances = face_recognition.face_distance(
            known_face_encodings, rgb_enc)
        best_match_index = np.argmin(face_distances)
        if matches[best_match_index]:
            name = known_face_names[best_match_index]
            session['master_key'] = name

    return name


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    # Clear session variables
    session.pop('master_key', None)
    # Redirect to login page
    return redirect('/face-detection')


@app.route("/login", methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        cmp_mk = session.get("master_key")
        master_key = request.form['master-key']
        print(cmp_mk, master_key)
        if master_key == cmp_mk:
            return redirect('/')
    return render_template("login.html")


@app.route("/", methods=['GET', 'POST'])
def home():
    if 'master_key' in session:
        with open(r'static\data.json') as f:
            data = json.load(f)
            name = data[session.get("master_key")]['name']
            with open(r'static\post.json', 'r') as f:
                data = json.load(f)
        return render_template("home.html", name=name,posts=data)
    else:
        # Redirect to login page
        return redirect('/face-detection')
    
@app.route("/post", methods=['GET', 'POST'])
def post():
    if not os.path.isfile(r'static\post.json'):
        data = {}
        with open(r'static\post.json', "w") as f:
            # write the python object as a json string
            json.dump(data, f)
    if request.method == 'POST':
        # Get the user input
        text = request.form['text']
        location = request.form['location']
        current_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(r'static\data.json') as f:
            data = json.load(f)
        name = data[session.get("master_key")]['name']
        email = data[session.get("master_key")]['email']
        with open(r'static\post.json', 'r') as f:
            data = json.load(f)
        data[current_datetime] = {
            'name': name, 'email': email, 'text': text,'location': location}
        with open(r'static\post.json', "w") as f:
            json.dump(data, f)
        return redirect('/')

@app.route('/profile',methods=['GET','POST'])
def profile():
    with open(r'static\data.json') as f:
        data=json.load(f)
    info=data[session.get("master_key")]
    return render_template('profile.html', info=info)
    


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
