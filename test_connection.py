"""
Test Script - Verify GUI to Robot Connection
Run this to test if everything is connected properly
"""

import socket
import json
import sys

def test_robot_connection(host='127.0.0.1', port=9001):
    """Test TCP connection to robot server"""
    print(f"🧪 Testing connection to {host}:{port}...")
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((host, port))
        print("✅ Connected to robot server!")
        
        # Test a command
        test_commands = [
            "find the lion",
            "grab the tiger",
            "help",
            "home"
        ]
        
        for cmd in test_commands:
            print(f"\n📨 Sending: '{cmd}'")
            s.send(cmd.encode())
            response = s.recv(4096).decode()
            result = json.loads(response)
            print(f"📤 Response: {result['message']}")
            print(f"   Status: {result['status']}")
        
        s.close()
        print("\n✅ All tests passed!")
        return True
    
    except ConnectionRefusedError:
        print("❌ Connection refused!")
        print("   Is robot_server.py running? Try: python Gui/robot_server.py")
        return False
    
    except json.JSONDecodeError:
        print("❌ Invalid JSON response from server")
        return False
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def test_flask_connection(url='http://127.0.0.1:5000'):
    """Test Flask web server"""
    print(f"\n🧪 Testing Flask app at {url}...")
    
    try:
        import requests
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            print("✅ Flask server is running!")
            return True
        else:
            print(f"❌ Flask returned status {response.status_code}")
            return False
    except ImportError:
        print("⚠️  requests library not installed, skipping Flask test")
        print("   Install: pip install requests")
        return None
    except Exception as e:
        print(f"❌ Cannot reach Flask: {e}")
        print("   Is Flask running? Try: python -m flask run --port 5000")
        return False


def test_imports():
    """Test if required modules are importable"""
    print("🧪 Testing imports...")
    
    modules_to_test = [
        ('socket', 'Socket library'),
        ('json', 'JSON library'),
        ('threading', 'Threading library'),
        ('core.robot_controller', 'RobotController (optional)'),
    ]
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {description}")
        except ImportError:
            if 'optional' in description:
                print(f"⚠️  {description} - Not required yet")
            else:
                print(f"❌ {description}")


def print_instructions():
    """Print setup instructions"""
    print("\n" + "="*60)
    print("SETUP INSTRUCTIONS")
    print("="*60)
    print("""
1. CONVERT NOTEBOOK TO PYTHON:
   cd core
   jupyter nbconvert --to python robot_controller.ipynb

2. START ROBOT SERVER (Terminal 1):
   cd Gui
   python robot_server.py

3. START FLASK APP (Terminal 2):
   cd Gui
   python -m flask run --host 0.0.0.0 --port 5000

4. OPEN BROWSER:
   http://localhost:5000

5. GIVE VOICE COMMAND:
   Say "Find the lion!"
""")
    print("="*60)


if __name__ == '__main__':
    print("\n" + "="*60)
    print("SMARTY OS - GUI TO ROBOT CONNECTION TEST")
    print("="*60)
    
    # Test imports
    test_imports()
    
    # Test robot server
    print("\n" + "-"*60)
    robot_ok = test_robot_connection()
    
    # Test Flask
    print("\n" + "-"*60)
    flask_ok = test_flask_connection()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    if robot_ok:
        print("✅ Robot server is running and responding")
    else:
        print("❌ Robot server not responding - start with: python Gui/robot_server.py")
    
    if flask_ok:
        print("✅ Flask web server is running")
    elif flask_ok is False:
        print("❌ Flask not running - start with: python -m flask run --port 5000")
    
    if robot_ok and flask_ok:
        print("\n🎉 Everything is connected! Try giving voice commands at http://localhost:5000")
        sys.exit(0)
    else:
        print("\n⚠️  Some components are not ready yet")
        print_instructions()
        sys.exit(1)
