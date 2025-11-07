# =================================================================================================
# Contributing Authors:	    <Anyone who touched the code>
# Email Addresses:          <Your uky.edu email addresses>
# Date:                     <The date the file was last edited>
# Purpose:                  <How this file contributes to the project>
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import socket
import threading
import hashlib #Needed to store passwords securely
import os #Needed to read in files
import json #Using this for easy read in and write for values
# Use this file to write your server logic
# You will need to support at least two clients
# You will need to keep track of where on the screen (x,y coordinates) each paddle is, the score 
# for each player and where the ball is, and relay that to each client
# I suggest you use the sync variable in pongClient.py to determine how out of sync your two
# clients are and take actions to resync the games


PASSWORD_FILE = "passwords.json" #Constant will always been in every run
LEADERBOARD_FILE = "leaderboard.json" #Constant, file will always be called this

#This is to read in the password dictionary
def load_passwords():
    try:
        with open(PASSWORD_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

#This is to save passwords if new users were added
def save_passwords(password_dict):
    with open(PASSWORD_FILE, 'w') as f:
        json.dump(password_dict,f)

password_dict = load_passwords() #Get the dictionary

#Hash the password for secure storage and login


server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Setup of Server Scoket  
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server.bind(("0.0.0.0", 65432))   # listen on all interfaces, port 65432
server.listen()

clients = []  # list of connected clients

def handle_client(conn, addr):
    print(f"[NEW CONNECTION] {addr}")
    authenticated = False
    username = None
    try:
        auth_msg = conn.recv(1024).decode('utf-8').strip()
        auth_data = json.loads(auth_msg)

        if auth_data.get("type") == "auth":
            username = auth_data.get("username")
            password = auth_data.get("password")

            if username in password_dict:
                if password_dict[username] == password:
                    authenticated = True
                    response = { 
                        "type" : "auth_response",
                        "success" : True,
                        "message" : "Login successful"
                    }
                else:
                    
                        response = { 
                        "type" : "auth_response",
                        "success" : False,
                        "message" : "Incorrect Password"
                        }
            else:
                password_dict[username] = password
                save_passwords(password_dict)
                authenticated = True
                response = { 
                        "type" : "auth_response",
                        "success" : True,
                        "message" : "Registration Successful"
                    }
            response_json = json.dumps(response)
            padded_response = response_json.ljust(1024)
            conn.send(padded_response.encode('utf-8'))
    except Exception as e:
        print(f"ERROR {addr} : {e}")
        authenticated = False
    if not authenticated:
        conn.close()
        print(f"Connection failed with {addr}")
        return
    print(f"Authenticated User: {username} from {addr}")


while True:
    conn, addr = server.accept()
    clients.append(conn)
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()


