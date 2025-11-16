import socket
import threading
import json
import time

HOST = '127.0.0.1'
PORT = 9000

def handle_conn(conn, addr):
    print('Connected by', addr)
    with conn:
        data = conn.recv(2048)
        if not data:
            return
        msg = data.decode().lower()
        print('Received:', msg)
        time.sleep(1)

        # --- inside handle_conn ---
        animals = ['lion', 'tiger', 'elephant', 'zebra', 'giraffe', 'leopard']
        found_animal = next((animal for animal in animals if animal in msg), None)

        if 'grab' in msg and found_animal:
            resp = {'status': 'grab', 'message': f'Dora grabbed the {found_animal}! 🤗'}
        elif 'put' in msg and 'back' in msg:
            resp = {'status': 'putback', 'message': 'Yay! We did it! 🎉'}
        elif found_animal:
            resp = {'status': 'happy', 'message': f'Dora found the {found_animal}! 🐾'}
        else:
            resp = {'status': 'sad', 'message': 'Hmm... Dora could not find it 😢'}

        conn.send(json.dumps(resp).encode())

def server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print('Mock Pi server listening on', HOST, PORT)
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_conn, args=(conn, addr)).start()

if __name__ == '__main__':
    server()
