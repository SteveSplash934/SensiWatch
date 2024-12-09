# SensiWatch

**Remote Screen Monitoring Tool**

SensiWatch is a lightweight screen monitoring tool designed for educational purposes, remote assistance, or internal use within a secure network. It allows users to view and record screen activities remotely in real time.

---

### Features

- **Real-Time Streaming**: Stream desktop activity securely over a local network.
- **Recording Option**: Save the screen activity as a 4K video file for later review.
- **Telegram Notifications**: Option to receive updates via Telegram for specific events.

---

### Known Issues

- **Downloading Recordings**: The download functionality is under maintenance and will be updated soon.

### Fixed

- NGROK fixed

Stay tuned for updates in upcoming releases!

---

### Installation

Follow these steps to set up and run SensiWatch:

1. **Clone the Repository**

   ```bash
   git clone https://github.com/stevesplash934/SensiWatch.git
   cd SensiWatch
   ```

2. **Set Up a Virtual Environment (Optional)**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**  
   Copy the `.sample.env` file to `.env` and fill in the necessary details:

   ```bash
   cp .sample.env .env
   ```

   Update the `.env` file:

   - `HOST`: IP address of the host server (default: `127.0.0.1`).
   - `PORT`: Port for the server to run on (default: `9091`).
   - `USER`: Username for authentication (default: `admin`).
   - `PASS`: Password for authentication (default: `password`).
   - `VIDEO_OUTPUT_DIR`: Directory to save recorded videos (default: `vids`).
   - `NGROK_TOKEN`: Your ngrok authentication token (leave blank if not using ngrok).
   - `TELEGRAM_CHATID`: Your Telegram chat ID (optional for Telegram notifications).
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token (optional for Telegram notifications).

5. **Run the Application**

   ```bash
   python main.py
   ```

6. **Access the Tool**
   - Open a web browser and navigate to:  
     `http://<HOST>:<PORT>`  
     (e.g., `http://127.0.0.1:9091`)

---

### .env Sample File

```env
HOST=127.0.0.1
PORT=9091
USER=admin
PASS=password
VIDEO_OUTPUT_DIR="vids"
NGROK_TOKEN=
TELEGRAM_CHATID=
TELEGRAM_BOT_TOKEN=
```

---

### Legal Disclaimer

This tool is for authorized use only. Unauthorized use of this tool to monitor someone else’s activity without their consent is illegal and against the ethics of cybersecurity. Always respect privacy and comply with local laws.

---

### Developer

- **Name**: Steve Splash
- **Contact**: [GitHub](https://github.com/stevesplash934/) | [Email](mailto:stevesplash4@gmail.com)

---

### Future Updates

- **Downloading**: Enhancing download reliability for recorded videos.
