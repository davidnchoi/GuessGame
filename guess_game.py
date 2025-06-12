import random
import tkinter as tk
from tkinter import messagebox
import socket
import threading
import json

class GuessingGameGUI:
    def __init__(self, master):
        self.master = master
        master.title("Multiplayer Number Guessing Game")
        
        # Set window to fullscreen and bind escape key
        master.attributes('-fullscreen', True)
        master.bind('<Escape>', lambda e: master.attributes('-fullscreen', False))
        
        # Set background color for the main window
        master.config(bg="black")
        
        # Configure grid for centering
        for i in range(8): # Increased rows for new elements
            master.grid_rowconfigure(i, weight=1)
        master.grid_columnconfigure(0, weight=1)

        # Network variables
        self.client_socket = None
        self.is_connected = False
        self.receive_thread = None

        # UI Elements
        self.title_label = tk.Label(master, text="Multiplayer Number Guessing Game!", font=("Arial", 30, "bold"), fg="white", bg="black")
        self.title_label.grid(row=0, column=0, pady=10)

        self.ip_label = tk.Label(master, text="Server IP:", font=("Arial", 16), fg="white", bg="black")
        self.ip_label.grid(row=1, column=0, pady=5, sticky="e")
        self.ip_entry = tk.Entry(master, width=15, font=("Arial", 16), justify='center', fg="white", bg="#333333", insertbackground="white")
        self.ip_entry.grid(row=1, column=0, pady=5, sticky="w", padx=(200,0))
        self.ip_entry.insert(0, "127.0.0.1") # Default to localhost

        self.port_label = tk.Label(master, text="Port:", font=("Arial", 16), fg="white", bg="black")
        self.port_label.grid(row=2, column=0, pady=5, sticky="e")
        self.port_entry = tk.Entry(master, width=10, font=("Arial", 16), justify='center', fg="white", bg="#333333", insertbackground="white")
        self.port_entry.grid(row=2, column=0, pady=5, sticky="w", padx=(200,0))
        self.port_entry.insert(0, "65432") # Default port

        self.connect_button = tk.Button(master, text="Connect to Server", command=self.connect_to_server, font=("Arial", 14), fg="white", bg="#555555")
        self.connect_button.grid(row=3, column=0, pady=10)

        self.status_label = tk.Label(master, text="Not Connected", font=("Arial", 14), fg="gray", bg="black")
        self.status_label.grid(row=4, column=0, pady=5)

        self.instruction_label = tk.Label(master, text="", font=("Arial", 18), fg="white", bg="black")
        self.instruction_label.grid(row=5, column=0, pady=5)
        
        self.feedback_label = tk.Label(master, text="", font=("Arial", 16), fg="white", bg="black")
        self.feedback_label.grid(row=6, column=0, pady=10)

        self.guess_entry = tk.Entry(master, width=10, font=("Arial", 16), justify='center', fg="white", bg="#333333", insertbackground="white")
        self.guess_entry.grid(row=7, column=0, pady=5)
        self.guess_entry.bind("<Return>", self.send_guess_event)
        self.guess_entry.config(state='disabled') # Disable until connected

        self.guess_button = tk.Button(master, text="Guess", command=self.send_guess, font=("Arial", 14), fg="white", bg="#555555")
        self.guess_button.grid(row=8, column=0, pady=10)
        self.guess_button.config(state='disabled') # Disable until connected
        
        self.other_players_feedback = tk.Text(master, height=5, width=50, font=("Arial", 12), state='disabled', fg="white", bg="#333333")
        self.other_players_feedback.grid(row=9, column=0, pady=10)
        
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing) # Handle window close event

    def connect_to_server(self):
        host = self.ip_entry.get()
        port = int(self.port_entry.get()) # Ensure port is integer

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((host, port))
            self.is_connected = True
            self.status_label.config(text=f"Connected to {host}:{port}", fg="green")
            self.connect_button.config(text="Disconnect", command=self.disconnect_from_server, bg="red")
            self.guess_entry.config(state='normal')
            self.guess_button.config(state='normal')
            self.guess_entry.focus_set()
            self.other_players_feedback.config(state='normal') # Enable for writing
            self.other_players_feedback.delete(1.0, tk.END)
            self.other_players_feedback.config(state='disabled') # Disable after clearing

            # Start receiving messages in a separate thread
            self.receive_thread = threading.Thread(target=self.receive_messages, daemon=True)
            self.receive_thread.start()

        except ConnectionRefusedError:
            self.status_label.config(text="Connection Refused! Server might be offline.", fg="red")
        except ValueError:
            self.status_label.config(text="Invalid IP or Port. Please check your input.", fg="red")
        except Exception as e:
            self.status_label.config(text=f"Error connecting: {e}", fg="red")

    def disconnect_from_server(self):
        if self.is_connected:
            self.is_connected = False
            self.client_socket.close()
            self.status_label.config(text="Disconnected", fg="red")
            self.connect_button.config(text="Connect to Server", command=self.connect_to_server, bg="#555555")
            self.guess_entry.config(state='disabled')
            self.guess_button.config(state='disabled')
            self.instruction_label.config(text="", fg="white")
            self.feedback_label.config(text="", fg="white")
            self.other_players_feedback.config(state='normal')
            self.other_players_feedback.delete(1.0, tk.END)
            self.other_players_feedback.config(state='disabled')
            if self.receive_thread and self.receive_thread.is_alive():
                self.receive_thread.join(timeout=1) # Give it a moment to finish

    def receive_messages(self):
        while self.is_connected:
            try:
                data = self.client_socket.recv(1024).decode().strip()
                if data:
                    self.update_gui_with_message(data)
                else:
                    # Server disconnected
                    print("Server disconnected.")
                    self.disconnect_from_server()
                    break
            except OSError as e:
                if self.is_connected: # Only print if not intentionally disconnected
                    print(f"Socket error during receive: {e}")
                self.disconnect_from_server()
                break
            except Exception as e:
                print(f"Error receiving messages: {e}")
                self.disconnect_from_server()
                break

    def update_gui_with_message(self, message):
        # Use after() to update GUI from a non-GUI thread
        self.master.after(0, lambda: self._update_feedback_label(message))

    def _update_feedback_label(self, message):
        if "Welcome to the multiplayer guessing game!" in message:
            self.instruction_label.config(text="I'm thinking of a number between 1 and 100.", fg="white")
            self.feedback_label.config(text="", fg="white") # Clear previous feedback
        elif "Too low!" in message or "Too high!" in message:
            if "Client" in message: # This is feedback for another player
                self.other_players_feedback.config(state='normal')
                self.other_players_feedback.insert(tk.END, message + "\n")
                self.other_players_feedback.see(tk.END) # Scroll to bottom
                self.other_players_feedback.config(state='disabled')
            else: # This is feedback for the current player
                self.feedback_label.config(text=message, fg="white")
        elif "Congratulations!" in message:
            self.feedback_label.config(text=message, fg="green")
            self.guess_entry.config(state='disabled')
            self.guess_button.config(state='disabled')
            self.other_players_feedback.config(state='normal')
            self.other_players_feedback.insert(tk.END, message + "\n")
            self.other_players_feedback.see(tk.END)
            self.other_players_feedback.config(state='disabled')
        elif "GAME OVER!" in message:
            # The server will send this before the new game message, so we just clear for new game
            self.feedback_label.config(text=message, fg="purple")
            self.instruction_label.config(text="", fg="white")
            self.guess_entry.config(state='disabled')
            self.guess_button.config(state='disabled')
            self.other_players_feedback.config(state='normal')
            self.other_players_feedback.insert(tk.END, message + "\n")
            self.other_players_feedback.see(tk.END)
            self.other_players_feedback.config(state='disabled')

        elif "A new game has started!" in message:
            self.instruction_label.config(text="A new game has started! I'm thinking of a number between 1 and 100.", fg="white")
            self.feedback_label.config(text="", fg="white")
            self.guess_entry.config(state='normal')
            self.guess_button.config(state='normal')
            self.guess_entry.focus_set()
            self.other_players_feedback.config(state='normal')
            self.other_players_feedback.delete(1.0, tk.END)
            self.other_players_feedback.config(state='disabled')
            self.guess_entry.delete(0, tk.END)
            self.status_label.config(text="Connected", fg="green") # Reset status after new game
        else:
            # For any other general messages from the server
            self.feedback_label.config(text=message, fg="blue")

    def send_guess_event(self, event):
        self.send_guess()

    def send_guess(self):
        if self.is_connected:
            guess = self.guess_entry.get().strip()
            if guess.isdigit():
                try:
                    self.client_socket.sendall(guess.encode())
                    self.guess_entry.delete(0, tk.END)
                except Exception as e:
                    self.feedback_label.config(text=f"Error sending guess: {e}", fg="red")
                    self.disconnect_from_server()
            else:
                self.feedback_label.config(text="Please enter a valid number.", fg="red")
        else:
            self.status_label.config(text="Not connected to server.", fg="red")

    def on_closing(self):
        if self.is_connected:
            self.disconnect_from_server()
        self.master.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    game = GuessingGameGUI(root)
    root.mainloop() 