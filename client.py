#!/usr/bin/env python3
"""
Remote Connection Client
A simple client to connect to the Remote Connection Host Server.
"""

import socket
import json
import sys
import getpass
from typing import Optional

class RemoteConnectionClient:
    """Client class for connecting to remote host server."""
    
    def __init__(self, host: str, port: int = 3389):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.token: Optional[str] = None
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to the remote host server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            
            # Receive welcome message
            welcome_data = self.socket.recv(4096)
            welcome_msg = json.loads(welcome_data.decode().strip())
            print(f"Server: {welcome_msg.get('message', 'Connected')}")
            
            return True
        except Exception as e:
            print(f"Failed to connect: {str(e)}")
            return False
    
    def send_message(self, message: dict) -> Optional[dict]:
        """Send message to server and receive response."""
        if not self.connected or not self.socket:
            print("Not connected to server")
            return None
        
        try:
            self.socket.send(json.dumps(message).encode() + b'\n')
            response_data = self.socket.recv(4096)
            return json.loads(response_data.decode().strip())
        except Exception as e:
            print(f"Communication error: {str(e)}")
            return None
    
    def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the server."""
        auth_msg = {
            "type": "auth",
            "username": username,
            "password": password
        }
        
        response = self.send_message(auth_msg)
        if response and response.get("success"):
            self.token = response.get("token")
            print("Authentication successful!")
            return True
        else:
            print(f"Authentication failed: {response.get('message', 'Unknown error')}")
            return False
    
    def execute_command(self, command: str) -> None:
        """Execute a command on the remote server."""
        if not self.token:
            print("Not authenticated. Please authenticate first.")
            return
        
        cmd_msg = {
            "type": "command",
            "token": self.token,
            "command": command
        }
        
        response = self.send_message(cmd_msg)
        if response:
            if response.get("type") == "command_response":
                stdout = response.get("stdout", "")
                stderr = response.get("stderr", "")
                returncode = response.get("returncode", 0)
                
                if stdout:
                    print(f"Output:\n{stdout}")
                if stderr:
                    print(f"Error:\n{stderr}")
                print(f"Return code: {returncode}")
            else:
                print(f"Error: {response.get('message', 'Unknown error')}")
    
    def get_system_info(self) -> None:
        """Get system information from the remote server."""
        if not self.token:
            print("Not authenticated. Please authenticate first.")
            return
        
        info_msg = {
            "type": "system_info",
            "token": self.token
        }
        
        response = self.send_message(info_msg)
        if response and response.get("type") == "system_info_response":
            print("System Information:")
            print(f"  Hostname: {response.get('hostname')}")
            print(f"  Platform: {response.get('platform')}")
            print(f"  Python Version: {response.get('python_version')}")
            print(f"  Server Time: {response.get('current_time')}")
        else:
            print(f"Error: {response.get('message', 'Failed to get system info')}")
    
    def disconnect(self):
        """Disconnect from the server."""
        if self.socket:
            self.socket.close()
        self.connected = False
        self.token = None
        print("Disconnected from server")
    
    def interactive_session(self):
        """Start an interactive session with the server."""
        print("Remote Connection Client")
        print("Available commands:")
        print("  auth <username> - Authenticate with username")
        print("  cmd <command> - Execute command on remote server")
        print("  sysinfo - Get system information")
        print("  quit - Exit")
        print()
        
        while True:
            try:
                user_input = input("remote> ").strip()
                if not user_input:
                    continue
                
                parts = user_input.split(None, 1)
                command = parts[0].lower()
                
                if command == "quit":
                    break
                elif command == "auth":
                    if len(parts) > 1:
                        username = parts[1]
                    else:
                        username = input("Username: ")
                    password = getpass.getpass("Password: ")
                    self.authenticate(username, password)
                elif command == "cmd":
                    if len(parts) > 1:
                        cmd = parts[1]
                        self.execute_command(cmd)
                    else:
                        print("Usage: cmd <command>")
                elif command == "sysinfo":
                    self.get_system_info()
                else:
                    print(f"Unknown command: {command}")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except EOFError:
                break


def main():
    """Main function for the client."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remote Connection Client")
    parser.add_argument("host", help="Remote host address")
    parser.add_argument("--port", type=int, default=3389, help="Remote port (default: 3389)")
    parser.add_argument("--username", help="Username for authentication")
    parser.add_argument("--command", help="Single command to execute")
    
    args = parser.parse_args()
    
    client = RemoteConnectionClient(args.host, args.port)
    
    if not client.connect():
        sys.exit(1)
    
    try:
        if args.username:
            password = getpass.getpass("Password: ")
            if not client.authenticate(args.username, password):
                sys.exit(1)
            
            if args.command:
                client.execute_command(args.command)
            else:
                client.interactive_session()
        else:
            client.interactive_session()
    
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()