# =================================================================================================
# Contributing Authors:	    Gabriel Kahle
# Email Addresses:          gtka226@uky.edu
# Date:                     11/26/2025
# Purpose:                  This handles the server logic for login, authentication, matchmaking and gameplay communication between two clients
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

def load_passwords():
    #Purpose: Read in the password dictionary
    #Arguments : None
    try:
        with open(PASSWORD_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_passwords(password_dict):
    #Purpose: Add a new user to the password dictionary and write it to the file
    #Arguments: The password dictionary
    with open(PASSWORD_FILE, 'w') as f:
        json.dump(password_dict,f)

def load_leaderboard(): #This would load in our leaderboard if I could get it working
    try:
        with open(LEADERBOARD_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return{}

password_dict = load_passwords() #Get the dictionary
leaderboard = load_leaderboard() # Get the leaderboards

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Setup of Server Scoket  
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
print(socket.gethostbyname(socket.gethostname())) #Print the IP address of our server on startup
server.bind(("0.0.0.0", 65432))   # listen on all interfaces, port 65432
server.listen()

waiting_for_game = {}  #Waiting for game dictionary
game_lock = threading.Lock() #The thread locker for the waiting for games dictioanry

active_games ={} #Active games dictionary
active_lock = threading.Lock() #Thread locker

def handle_game(my_conn, enemy_conn, my_name, their_name, game_id):
    #Purpose: Handles the message swapping between two clients
    #Arguments
    #my_conn    The socket object for the client using this thread
    #enemy_conn The socket object for the opponnent of this thread
    #my_name    My usernmae
    #their_name Their username 
    #game_id    The id of the game

    #Notes      This is very primitive, but it works for what is required of the project, I could add to it and give it leaderboard addtion and then proper call backs, but did not have the time

    #print(f'The thread for {my_name} is working for {their_name}')
    with active_lock: #Add the id to active games
        if game_id not in active_games:
            active_games[game_id] ={
                "user1" : my_name,
                "user2" : their_name,
            }
    me_disconnect = False #Check for disconnects
    them_disconnect = False
    winner = None
    while True:
        try:
            msg = my_conn.recv(1024) # we receive the packet from the user
            #print(f"[SERVER] Received {len(msg)} bytes from {my_name}", flush=True)  # ← ADD THIS

            if not msg: #We did not receive anything, indicating a disconnect so we tell the opponennt
                break

            try:
                msg_data = msg.decode('utf-8').strip() #We have to make sure no one won yet
                msg_data = json.loads(msg)
                #print(f"[SERVER {my_name}] Parsed successfully, forwarding to {their_name}", flush=True)
            
                enemy_conn.send(msg)
               # print(f"[SERVER {my_name}] Forwarded to {their_name}", flush=True)
            except json.JSONDecodeError as e:
                #print(f"[SERVER {my_name}] JSON error: {e}", flush=True)
                continue
            except Exception as e:
                #print(f"[SERVER {my_name}] Exception: {e}", flush=True)
                break

        except Exception as e:
            print(f"[SERVER {my_name}] Exception: {e}", flush=True)
            break
    
    with active_lock: #Game over, we remove the game from active_games
        if game_id in active_games:
            del active_games[game_id]
    




def handle_client(conn, addr):
    #Purpose    To authenticate and find the client an opponent
    #Arguments
    #Conn       The connection of the client
    #Addr       The address of the client
    print(f"[NEW CONNECTION] {addr}") #output to make sure the client is connecting
    authenticated = False #Vars to use later
    username = None
    try:
        auth_msg = conn.recv(1024).decode('utf-8').strip()
        auth_data = json.loads(auth_msg) #Get the json out

        if auth_data.get("type") == "auth": #Make sure this is an authentication message
            username = auth_data.get("username") #Get the username and password
            password = auth_data.get("password")

            if username in password_dict: #This is a reutrning user
                if password_dict[username] == password:
                    authenticated = True
                    response = {  #Craft the message back
                        "type" : "auth_response",
                        "success" : True,
                        "message" : "Login successful"
                    }
                else: #Wrong password
                    
                        response = { 
                        "type" : "auth_response",
                        "success" : False,
                        "message" : "Incorrect Password"
                        }
            else: #New user, so setup account
                password_dict[username] = password
                save_passwords(password_dict)
                authenticated = True
                response = { 
                        "type" : "auth_response",
                        "success" : True,
                        "message" : "Registration Successful"
                    }
            response_json = json.dumps(response) #Craft the JSon packet
            padded_response = response_json.ljust(1024) #Pad
            conn.send(padded_response.encode('utf-8')) #Encode and send
    except Exception as e:
        print(f"ERROR {addr} : {e}")
        authenticated = False
    if not authenticated:
        conn.close()
        print(f"Connection failed with {addr}")
        return
    print(f"Authenticated User: {username} from {addr}")


    chal_rec = conn.recv(1024).decode('utf-8').strip()
    chal_data = json.loads(chal_rec) #This holds the information about who the client is trying to challenge
    user_event = threading.Event() #We set up the event and may or may not use it
    if(chal_data["type"] == "Find Opponent"): #This is just a secondary check to make sure the right message came through
        if chal_data["mode"] == "random": #They want a random opponent
            with game_lock:
                found = False
                for client in waiting_for_game: #loop through clients to see if someone is waiting
                    client_data = waiting_for_game[client] #We get the stored information of the client
                    if client_data["target"] == None: #They also want a random opponent
                        #Set found to true and build the challenge message
                        found = True
                        client_data["target"] = conn #We put our information in for the opponent
                        game_id = f"{username}_{client}"
                        client_data["id"] = game_id
                        #We grab their info
                        enemy_name = client
                        enemy_conn = client_data["conn"]
                        client_data["event"].set()
                        
                        assignment_msg = { #This message is the same for both clients, but if you get found, you get the right paddle
                            "type" : "assignment",
                            "paddle" : "left",
                            "height" : 640,
                            "width" : 964,
                        }
                        send = json.dumps(assignment_msg)
                        padded_response = send.ljust(1024)
                        conn.send(padded_response.encode('utf-8'))
                        
                if not found: # we didn't find anyone in the list so we add ourselves
                    waiting_for_game[username] = {"conn" : conn,  #Insert ourselves into the waiting for game
                                        "mode" : "random", 
                                        "target" : None,
                                        "event" : user_event,
                                        "id" : None,
                                        }

                
            if(not found): #we wait for someone to find us
                user_event.wait() #Start the event, it will be turned off when we are found
                with game_lock:
                    #Get all the information we need
                    enemy_conn = waiting_for_game[username]["target"]
                    game_id = waiting_for_game[username]["id"]
                    username_list = game_id.split("_")
                    enemy_name = username_list[0] 
                    del waiting_for_game[username] #Remove ourselves from waiting
                assignment_msg = { #Send the assignment message to the client
                            "type" : "assignment",
                            "paddle" : "right",
                            "height" : 640,
                            "width" : 964,
                        }
                send = json.dumps(assignment_msg)
                padded_response = send.ljust(1024)
                conn.send(padded_response.encode('utf-8'))
                
        else: #They want a specific person
            with game_lock:

                found = False

                for client in waiting_for_game: #loop through clients to see if the specific person is waiting
                    if client == chal_data["target"]: #Found the correct person
                        found =True
                        client_data = waiting_for_game[client]
                        client_data["target"] = conn #We set the opponents information
                        game_id = f"{username}_{client}"
                        client_data["id"] = game_id
                        #We grab their info
                        enemy_name = client
                        enemy_conn = client_data["conn"]
                        client_data["event"].set()
                        assignment_msg = {
                            "type" : "assignment",
                            "paddle" : "left",
                            "height" : 640,
                            "width" : 964,
                        }
                        send = json.dumps(assignment_msg)
                        padded_response = send.ljust(1024)
                        conn.send(padded_response.encode('utf-8'))
                if (not found): #we didn't find the person so we edit the list to hold us
                    waiting_for_game[username] = {"conn" : conn,  #Insert ourselves into the waiting for game
                                            "mode" : "specifc", 
                                            "target" : chal_data["target"],
                                             "event" : user_event,
                                              "id" : None
                                              }
            if (not found): #we wait outside the list
                user_event.wait() #Set the event, to be turned off by the person who finds us
                with game_lock:
                    #Get the necessary information
                    enemy_conn = waiting_for_game[username]["target"]
                    game_id = waiting_for_game[username]["id"]
                    username_list = game_id.split("_")
                    enemy_name = username_list[0]
                    del waiting_for_game[username]   #Remove ourselves from the list
                assignment_msg = { #Send the assignment message
                            "type" : "assignment",
                            "paddle" : "right",
                            "height" : 640,
                            "width" : 964,
                        }
                send = json.dumps(assignment_msg)
                padded_response = send.ljust(1024)
                conn.send(padded_response.encode('utf-8'))
        
    else: #Some error occured so we close the connection and quit
        conn.close()
        print("Error when finding opponent for user")
        return 
    handle_game(conn, enemy_conn, username, enemy_name, game_id) #Go into handle game
    
    
    



while True: #Constant loop of accepting clients when they come in
    conn, addr = server.accept()
    thread = threading.Thread(target=handle_client, args=(conn, addr))
    thread.start()


