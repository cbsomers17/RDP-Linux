#!/usr/bin/env python3
"""Quick test script to verify the server functionality."""

import socket
import json
import time
import subprocess
import sys
import os

def test_server():
    # Start server in background
    server_cmd = [
        "python3",
        "start.py",
        "--port", "3392"
    ]
    
    print("Starting server...")
    server_process = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(2)  # Give server time to start
    
    try:
        # Test client connection
        print("Testing client connection...")
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(("localhost", 3392))
        
        # Receive welcome message
        welcome_data = client_socket.recv(4096)
        welcome_msg = json.loads(welcome_data.decode().strip())
        print(f"Server welcome: {welcome_msg.get('message')}")
        
        # Test authentication
        auth_msg = {
            "type": "auth",
            "username": "admin",
            "password": "admin123"
        }
        
        print("Testing authentication...")
        client_socket.send(json.dumps(auth_msg).encode() + b'\n')
        auth_response = client_socket.recv(4096)
        auth_result = json.loads(auth_response.decode().strip())
        
        print(f"Auth result: {auth_result}")
        
        if auth_result.get("success"):
            token = auth_result.get("token")
            print(f"Authentication successful! Token: {token[:16]}...")
            
            # Test command execution
            cmd_msg = {
                "type": "command",
                "token": token,
                "command": "echo 'Hello from remote server'"
            }
            
            print("Testing command execution...")
            client_socket.send(json.dumps(cmd_msg).encode() + b'\n')
            cmd_response = client_socket.recv(4096)
            cmd_result = json.loads(cmd_response.decode().strip())
            
            print(f"Command result: {cmd_result}")
            
            if cmd_result.get("stdout"):
                print(f"Command output: {cmd_result['stdout'].strip()}")
                print("✅ All tests passed!")
            else:
                print("❌ Command execution failed")
        else:
            print("❌ Authentication failed")
        
        client_socket.close()
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
    
    finally:
        # Stop server
        print("Stopping server...")
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    test_server()