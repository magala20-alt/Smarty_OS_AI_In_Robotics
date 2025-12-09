"""
Robot Server - Bridges GUI commands to RobotController
Runs on Raspberry Pi (or localhost for testing)
Receives commands from GUI via TCP socket and controls the DofBot arm
"""

import socket
import json
import threading
import time
import sys
import os
import import_ipynb

# Add parent folder to path for imports
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), '..')))

try:
    from robot_controller import RobotController
except ImportError:
    print("⚠️  Warning: Could not import RobotController - running in mock mode")
    RobotController = None

HOST = '0.0.0.0'  # Listen on all interfaces
PORT = 9001       # Must match pi_client.py PORT

# ============= ANIMAL POSITIONS  =============
ANIMAL_POSITIONS = {
    'lion': {'x': 180, 'y': 50, 'z': 100},
    'tiger': {'x': 180, 'y': -50, 'z': 100},
    'elephant': {'x': 150, 'y': 100, 'z': 100},
    'zebra': {'x': 150, 'y': -100, 'z': 100},
    'giraffe': {'x': 120, 'y': 80, 'z': 100},
    'leopard': {'x': 120, 'y': -80, 'z': 100},
}

DROP_ZONE = {'x': 100, 'y': -150, 'z': 150}


class RobotServer:
    """
    Server that handles GUI commands and controls the robot.
    Provides high-level command parsing and delegates to RobotController.
    """
    
    def __init__(self, use_real_hardware=False):
        """
        Initialize robot server.
        
        Args:
            use_real_hardware: If True, initialize real arm. If False, simulate.
        """
        self.use_real_hardware = use_real_hardware
        self.robot = None
        self.holding_object = False
        self.current_object = None
        
        if RobotController is None:
            print("⚠️  RobotController not available - using mock server only")
            return
        
        try:
            print("🤖 Initializing robot server...")
            self.robot = RobotController(use_real_hardware=use_real_hardware)
            self.robot.connect()
            self.robot.home()
            print("✅ Robot initialized and homed")
        except Exception as e:
            print(f"⚠️  Error initializing robot: {e}")
            self.robot = None
    
    def parse_command(self, command_text):
        """
        Parse natural language commands from GUI.
        
        Supported commands:
        - "find/search [animal]" → Search for animal
        - "grab/pick [animal]" → Pick up animal
        - "put [it/that] back" → Put object back in drop zone
        - "home" → Return to home position
        - "help" → List available animals
        
        Args:
            command_text: Raw text from GUI
            
        Returns:
            dict: {'status': str, 'message': str}
        """
        cmd = command_text.lower().strip()
        print(f"📨 Parsing command: '{cmd}'")
        
        # List of animals
        animals = list(ANIMAL_POSITIONS.keys())
        
        # Find which animal is mentioned
        found_animal = next((animal for animal in animals if animal in cmd), None)
        
        # --- HELP COMMAND ---
        if 'help' in cmd:
            animal_list = ', '.join(animals)
            return {
                'status': 'happy',
                'message': f'I can find: {animal_list} 🐾'
            }
        
        # --- GRAB/PICK COMMAND ---
        if any(word in cmd for word in ['grab', 'pick', 'take']):
            if found_animal:
                return self.grab_object(found_animal)
            else:
                return {
                    'status': 'confused',
                    'message': 'Which animal do you want me to grab? 🤔'
                }
        
        # --- PUT BACK COMMAND ---
        if 'put' in cmd and 'back' in cmd:
            if self.holding_object:
                return self.put_back_object()
            else:
                return {
                    'status': 'sad',
                    'message': 'I am not holding anything! 😢'
                }
        
        # --- FIND/SEARCH COMMAND ---
        if any(word in cmd for word in ['find', 'search', 'look']):
            if found_animal:
                return self.search_object(found_animal)
            else:
                return {
                    'status': 'confused',
                    'message': 'What animal are we looking for? 🔍'
                }
        
        # --- HOME COMMAND ---
        if 'home' in cmd:
            return self.go_home()
        
        # --- DEFAULT ---
        return {
            'status': 'sad',
            'message': "I didn't understand that! Say 'help' for commands. 😢"
        }
    
    def grab_object(self, animal):
        """
        Grab an object at known position.
        
        Args:
            animal: Animal name to grab
            
        Returns:
            dict: Response with status and message
        """
        if not self.robot:
            return {'status': 'grab', 'message': f'[MOCK] Dora grabbed the {animal}! 🤗'}
        
        try:
            if self.holding_object:
                return {
                    'status': 'sad',
                    'message': f'I am already holding the {self.current_object}! 😢'
                }
            
            # Get position for this animal
            pos = ANIMAL_POSITIONS.get(animal)
            if not pos:
                return {
                    'status': 'sad',
                    'message': f'I do not know where the {animal} is! 😢'
                }
            
            print(f"🎯 Grabbing {animal} at {pos}")
            
            # Execute pick sequence
            success = self.robot.pick_object(
                pos['x'], pos['y'], pos['z'],
                obj_label=animal
            )
            
            if success:
                self.holding_object = True
                self.current_object = animal
                return {
                    'status': 'grab',
                    'message': f'Dora grabbed the {animal}! 🤗'
                }
            else:
                return {
                    'status': 'sad',
                    'message': f'I could not grab the {animal}! 😢'
                }
        
        except Exception as e:
            print(f"❌ Error grabbing object: {e}")
            return {
                'status': 'sad',
                'message': f'Oops! Something went wrong: {str(e)}'
            }
    
    def put_back_object(self):
        """
        Put object back in drop zone and return home.
        
        Returns:
            dict: Response with status and message
        """
        if not self.robot:
            return {'status': 'putback', 'message': '[MOCK] We did it! 🎉'}
        
        try:
            if not self.holding_object:
                return {
                    'status': 'sad',
                    'message': 'I am not holding anything! 😢'
                }
            
            print(f"🏠 Putting back {self.current_object}")
            
            # Move to drop zone
            drop = DROP_ZONE
            self.robot.move_to(drop['x'], drop['y'], drop['z'], gripper_open=False)
            
            # Open gripper
            self.robot.set_gripper(True)
            time.sleep(0.5)
            
            # Return home
            self.robot.home()
            
            self.holding_object = False
            object_name = self.current_object
            self.current_object = None
            
            return {
                'status': 'putback',
                'message': f'We put the {object_name} back! Yay! 🎉'
            }
        
        except Exception as e:
            print(f"❌ Error putting back object: {e}")
            return {
                'status': 'sad',
                'message': f'Oops! Could not put it back: {str(e)}'
            }
    
    def search_object(self, animal):
        """
        Search for an object by moving to its position.
        
        Args:
            animal: Animal name to search for
            
        Returns:
            dict: Response with status and message
        """
        if not self.robot:
            return {'status': 'happy', 'message': f'[MOCK] Dora found the {animal}! 🐾'}
        
        try:
            pos = ANIMAL_POSITIONS.get(animal)
            if not pos:
                return {
                    'status': 'sad',
                    'message': f'I have not seen the {animal}! 😢'
                }
            
            print(f"🔍 Searching for {animal} at {pos}")
            
            # Move to search position
            self.robot.move_to(pos['x'], pos['y'], pos['z'] + 100, gripper_open=True)
            
            return {
                'status': 'happy',
                'message': f'Dora found the {animal}! 🐾'
            }
        
        except Exception as e:
            print(f"❌ Error searching: {e}")
            return {
                'status': 'sad',
                'message': f'I could not search: {str(e)}'
            }
    
    def go_home(self):
        """
        Return robot to home position.
        
        Returns:
            dict: Response with status and message
        """
        if not self.robot:
            return {'status': 'happy', 'message': '[MOCK] Dora is home! 🏠'}
        
        try:
            print("🏠 Moving home")
            self.robot.home()
            return {
                'status': 'happy',
                'message': 'Dora is ready! 🏠'
            }
        except Exception as e:
            print(f"❌ Error going home: {e}")
            return {
                'status': 'sad',
                'message': f'Could not go home: {str(e)}'
            }


