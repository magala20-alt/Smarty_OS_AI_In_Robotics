# GUI/app.py
import sys
import os
import threading
import speech_recognition as sr
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

# Fix import paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comms.pi_client import send_command_to_pi
from speech.voice_input import listen_command

# Initialize Flask app
app = Flask(__name__, static_folder="../static", template_folder="templates")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')


# Home page
@app.route('/')
def index():
    return render_template('index.html')


# Endpoint to send command to robot
@app.route('/send', methods=['POST'])
def send():
    data = request.json
    command = data.get('command')
    socketio.emit('status', {'state': 'thinking', 'message': '🤔 Dora is thinking...'})
    threading.Thread(target=send_and_update, args=(command,)).start()
    return jsonify({'ok': True})


# Voice input endpoint
@app.route('/voice', methods=['GET'])
def voice_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎤 Listening for voice input...")
        audio = recognizer.listen(source)
        try:
            command = recognizer.recognize_google(audio)
            print(f"✅ Recognized: {command}")
            return jsonify({"command": command})
        except sr.UnknownValueError:
            print("❌ Could not understand audio")
            return jsonify({"command": ""})
        except sr.RequestError as e:
            print(f"⚠️ Speech recognition service error: {e}")
            return jsonify({"command": ""})

# Function to handle sending command and updating GUI
def send_and_update(command):
    try:
        socketio.emit('status', {'state': 'thinking', 'message': '🤔 Dora is thinking...'})
        response = send_command_to_pi(command)
        state = response.get('status', 'sad')
        message = response.get('message', '')

        # Friendly child-like messages
        if 'Comm error' in message:
            socketio.emit('status', {'state': 'sad', 'message': "Oops! I couldn’t find that item!"})
        else:
            socketio.emit('status', {'state': state, 'message': message})
    except Exception as e:
        socketio.emit('status', {'state': 'sad', 'message': "Uh-oh! Something went wrong."})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
