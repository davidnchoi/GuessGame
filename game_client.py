import socket

HOST = '127.0.0.1'  # The server's hostname or IP address
PORT = 65432        # The port used by the server

def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
            print(f"Connected to server at {HOST}:{PORT}")

            # Receive initial welcome messages
            initial_messages = s.recv(1024).decode()
            print(initial_messages.strip())

            while True:
                guess_input = input("Enter your guess: ")
                s.sendall(guess_input.encode())

                response = s.recv(1024).decode()
                print(response.strip())

                if "Congratulations!" in response:
                    break # Game over for this client

        except ConnectionRefusedError:
            print(f"Connection refused. Make sure the server is running at {HOST}:{PORT}")
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    start_client() 