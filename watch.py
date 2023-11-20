from flask import Flask, Response, send_file
from PIL import ImageGrab
import cv2
import numpy as np
import random as rdm
from datetime import datetime
import string as stg
import argparse
# import ngork

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--interface', default='127.0.0.1', help='Host/Interface on which the service will be hosted on.')
parser.add_argument('-p', '--port', default=9090, help='Port on which the host will be running on.')
args = parser.parse_args()


def new_video_filename():
    '''
    Generate a video filename based using 'VIDEO_' and time called and random ascii character.
    '''
    NEW_VIDEO_FILENAME = 'VIDEO_'
    EXT = '.mp4'
    current_datetime = datetime.now()
    formatted_date = current_datetime.strftime('%Y%m%d%H%M%S')
    rand_str = ''.join(rdm.choices(stg.ascii_letters, k=12))
    return f"{NEW_VIDEO_FILENAME}{formatted_date}_{rand_str}{EXT}"

HOST = args.interface or '127.0.0.1'
PORT = args.port or 9090
VIDEO_FILENAME = new_video_filename() # generate a video file name
print(VIDEO_FILENAME)

# Initialize video writer with 4K resolution
output_video = cv2.VideoWriter(VIDEO_FILENAME, cv2.VideoWriter_fourcc(*'mp4v'), 10, (3840, 2160))  # 4K resolution

app = Flask(__name__) # Flask app for serving screenrecord

def generate_screen_frames():
    '''
    Generate screen record
    '''
    while True:
        screen = ImageGrab.grab()  # Capture the screen
        screen_np = np.array(screen)  # Convert to NumPy array
        _, screen_encoded = cv2.imencode('.jpg', cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR))  # Encode image as JPEG
        frame = screen_encoded.tobytes()

        # Write frame to video file
        output_video.write(cv2.cvtColor(screen_np, cv2.COLOR_RGB2BGR))  # Write frame to video file
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def stream_screen():
    '''
    Stream screen record.
    '''
    return Response(generate_screen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/download_video')
def download_video():
    '''
    Download stream screenrecord.
    '''
    try:
        output_video.release()  # Release the video writer before download
        return send_file(VIDEO_FILENAME, as_attachment=True)
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    # add ngrok tunneling here
    app.run(host=HOST, port=PORT, debug=True)