def handle_client_connection(conn, addr, server):
    """
    Handle incoming connection from GUI client.
    
    Args:
        conn: Socket connection
        addr: Client address
        server: RobotServer instance
    """
    print(f"🔗 Client connected: {addr}")
    try:
        with conn:
            # Receive command
            data = conn.recv(2048)
            if not data:
                print(f"❌ No data received from {addr}")
                return
            
            command = data.decode('utf-8')
            print(f"📨 Received: {command}")
            
            # Parse and execute command
            response = server.parse_command(command)
            print(f"📤 Sending: {response}")
            
            # Send JSON response
            conn.send(json.dumps(response).encode('utf-8'))
    
    except Exception as e:
        print(f"❌ Error handling client {addr}: {e}")
        try:
            error_response = {
                'status': 'sad',
                'message': f'Server error: {str(e)}'
            }
            conn.send(json.dumps(error_response).encode('utf-8'))
        except:
            pass
    finally:
        print(f"🔌 Client disconnected: {addr}")


def start_server(use_real_hardware=False, host=None, port=None):
    """
    Start the robot server.
    
    Args:
        use_real_hardware: Connect to real arm (True for Pi, False for testing)
        host: Server host (default: 0.0.0.0)
        port: Server port (default: 9001)
    """
    if host is None:
        host = HOST
    if port is None:
        port = PORT
    
    # Initialize robot controller
    server = RobotServer(use_real_hardware=use_real_hardware)
    
    # Create server socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"\n{'='*60}")
        print(f"🤖 ROBOT SERVER STARTED")
        print(f"{'='*60}")
        print(f"📍 Listening on {host}:{port}")
        print(f"🔧 Hardware mode: {use_real_hardware}")
        print(f"✅ Ready for GUI commands!")
        print(f"{'='*60}\n")
        
        # Accept connections
        while True:
            try:
                conn, addr = server_socket.accept()
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=handle_client_connection,
                    args=(conn, addr, server),
                    daemon=True
                )
                client_thread.start()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"❌ Error accepting connection: {e}")
    
    except KeyboardInterrupt:
        print("\n🛑 Server shutting down...")
    except Exception as e:
        print(f"❌ Fatal server error: {e}")
    finally:
        if server.robot:
            print("👋 Disconnecting robot...")
            server.robot.disconnect()
        server_socket.close()
        print("✅ Server stopped")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Robot Server - GUI to DofBot Bridge')
    parser.add_argument('--hardware', action='store_true', 
                       help='Connect to real hardware (Raspberry Pi)')
    parser.add_argument('--host', default=HOST,
                       help=f'Server host (default: {HOST})')
    parser.add_argument('--port', type=int, default=PORT,
                       help=f'Server port (default: {PORT})')
    
    args = parser.parse_args()
    
    try:
        start_server(
            use_real_hardware=args.hardware,
            host=args.host,
            port=args.port
        )
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
