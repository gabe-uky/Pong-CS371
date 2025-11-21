# =================================================================================================
# Contributing Authors:	    <Anyone who touched the code>
# Email Addresses:          <Your uky.edu email addresses>
# Date:                     <The date the file was last edited>
# Purpose:                  <How this file contributes to the project>
# Misc:                     <Not Required.  Anything else you might want to include>
# =================================================================================================

import pygame
import tkinter as tk
import sys
import socket
import hashlib
import json
from assets.code.helperCode import *

# This is the main game loop.  For the most part, you will not need to modify this.  The sections
# where you should add to the code are marked.  Feel free to change any part of this project
# to suit your needs.
def playGame(screenWidth:int, screenHeight:int, playerPaddle:str, client:socket.socket, username : str) -> None:
    client.setblocking(False) #makes it so we can play the game
    print("entered play game")
    # Pygame inits
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()

    # Constants
    WHITE = (255,255,255)
    clock = pygame.time.Clock()
    scoreFont = pygame.font.Font("./assets/fonts/pong-score.ttf", 32)
    winFont = pygame.font.Font("./assets/fonts/visitor.ttf", 48)
    pointSound = pygame.mixer.Sound("./assets/sounds/point.wav")
    bounceSound = pygame.mixer.Sound("./assets/sounds/bounce.wav")

    # Display objects
    screen = pygame.display.set_mode((screenWidth, screenHeight))
    winMessage = pygame.Rect(0,0,0,0)
    topWall = pygame.Rect(-10,0,screenWidth+20, 10)
    bottomWall = pygame.Rect(-10, screenHeight-10, screenWidth+20, 10)
    centerLine = []
    for i in range(0, screenHeight, 10):
        centerLine.append(pygame.Rect((screenWidth/2)-5,i,5,5))

    # Paddle properties and init
    paddleHeight = 50
    paddleWidth = 10
    paddleStartPosY = (screenHeight/2)-(paddleHeight/2)
    leftPaddle = Paddle(pygame.Rect(10,paddleStartPosY, paddleWidth, paddleHeight))
    rightPaddle = Paddle(pygame.Rect(screenWidth-20, paddleStartPosY, paddleWidth, paddleHeight))

    ball = Ball(pygame.Rect(screenWidth/2, screenHeight/2, 5, 5), -5, 0)

    if playerPaddle == "left":
        opponentPaddleObj = rightPaddle
        playerPaddleObj = leftPaddle
    else:
        opponentPaddleObj = leftPaddle
        playerPaddleObj = rightPaddle

    lScore = 0
    rScore = 0

    sync = 0
    send_counter = 0 #for send buffer
    while True:
        # Wiping the screen
        screen.fill((0,0,0))

        # Getting keypress events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    playerPaddleObj.moving = "down"

                elif event.key == pygame.K_UP:
                    playerPaddleObj.moving = "up"

            elif event.type == pygame.KEYUP:
                playerPaddleObj.moving = ""

        # =========================================================================================
        # Your code here to send an update to the server on your paddle's information,
        # where the ball is and the current score.
        # Feel free to change when the score is updated to suit your needs/requirements
        
         
        # =========================================================================================

        # Update the player paddle and opponent paddle's location on the screen
        
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            if paddle.moving == "down":
                if paddle.rect.bottomleft[1] < screenHeight-10:
                    paddle.rect.y += paddle.speed
            elif paddle.moving == "up":
                if paddle.rect.topleft[1] > 10:
                    paddle.rect.y -= paddle.speed
                   
        # If the game is over, display the win message
        if lScore > 4 or rScore > 4:
            winText = "Player 1 Wins! " if lScore > 4 else "Player 2 Wins! "
            textSurface = winFont.render(winText, False, WHITE, (0,0,0))
            textRect = textSurface.get_rect()
            textRect.center = ((screenWidth/2), screenHeight/2)
            winMessage = screen.blit(textSurface, textRect)
            
        else:

            # ==== Ball Logic =====================================================================
            ball.updatePos()

            # If the ball makes it past the edge of the screen, update score, etc.
            if ball.rect.x > screenWidth:
                lScore += 1
                pointSound.play()
                ball.reset(nowGoing="left")
            elif ball.rect.x < 0:
                rScore += 1
                pointSound.play()
                ball.reset(nowGoing="right")
                
            # If the ball hits a paddle
            if ball.rect.colliderect(playerPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(playerPaddleObj.rect.center[1])
            elif ball.rect.colliderect(opponentPaddleObj.rect):
                bounceSound.play()
                ball.hitPaddle(opponentPaddleObj.rect.center[1])
                
            # If the ball hits a wall
            if ball.rect.colliderect(topWall) or ball.rect.colliderect(bottomWall):
                bounceSound.play()
                ball.hitWall()
            
            pygame.draw.rect(screen, WHITE, ball)
            # ==== End Ball Logic =================================================================

        # Drawing the dotted line in the center
        for i in centerLine:
            pygame.draw.rect(screen, WHITE, i)
        
        # Drawing the player's new location
        for paddle in [playerPaddleObj, opponentPaddleObj]:
            pygame.draw.rect(screen, WHITE, paddle)

        pygame.draw.rect(screen, WHITE, topWall)
        pygame.draw.rect(screen, WHITE, bottomWall)
        scoreRect = updateScore(lScore, rScore, screen, WHITE, scoreFont)
        pygame.display.update([topWall, bottomWall, ball, leftPaddle, rightPaddle, scoreRect, winMessage])
        clock.tick(60)
        
        # This number should be synchronized between you and your opponent.  If your number is larger
        # then you are ahead of them in time, if theirs is larger, they are ahead of you, and you need to
        # catch up (use their info)
        sync += 1
        # =========================================================================================
        # Send your server update here at the end of the game loop to sync your game with your
        # opponent's game
        send_counter += 1 #inc counter
        if send_counter >=2:
            send_counter =0
            paddle_pos = playerPaddleObj.rect.y
            ball_x = ball.rect.x
            ball_y = ball.rect.y
            score = {"left" : lScore, "right" : rScore}
            update_mesage = {"type" : "game update",
                            "sync" : sync,
                            "ball_x" : ball_x,
                            "ball_y" : ball_y,
                            "opp_pad" : paddle_pos,
                            "score" : score}
            print(f'Sent sync: {sync}')
            update_mesage = json.dumps(update_mesage).ljust(1024).encode()
        #print("trying to send a message")
            try:
                client.send(update_mesage)
                #print("should have sent the message")
            except BlockingIOError:
                pass
            except Exception as e:
                print(f'Error {e} when sending')
        
        try:
            rec = client.recv(1024)
            if rec:
                #print(f'{username} receieved data')
                opp_update = json.loads(rec.decode().strip())
                if opp_update["sync"] > sync: #They are ahead of us so we catch up
                    ball.rect.x = opp_update["ball_x"]
                    ball.rect.y = opp_update["ball_y"]
                    ball.updatePos() #Debug help
                    opponentPaddleObj.rect.y = opp_update["opp_pad"]
                    lScore = opp_update["score"]["left"]
                    rScore = opp_update["score"]["right"]
                    sync = opp_update["sync"]
                    print(f'Received sync: {sync}')
                elif sync > opp_update["sync"]: #we are ahead of them so they catch up
                    opponentPaddleObj.rect.y = opp_update["opp_pad"]
                else: #we are equal
                    opponentPaddleObj.rect.y = opp_update["opp_pad"]
        except BlockingIOError:
            pass
        except Exception as e:
            print(f'Error: {e}')
        pygame.display.update()
        # =========================================================================================

def game_challenge(client : socket, opp : str, username : str ) -> None: #Create the challenge message to send to the server and gets the assignment info back
    if opp == "random":
        challenge_msg = {
            "type" : "Find Opponent",
            "mode" : "random",
            "target" : None
        }
    else:
        challenge_msg = {
            "type" : "Find Opponent",
            "mode" : "specific",
            "target" : username
        }
    msg = json.dumps(challenge_msg).ljust(1024).encode()
    client.send(msg)
    rec = client.recv(1024)
    assignment = json.loads(rec.decode().strip())
    return assignment

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# This is where you will connect to the server to get the info required to call the game loop.  Mainly
# the screen width, height and player paddle (either "left" or "right")
# If you want to hard code the screen's dimensions into the code, that's fine, but you will need to know
# which client is which
def joinServer(ip:str, port:str, username : str, password : str, errorLabel:tk.Label, app:tk.Tk) -> None:
    # Purpose:      This method is fired when the join button is clicked
    # Arguments:
    # ip            A string holding the IP address of the server
    # port          A string holding the port the server is using
    #username       The Users login id
    #password       The password they are logging in with
    # errorLabel    A tk label widget, modify it's text to display messages to the user (example below)
    # app           The tk window object, needed to kill the window
    
    # Create a socket and connect to the server
    # You don't have to use SOCK_STREAM, use what you think is best
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Create the socket
    pw_h = hash_password(password) #hash the password

    auth_message = { #Craft the message to login
        "type" : "auth",
        "username" : username,
        "password" : pw_h
    }
    client.connect((ip,int(port))) #Connect to the server
    msg = json.dumps(auth_message).ljust(1024).encode() #Craft the json message and encode
    client.send(msg) #Send to server

    rec = client.recv(1024) #Receive information back from the server
    rec = json.loads(rec.decode().strip()) #Decode and strip

    if(rec["success"] == False): #Wrong Password
        errorLabel.config(text = f"Incorrect Password for the associated account")
        errorLabel.update()
        client.close()
        return
    
    errorLabel.config(text = f"Login Successful")
    errorLabel.update()

    image = tk.PhotoImage(file="./assets/images/logo.png") #Reload the image
    for widget in app.winfo_children(): #Destroy all widgets
        widget.destroy()
    titleLabel = tk.Label(app, image=image) #Repost the image
    titleLabel.image = image  
    titleLabel.grid(column=0, row=0, columnspan=3)
    
    errorLabel = tk.Label(app, text="Choose your opponent:") 
    errorLabel.grid(column=0, row=1, columnspan=3, pady=10)


    matchErrorLabel = tk.Label(app, text="", fg="red")
    matchErrorLabel.grid(column=0, row=4, columnspan=3)
    
    assignment_holder = {"data" : None}
    #define these subfunctions to avoid a weird loop scenario
    def on_rand_click(): 
        print("went in rand")
        assignment_holder["data"] = game_challenge(client,"random", None)
        app.quit()
    
    def on_spec():
        opponent = opponentEntry.get()
        if opponent.strip() == "":
            errorLabel.config(text="Enter username")
            return
        assignment_holder["data"] = game_challenge(client,"specific", opponent)
        app.quit()

    randomButton = tk.Button(app, text="Random Opponent",command=on_rand_click)
    randomButton.grid(column=0, row=2, columnspan=3, pady=5, padx=20, sticky="EW")
    print("made random button correct")
    opponentEntry = tk.Entry(app)
    opponentEntry.grid(column=1, row=3, pady=5)

    opponentButton = tk.Button(app, text="Specific Opponent",command=on_spec)
    opponentButton.grid(column=2, row=3, pady=5, padx=5)
    print("made spec button")
    while True: #Based on the on_rand and on_spec functions we will have the information in assignment holder
        app.mainloop() #Start a pause until the button is clicked

        if assignment_holder["data"]:
            app.withdraw() #Hide the buttons
            playGame(assignment_holder["data"]["width"],
                     assignment_holder["data"]["height"],
                     assignment_holder["data"]["paddle"],
                     client,
                     username) #We now call the button
            pygame.quit() #Close the window
            app.deiconify() #Brings the window back up
            assignment_holder["data"] = None #Reset so the user can challenge again
        else:
            break #We never get an assignment so we can just close this
    app.destroy()



# This displays the opening screen, you don't need to edit this (but may if you like)
def startScreen():
    app = tk.Tk()
    app.title("Server Info")

    image = tk.PhotoImage(file="./assets/images/logo.png")

    titleLabel = tk.Label(image=image)
    titleLabel.grid(column=0, row=0, columnspan=2)

    ipLabel = tk.Label(text="Server IP:")
    ipLabel.grid(column=0, row=1, sticky="W", padx=8)

    ipEntry = tk.Entry(app)
    ipEntry.grid(column=1, row=1)

    portLabel = tk.Label(text="Server Port:")
    portLabel.grid(column=0, row=2, sticky="W", padx=8)

    portEntry = tk.Entry(app)
    portEntry.grid(column=1, row=2)

    userLabel = tk.Label(text="Username:")
    userLabel.grid(column=0, row=3, sticky="W", padx=8)
    userEntry = tk.Entry(app)
    userEntry.grid(column=1,row=3)

    passLabel = tk.Label(text="Password:")
    passLabel.grid(column=0, row=4, sticky="W", padx=8)
    passEntry = tk.Entry(app)
    passEntry.grid(column=1,row=4)

    errorLabel = tk.Label(text="")
    errorLabel.grid(column=0, row=6, columnspan=2)
    if(userEntry.get() == "" or passEntry.get() == ""): ##Have  to come back and fix this so that we can loop this properly
        errorLabel = tk.Label(text="No NULL passwords or usernames")
        errorLabel.grid(column=0, row=6, columnspan=2)
    joinButton = tk.Button(text="Join", command=lambda: joinServer(ipEntry.get(), portEntry.get(), userEntry.get(), passEntry.get(), errorLabel, app))
    joinButton.grid(column=0, row=5, columnspan=2) ##CRASHES, no clue where lmao

    app.mainloop()

if __name__ == "__main__":
    startScreen()
    
    # Uncomment the line below if you want to play the game without a server to see how it should work
    # the startScreen() function should call playGame with the arguments given to it by the server this is
    # here for demo purposes only
    #playGame(640, 480,"left",socket.socket(socket.AF_INET, socket.SOCK_STREAM))
