'''
S3ns1W47ch
BORED AND OUT MY MIND, THEN I WROTE A SIMPLE SCRIPT TO WATCH WHAT'S HAPPENING ON MY PC FROM MY PHONE OR OTHER COMPUTERS AT HOME!
USE FOR GOOD ONLY! REMEMBER GOD IS WATCHING YOU;
ONLY FOR EDUCATIONAL PURPOSE ONLY

DEVELOPER: SHEPHERDDOMAIN (aka. SteveSplash)

CONTACTS: {
    'GitHub': 'https://github.com/stevesplash934/',
    'Gmail': 'stevesplash4@gmail.com',
    'Facecbook': 'https://facebook.com/steve.splash.10'
}
'''

from flask import Flask, Response, send_file, render_template
from PIL import ImageGrab
import cv2
import numpy as np
import random as rdm
from datetime import datetime
import string as stg
import argparse
import ngrok

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--interface', default='127.0.0.1', help='Host/Interface on which the service will be hosted on.')
parser.add_argument('-p', '--port', default=9090, help='Port on which the host will be running on.')
parser.add_argument('-ng', '--ngrok', help='Enable ngrok tunneling, pass your authkey or else ngrok won\'t work')
args = parser.parse_args()

if args.ngrok and args.ngrok == '':
    print('NGROK authkey missing! Quitting program.')
    exit()

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
HTML_S_URL = f'http://{HOST}:{PORT}'
HTML_TITLE = f'{HTML_S_URL} DISPLAY'
HTML_VIEW = f"""
<!DOCTYPE html>
<html lang='en'>
<head>
    <meta charset='UTF-8'>
    <meta name='viewport' content='width=device-width, initial-scale=1.0'>
    <title>{HTML_TITLE}</title>
    <style>
        html{{
            font-size: 100%;
        }}
        *{{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body{{
            max-width: 100vw;
            width: 100vw;
            min-width: 100vw;
            max-height: 100vh;
            height: 100vh;
            min-height: 100vh;
            background-color: #030303;
            color: white;
        }}
        #sensi-label{{
            width: 100%;
            height: fit-content;
            padding: 10px;
            background-color: green;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: calc(0.2rem + 36px);
            font-weight: bold;
            flex-direction: row;
            font-family: verdana;
        }}
        .footer{{
            width: 100%;
            height: fit-content;
            position: fixed;
            bottom: 0;
            left: 0;
            padding: 10px;
            background-color: green;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: calc(0.065rem + 20px);
            font-weight: bold;
            font-family: verdana;
        }}
        #render-viewer{{
            margin-top: 30px;
            margin-bottom: 30px;
            width: 100%;
        }}
        #render-frame>iframe{{
            width: 100%;
            background-color: #fff;
        }}
        .control-panel{{
            width: 100%;
            margin-top: 10px;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .control-panel ul{{
            list-style: none;
        }}
        .control-panel ul li{{
            display: inline;
            padding: 10px;
        }}
        .control-panel ul li a{{
            background-color: green;
            font: 16px verdana;
            text-decoration: none;
            border: none;
            border-radius: 5px;
            padding: 3px;
            color: #030303;
            font-weight: bold;
        }}
        .control-panel ul li a:hover{{
            background-color: lightblue;
        }}
    </style>
</head>
<body>
    <div class='sensi-label' id='sensi-label'>
        SensiWatch
    </div>
     <div class='control-panel'>
        <ul>
            <li><a href='{HTML_S_URL}/disconnect'>DISCONNECT</a></li>
            <li><a href='{HTML_S_URL}/download_video'>SAVE VIDEO</a></li>
            <li><a href='{HTML_S_URL}/about'>ABOUT</a></li>
            <li><a href='{HTML_S_URL}/help'>HELP</a></li>
        </ul>
    </div>
        <iframe src='{HTML_S_URL}/get_screen_view' frameborder='5' id='view_renderr' style='width: 100%; height:85vh;'></iframe>
        <iframe frameborder='5' id='hidden_view_renderr' style='width: 100%; height:85vh; display:none;'></iframe>
    <div class='footer'>
        &copy; - SensiWatch @ ShepherdDomain
    </div>
    <script>
    setInterval(function(){{
      mainFrame = document.getElementById('view_renderr');
      hiddenFrame = document.getElementById('hidden_view_renderr');
      hiddenFrame.src = mainFrame.src;
      hiddenFrame.onload = function(){{
       mainFrame.src = hiddenFrame.src;
      }}
        }}, 1000);
    </script>
</body>
</html>
"""
if args.ngrok:
    AUTHTOKEN = args.ngrok
    
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
def index():
    """
    Parse the index.html file and let the iframe inside call the get screen view
    """
    # generate index.html
    with open('templates/render.html', 'w') as html_render_file:
        html_render_file.write(HTML_VIEW)
        
    # render index.html view
    return render_template('render.html')
    
@app.route('/get_screen_view')
def return_iframe():
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
    if args.ngrok:
        try:
            listener = ngrok.connect(PORT, authtoken=AUTHTOKEN)
            print (f"Loopback URL established at: {listener.url()}")
        except Exception as e:
            print(e)
    app.run(host=HOST, port=PORT)
