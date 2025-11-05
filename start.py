#!/usr/bin/env python3
"""
Remote Connection Host Server
A secure remote access server that listens on port 3389 and allows
authorized clients to connect via hostname or IP address.
"""

import socket
import threading
import subprocess
import json
import hashlib
import secrets
import time
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rdp_host.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class RemoteConnectionHost:
    """Main server class for handling remote connections."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 3389):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.clients: Dict[str, dict] = {}
        self.auth_tokens: Dict[str, str] = {}
        
        # Default credentials (should be changed in production)
        self.credentials = {
            "admin": self._hash_password("admin123"),
            "user": self._hash_password("user123")
        }
        
        logger.info(f"Initialized RemoteConnectionHost on {host}:{port}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_hex(32)
    
    def _authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate user and return session token if successful."""
        hashed_password = self._hash_password(password)
        if username in self.credentials and self.credentials[username] == hashed_password:
            token = self._generate_token()
            self.auth_tokens[token] = username
            logger.info(f"User '{username}' authenticated successfully")
            return token
        logger.warning(f"Authentication failed for user '{username}'")
        return None
    
    def _validate_token(self, token: str) -> bool:
        """Validate session token."""
        return token in self.auth_tokens
    
    def _execute_command(self, command: str) -> Tuple[str, str, int]:
        """Execute system command and return output, error, and return code."""
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            try:
                stdout, stderr = process.communicate(timeout=30)
                return stdout, stderr, process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return stdout, "Command timed out", 1
        except Exception as e:
            return "", f"Error executing command: {str(e)}", 1
    
    def _handle_client_message(self, client_socket: socket.socket, message: dict) -> dict:
        """Process client message and return response."""
        msg_type = message.get("type")
        
        if msg_type == "auth":
            username = message.get("username")
            password = message.get("password")
            token = self._authenticate(username, password)
            
            if token:
                return {
                    "type": "auth_response",
                    "success": True,
                    "token": token,
                    "message": "Authentication successful"
                }
            else:
                return {
                    "type": "auth_response",
                    "success": False,
                    "message": "Authentication failed"
                }
        
        elif msg_type == "command":
            token = message.get("token")
            if not self._validate_token(token):
                return {
                    "type": "error",
                    "message": "Invalid or expired token"
                }
            
            command = message.get("command")
            if not command:
                return {
                    "type": "error",
                    "message": "No command provided"
                }
            
            stdout, stderr, returncode = self._execute_command(command)
            return {
                "type": "command_response",
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode
            }
        
        elif msg_type == "system_info":
            token = message.get("token")
            if not self._validate_token(token):
                return {
                    "type": "error",
                    "message": "Invalid or expired token"
                }
            
            return {
                "type": "system_info_response",
                "hostname": socket.gethostname(),
                "platform": sys.platform,
                "python_version": sys.version,
                "current_time": datetime.now().isoformat()
            }
        
        else:
            return {
                "type": "error",
                "message": f"Unknown message type: {msg_type}"
            }
    
    def _handle_client(self, client_socket: socket.socket, client_address: Tuple[str, int]):
        """Handle individual client connection."""
        client_id = f"{client_address[0]}:{client_address[1]}"
        logger.info(f"New client connected: {client_id}")
        
        self.clients[client_id] = {
            "socket": client_socket,
            "address": client_address,
            "connected_at": time.time(),
            "authenticated": False
        }
        
        try:
            # Send welcome message
            welcome_msg = {
                "type": "welcome",
                "message": "Connected to Remote Host Server",
                "server_time": datetime.now().isoformat()
            }
            client_socket.send(json.dumps(welcome_msg).encode() + b'\n')
            
            while self.running:
                # Receive data from client
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    # Parse JSON message
                    message = json.loads(data.decode().strip())
                    logger.debug(f"Received from {client_id}: {message.get('type', 'unknown')}")
                    
                    # Process message and send response
                    response = self._handle_client_message(client_socket, message)
                    client_socket.send(json.dumps(response).encode() + b'\n')
                    
                except json.JSONDecodeError:
                    error_response = {
                        "type": "error",
                        "message": "Invalid JSON format"
                    }
                    client_socket.send(json.dumps(error_response).encode() + b'\n')
                
        except ConnectionResetError:
            logger.info(f"Client {client_id} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {str(e)}")
        finally:
            client_socket.close()
            if client_id in self.clients:
                del self.clients[client_id]
            logger.info(f"Client {client_id} connection closed")
    
    def start(self):
        """Start the remote connection host server."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            logger.info(f"Remote Connection Host started on {self.host}:{self.port}")
            logger.info("Default credentials: admin/admin123, user/user123")
            logger.info("Waiting for connections...")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {str(e)}")
                    break
                    
        except Exception as e:
            logger.error(f"Failed to start server: {str(e)}")
            sys.exit(1)
    
    def stop(self):
        """Stop the server gracefully."""
        logger.info("Stopping Remote Connection Host...")
        self.running = False
        
        # Close all client connections
        for client_id, client_info in self.clients.items():
            try:
                client_info["socket"].close()
            except:
                pass
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
        
        logger.info("Server stopped")
    
    def get_server_info(self):
        """Get current server information."""
        return {
            "host": self.host,
            "port": self.port,
            "running": self.running,
            "active_clients": len(self.clients),
            "clients": list(self.clients.keys())
        }


def main():
    """Main function to start the remote connection host."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remote Connection Host Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3389, help="Port to listen on (default: 3389)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create and start the server
    server = RemoteConnectionHost(host=args.host, port=args.port)
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        server.stop()


if __name__ == "__main__":
    main()