from flask import Flask, Response, request, abort, send_file
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

app = Flask(__name__)

# load env file
load_dotenv()

#  Get Credentials
AUTHORIZED_USERS = {
    "user": os.getenv("USER"),
    "password": os.getenv("PASS")
    }

HOST= os.getenv("HOST", "127.0.0.1")
PORT= os.getenv("PORT", 5590)
VIDEO_OUTPUT_FOLDER = os.getenv("VIDEO_OUTPUT_DIR", "video_output")


def verify_authentication():
    """
    Verify the user's credentials from the Authorization header.
    """
    auth = request.authorization
    if not auth:
        print("No Authorization header provided")
        return False
    if auth.username != AUTHORIZED_USERS['user'] or auth.password != AUTHORIZED_USERS['password']:
        return False
    return True



def requires_auth(func):
    """
    Decorator to protect routes with authentication.
    """
    @wraps(func)  # Preserve the original function name and metadata
    def wrapped(*args, **kwargs):
        if not verify_authentication():
            return Response(
                'Unauthorized Access: Authentication Required',
                401,
                {'WWW-Authenticate': 'Basic realm="SensiWatch"'}
            )
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
    return "<h1>Welcome to SensiWatch!</h1><p>Use the appropriate routes to interact with the service.</p>"


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
        output_video.release()  # Release the video writer before download
        return send_file(VIDEO_FILENAME, as_attachment=True)
    except Exception as e:
        return f"Error: {e}", 500

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


# Register the cleanup function to run at exit
atexit.register(cleanup)

if __name__ == "__main__":
    try:
        app.run(host=HOST, port=PORT, debug=True)
    except KeyboardInterrupt:
        print("Shutting down...")