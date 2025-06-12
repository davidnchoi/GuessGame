import socket
import random
import threading
import time

# Shared game state managed by the server
class GameState:
    def __init__(self):
        self.secret_number = 0
        self.active_clients = [] # List to hold (conn, addr) tuples
        self.game_in_progress = False
        self.lock = threading.Lock() # For thread-safe access to shared state
        self.reset_game()

    def reset_game(self):
        with self.lock:
            self.secret_number = random.randint(1, 101)
            self.game_in_progress = True
            print(f"New game started. Secret number is {self.secret_number}")

    def add_client(self, conn, addr):
        with self.lock:
            self.active_clients.append((conn, addr))

    def remove_client(self, conn):
        with self.lock:
            self.active_clients = [(c, a) for c, a in self.active_clients if c != conn]

    def end_game(self):
        with self.lock:
            self.game_in_progress = False

    def is_game_in_progress(self):
        with self.lock:
            return self.game_in_progress

    def broadcast(self, message):
        with self.lock:
            for conn, _ in self.active_clients:
                try:
                    conn.sendall(message.encode())
                except Exception as e:
                    print(f"Error broadcasting to client: {e}")

HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
PORT = 65432        # Port to listen on (non-privileged ports are > 1023)

game_state = GameState() # Global instance of our game state

def handle_client(conn, addr, client_id):
    print(f"Connected by {addr} (Client ID: {client_id})")
    game_state.add_client(conn, addr)

    initial_message = f"Welcome to the multiplayer guessing game!\nI'm thinking of a number between 1 and 100.\n".encode()
    conn.sendall(initial_message)

    attempts = 0
    while True:
        if not game_state.is_game_in_progress():
            # If game ended by another player, just send new game message and break
            conn.sendall(b"A new game has started!\nI'm thinking of a number between 1 and 100.\n")
            break

        try:
            data = conn.recv(1024)
            if not data:
                print(f"Client {client_id} disconnected normally")
                break

            try:
                guess = int(data.decode().strip())
                attempts += 1

                if guess < game_state.secret_number:
                    response = b"Too low! Try a higher number.\n"
                    conn.sendall(response)
                elif guess > game_state.secret_number:
                    response = b"Too high! Try a lower number.\n"
                    conn.sendall(response)
                else:
                    # Correct guess!
                    winner_message = f"Congratulations! Client {client_id} guessed the number {game_state.secret_number} in {attempts} attempts!\n"
                    game_state.broadcast(f"GAME OVER! {winner_message}\n")
                    
                    # This client also receives the winning message
                    conn.sendall(winner_message.encode())

                    game_state.end_game()
                    print(f"Game over. Client {client_id} won.")

                    # Wait a moment, then start a new game for all clients
                    time.sleep(3) # Give clients time to see the win message
                    game_state.reset_game()
                    game_state.broadcast(b"A new game has started!\n")
                    break # End this client's current game loop

            except ValueError:
                conn.sendall(b"Please enter a valid number between 1 and 100.\n")

        except ConnectionResetError:
            print(f"Client {client_id} forcibly disconnected")
            break
        except Exception as e:
            print(f"An error occurred with client {client_id}: {e}")
            break

    game_state.remove_client(conn)
    conn.close()

def start_server():
    print(f"Server starting...")
    print(f"Listening on {HOST}:{PORT}")

    client_id_counter = 0

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print("Waiting for connections...")

        while True:
            conn, addr = s.accept()
            client_id_counter += 1
            client_handler = threading.Thread(target=handle_client, args=(conn, addr, client_id_counter))
            client_handler.start()

if __name__ == "__main__":
    start_server() 