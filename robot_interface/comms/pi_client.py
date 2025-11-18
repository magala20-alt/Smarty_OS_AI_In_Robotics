import socket
import json

PI_HOST = '127.0.0.1'  # change to Pi IP when deploying
PI_PORT = 9000

def send_command_to_pi(command_text, timeout=8):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((PI_HOST, PI_PORT))
        s.send(command_text.encode())
        data = s.recv(4096)
        s.close()
        return json.loads(data.decode())
    except Exception as e:
        return {'status':'sad', 'message': f'Comm error: {e}'}
