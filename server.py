import tkinter as tk
from tkinter import ttk, filedialog
import socket
import threading
import os
import logging
import time
from datetime import datetime

class FileServer:
    def __init__(self):
        # Create the root window for the GUI
        self.root = tk.Tk()
        self.root.title("Cloud File System Server")  # Set the title of the window
        self.root.geometry("800x600")  # Set the initial size of the window
        self.root.minsize(600, 500)  # Set the minimum size of the window
        
        # Server variables
        self.server_socket = None  # Placeholder for the server socket object
        self.is_running = False  # Boolean flag to track if the server is running
        self.clients = {}  # Dictionary to keep track of connected clients
        self.upload_dir = os.path.join(os.getcwd(), "uploaded_files")  # Default folder for uploaded files
        self.chunk_size = 4096  # Size of data chunks to be sent/received over the socket (in bytes)
        self.socket_timeout = 30  # Timeout for the socket operations in seconds
        self.used_usernames = set()  # Set to track usernames that have ever connected

        # Logger settings
        self.setup_logger()  # Initialize the logger for server activities
        
        # Create GUI components
        self.setup_gui()  # Setup the graphical user interface components
        
        # Capture the window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)  # Define actions to perform on window close


    def setup_logger(self):
        # Configure logging settings
        logging.basicConfig(
            level=logging.INFO,  # Set logging level to INFO
            format='%(asctime)s - %(levelname)s - %(message)s',  # Define the log message format
            handlers=[
                logging.FileHandler('server.log'),  # Save log messages to a file named 'server.log'
                logging.StreamHandler()  # Also output log messages to the console
            ]
        )
        # Create a logger instance for the class
        self.logger = logging.getLogger(__name__)


    def setup_gui(self):
        # Main container for the GUI
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Server control frame
        control_frame = ttk.LabelFrame(self.main_container, text="Server Control")
        control_frame.pack(fill=tk.X, padx=5, pady=5)

        # Frame for port and folder settings
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill=tk.X, padx=5, pady=5)

        # Port settings
        port_frame = ttk.Frame(settings_frame)
        port_frame.pack(fill=tk.X, padx=5, pady=5)
            
        # Port label and entry field
        ttk.Label(port_frame, text="Port:").pack(side=tk.LEFT, padx=(0, 5))
        self.port_entry = ttk.Entry(port_frame, width=10)
        self.port_entry.insert(0, "12345")  # Default port value
        self.port_entry.pack(side=tk.LEFT)

        # Folder selection
        folder_frame = ttk.Frame(settings_frame)
        folder_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Folder label and entry field
        ttk.Label(folder_frame, text="File:").pack(side=tk.LEFT, padx=(0, 5))
        self.folder_entry = ttk.Entry(folder_frame)
        self.folder_entry.insert(0, self.upload_dir)  # Default folder path
        self.folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Browse button to select a folder
        self.browse_button = ttk.Button(
            folder_frame,
            text="Browse",
            command=self.browse_folder  # Calls browse_folder method when clicked
        )
        self.browse_button.pack(side=tk.LEFT)

        # Start/Stop button to toggle the server state
        self.toggle_button = ttk.Button(
            settings_frame, 
            text="Start Server",
            command=self.toggle_server  # Calls toggle_server method when clicked
        )
        self.toggle_button.pack(pady=10)

        # Log frame to display server logs
        log_frame = ttk.LabelFrame(self.main_container, text="Server Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Container for the log text area and scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Scrollbar for the log text area
        scrollbar = ttk.Scrollbar(log_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Log text area for displaying log messages
        self.log_text = tk.Text(
            log_container,
            yscrollcommand=scrollbar.set,  # Connect scrollbar to the text widget
            wrap=tk.WORD,
            height=20
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure scrollbar to control the log text view
        scrollbar.config(command=self.log_text.yview)

            
    def log_message(self, message, level="INFO"):
        # Create a timestamp for the log message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}\n"
        
        # Add the log message to the GUI log text area
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)  # Scroll to the end to show the latest message
        
        # Save the log message to the log file
        if level == "INFO":
            self.logger.info(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "WARNING":
            self.logger.warning(message)
        
        # Update the GUI to reflect the changes
        self.root.update_idletasks()

    def run(self):
        # Start the main event loop for the GUI
        self.root.mainloop()

    def toggle_server(self):
        # Start or stop the server based on its current status
        if not self.is_running:
            try:
                # Check if the folder selection is valid
                selected_folder = self.folder_entry.get().strip()
                if not selected_folder:
                    self.log_message("Please choose a folder!", "ERROR")
                    return
                    
                # Update the upload directory
                self.upload_dir = selected_folder
                # Create the folder if it does not exist
                try:
                    os.makedirs(self.upload_dir, exist_ok=True)
                    self.log_message(f"Running folder: {self.upload_dir}")
                except Exception as e:
                    self.log_message(f"Folder creation error: {str(e)}", "ERROR")
                    return

                # Validate the port number
                port = int(self.port_entry.get())
                if not 1024 <= port <= 65535:
                    self.log_message("Port number must be between 1024 and 65535!", "ERROR")
                    return
                    
                # Create and configure the server socket
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.settimeout(self.socket_timeout)
                self.server_socket.bind(('0.0.0.0', port))
                self.server_socket.listen(5)
                    
                # Update server status and GUI controls
                self.is_running = True
                self.toggle_button.config(text="Stop Server")
                self.port_entry.config(state='disabled')
                self.folder_entry.config(state='disabled')
                self.browse_button.config(state='disabled')
                    
                # Start a new thread to accept client connections
                self.accept_thread = threading.Thread(target=self.accept_connections)
                self.accept_thread.daemon = True
                self.accept_thread.start()
                    
                self.log_message(f"Server started on port {port}!")
                
            except Exception as e:
                # Log error message if the server fails to start
                self.log_message(f"Server starting error: {str(e)}", "ERROR")
                self.cleanup_server()
        else:
            # Stop the server if it is currently running
            self.cleanup_server()
            self.log_message("Server stopped.")

    def browse_folder(self):
            # Open a dialog to select a folder
            folder = filedialog.askdirectory(
                title="Choose file folder",
                initialdir=self.upload_dir
            )
            if folder:
                # Get the absolute path of the selected folder
                self.upload_dir = os.path.abspath(folder) 
                # Update the folder entry field with the selected path 
                self.folder_entry.delete(0, tk.END)
                self.folder_entry.insert(0, self.upload_dir)
                # Check and create the folder if it doesn't exist
                try:
                    os.makedirs(self.upload_dir, exist_ok=True)
                    self.log_message(f"Running folder is changed: {self.upload_dir}")
                    
                    # If the server is running, stop it and restart with the new folder
                    if self.is_running:
                        self.cleanup_server()
                        self.toggle_server()
                except Exception as e:
                    self.log_message(f"Folder creation error: {str(e)}", "ERROR")
    
    def cleanup_server(self):
        # Set server status to not running
        self.is_running = False
        # Close all client connections
        for username, client in self.clients.items():
            try:
                client.close()
                self.log_message(f"{username} disconnected")
            except Exception as e:
                self.log_message(f"Error: {str(e)}", "ERROR")
        # Clear all client entries
        self.clients.clear()
        
        # Close the server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except Exception as e:
                self.log_message(f"Error: {str(e)}", "ERROR")
            # Set server socket to None after closing
            self.server_socket = None
        
        # Update the GUI to reflect the server stopped state
        self.toggle_button.config(text="Start Server")
        self.port_entry.config(state='normal')
        self.folder_entry.config(state='normal')
        self.browse_button.config(state='normal')

    def accept_connections(self):
            # Continuously accept incoming client connections while the server is running
            while self.is_running:
                try:
                    # Accept a new client connection
                    client_socket, address = self.server_socket.accept()
                    # Set the socket timeout for the client
                    client_socket.settimeout(self.socket_timeout)
                    
                    # Start a new thread to handle the client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True  # Set thread as daemon to exit when main program exits
                    client_thread.start()
                    
                except socket.timeout as e:
                    # Log a warning if the socket times out while waiting for a connection
                    self.log_message(f"Accept timeout: {str(e)}", "WARNING")
                    continue
                except Exception as e:
                    # Log any other exceptions that occur while accepting connections
                    if self.is_running:
                        self.log_message(f"Connection accept error: {str(e)}", "ERROR")

    def safe_send(self, socket, message, retries=3, timeout=5.0):
        # Store the original timeout of the socket
        original_timeout = socket.gettimeout()
        # Set the socket timeout for the send operation
        socket.settimeout(timeout)
        
        try:
            # Attempt to send the message up to the specified number of retries
            for attempt in range(retries):
                try:
                    # If the message is a string, encode it to bytes
                    if isinstance(message, str):
                        message = message.encode()
                    # Send the entire message to the socket
                    socket.sendall(message)
                    return True  # Return True if the message is successfully sent
                except socket.timeout as e:
                    # Log a warning if sending times out
                    self.log_message(f"Send timeout, attempt {attempt + 1}/{retries}: {str(e)}", "WARNING")
                    if attempt < retries - 1:
                        time.sleep(1)  # Wait before retrying
                except Exception as e:
                    # Log any other error that occurs during sending
                    self.log_message(f"Send error: {str(e)}", "ERROR")
                    break
            # Return False if all attempts fail
            return False
        finally:
            # Restore the original socket timeout
            socket.settimeout(original_timeout)

    def safe_receive(self, socket, buffer_size=4096, retries=3, timeout=5.0):
        # Store the original timeout of the socket
        original_timeout = socket.gettimeout()
        # Set the socket timeout for the receive operation
        socket.settimeout(timeout)
        
        try:
            # Attempt to receive data up to the specified number of retries
            for attempt in range(retries):
                try:
                    # Receive data from the socket with the specified buffer size
                    data = socket.recv(buffer_size)
                    if data:
                        # Decode data if it is in bytes format
                        decoded_data = data.decode() if isinstance(data, bytes) else data
                        # Log an error if the received data starts with "ERROR"
                        if decoded_data.startswith("ERROR"):
                            self.log_message(decoded_data, "ERROR")
                        return decoded_data  # Return the received data
                    return None  # Return None if no data is received
                except socket.timeout as e:
                    # Log a warning if receiving times out
                    self.log_message(f"Receive timeout, attempt {attempt + 1}/{retries}: {str(e)}", "WARNING")
                    if attempt < retries - 1:
                        time.sleep(1)  # Wait before retrying
                except Exception as e:
                    # Log any other error that occurs during receiving
                    self.log_message(f"Receive error: {str(e)}", "ERROR")
                    break
            # Return None if all attempts fail
            return None
        finally:
            # Restore the original socket timeout
            socket.settimeout(original_timeout)

    def on_closing(self):
        # Handle the closing event for the application window
        if self.is_running:
            # Stop the server if it is running
            self.cleanup_server()
        # Quit the main GUI loop
        self.root.quit()


    def handle_client(self, client_socket, address):
        username = None
        try:
            # Remove the socket timeout for the client
            client_socket.settimeout(None)
            # Receive the username from the client
            username = self.safe_receive(client_socket)
            
            if not username:
                client_socket.close()
                return
            
            # Check if the username has ever been used before
            if username in self.used_usernames:
                self.safe_send(client_socket, "ERROR: This username has been used before and is blocked!")
                client_socket.close()  # Close the connection immediately
                return
            
            # Check if the username is currently taken by another client
            if username in self.clients:
                self.safe_send(client_socket, "ERROR: This username is taken!")
                client_socket.close()  # Close the connection immediately
                return
            
            # If we reach here, the username is available for new connection
            self.used_usernames.add(username)   # Mark this username as used permanently
            self.clients[username] = client_socket
            self.safe_send(client_socket, "SUCCESS: Connection is successful!")
            self.log_message(f"New connection: {username} ({address[0]}:{address[1]})")
            
            # Handle incoming commands from the client while the server is running
            while self.is_running:
                try:
                    command = self.safe_receive(client_socket)
                    if not command:
                        continue
                    
                    if command == "EXIT":
                        break
                    
                    command_parts = command.split('|')
                    command_type = command_parts[0]
                    
                    if command_type in ["UPLOAD", "DOWNLOAD", "LIST", "DELETE", "UPDATE"]:
                        handler = getattr(self, f"handle_{command_type.lower()}")
                        handler(client_socket, username, command)
                        
                except ConnectionResetError as e:
                    self.log_message(f"Connection reset error: {str(e)}", "WARNING")
                    break
                except Exception as e:
                    if self.is_running:
                        self.log_message(f"Client error: {str(e)}", "ERROR")
            
        finally:
            # Ensure the client is removed from the clients dictionary and the socket is closed
            if username in self.clients:
                del self.clients[username]
                self.log_message(f"{username} disconnected")
            client_socket.close()


    def send_notification(self, username, message):
        try:
            # Check if the username is in the list of connected clients
            if username in self.clients:
                notification = f"NOTIFICATION|{message}"
                # Send the notification to the specified client
                if self.safe_send(self.clients[username], notification):
                    # Log a success message if the notification was sent successfully
                    self.log_message(f"Notification sent -> {username}: {message}")
                else:
                    # Log an error if the notification failed to send
                    self.log_message(f"Notification did not send: {username}", "ERROR")
        except Exception as e:
            # Log an error if any exceptions occur while sending the notification
            self.log_message(f"Notification error ({username}): {str(e)}", "ERROR")


    def handle_list(self, client_socket, username, data=None):
        try:
            # Check if the upload directory exists, and create it if not
            if not os.path.exists(self.upload_dir):
                os.makedirs(self.upload_dir)
                
            # List all files in the upload directory
            files = os.listdir(self.upload_dir)
            if not files:
                response = "There is no file in server."
            else:
                response = "\n".join(files)  # Join all filenames with a newline
            
            # Use the safe send function to send the file list to the client
            if self.safe_send(client_socket, response, retries=3, timeout=5.0):
                self.log_message(f"File list sent: {username}")
            else:
                self.log_message(f"File list did not send: {username}", "ERROR")
                
        except Exception as e:
            # Handle any errors that occur during file listing
            error_msg = f"File listing error: {str(e)}"
            self.safe_send(client_socket, f"ERROR: {error_msg}")
            self.log_message(error_msg, "ERROR")

    def verify_file_ownership(self, username, filename):
        # Check if the file belongs to the specified user by verifying the filename prefix
        if not filename.startswith(f"{username}_"):
            return False, "You do not have permission on this file."
        
        # Verify if the file exists in the upload directory
        filepath = os.path.join(self.upload_dir, filename)
        if not os.path.exists(filepath):
            return False, "File cannot be found."
        
        # If checks pass, return True along with the file path
        return True, filepath

    
    def handle_upload(self, client_socket, username, data):
        try:
            # Parse the command to get filename and filesize
            _, filename, filesize = data.split('|')
            filesize = int(filesize)

             # Construct the server filename with the user's name as a prefix
            server_filename = f"{username}_{filename}"
            filepath = os.path.join(self.upload_dir, server_filename)
            
            self.log_message(f"File uploading started: {server_filename} ({self.format_size(filesize)})")
            
            # Initialize variables for file receiving
            total_received = 0
            start_time = time.time()
            
            # Receive the file and write it to the specified path
            with open(filepath, 'wb') as f:
                while total_received < filesize:
                    # Calculate the size of the next chunk to receive
                    chunk_size = min(self.chunk_size, filesize - total_received)
                    try:
                        # Receive a chunk of data from the client
                        chunk = client_socket.recv(chunk_size)
                        if not chunk:
                            raise Exception("Connection failed")
                        # Write the received chunk to the file
                        f.write(chunk)
                        total_received += len(chunk)
                        
                        # Update the progress log every 10 chunks
                        if total_received % (self.chunk_size * 10) == 0:  
                            progress = (total_received / filesize) * 100
                            speed = total_received / (time.time() - start_time)
                            status = f"Loading: %{progress:.1f} - Speed: {self.format_size(speed)}/s"
                            self.log_message(status)
                            
                    except socket.timeout as e:
                        # Continue if a socket timeout occurs during receiving
                        continue
                    except Exception as e:
                        # Raise an exception if any other error occurs while receiving data
                        raise Exception(f"Data receiving error: {str(e)}")
            
            # Send success message to client once the file is successfully uploaded
            self.safe_send(client_socket, "SUCCESS: File successfully uploaded!")
            self.log_message(f"File successfully uploaded: {server_filename}")
            
        except Exception as e:
            # Handle any errors that occur during the upload process
            error_msg = f"File uploading error: {str(e)}"
            self.safe_send(client_socket, f"ERROR: {error_msg}")
            self.log_message(error_msg, "ERROR")

    def handle_download(self, client_socket, username, data):
        """
        It meets the "DOWNLOAD|fileName" command on the server.
        1) It finds the file owner, if the downloader is different, it sends NOTIFICATION.
        2) It waits for a 'READY' signal from the client.
        3) It sends the file in 65536 byte chunks.
        4) It sets the timeout to 600 seconds or you can make it None if you want.
        """
        original_timeout = client_socket.gettimeout()
        try:
            #1) We increase the Timeout (example: 10 minutes = 600 sec)
            client_socket.settimeout(600)

            # Command format: "DOWNLOAD|fileName"
            _, filename = data.split('|', 1)
            filepath = os.path.join(self.upload_dir, filename)

            # Does the file exist?
            if not os.path.exists(filepath):
                client_socket.send(b"ERROR: Cannot find file\u0131.")
                return

            # Notify the file owner (downloader = username)
            owner = filename.split('_')[0]
            if owner != username and owner in self.clients:
                # NOTIFICATION
                msg = f"NOTIFICATION|{username} is downloading your {filename} file."
                self.clients[owner].send(msg.encode())
                self.log_message(f"Notification sent -> {owner}: {msg}")

            #2) Get size, send title
            filesize = os.path.getsize(filepath)
            header = f"DOWNLOAD|{filename}|{filesize}".encode()
            client_socket.sendall(header)

            # 3) READY wait
            try:
                ready = client_socket.recv(1024).decode()
                if ready != "READY":
                    return
            except Exception:
                return

            # 4) Send file in chunks
            self.log_message(f"Starting file transfer: {filename} to {username}")
            with open(filepath, 'rb') as f:
                bytes_sent = 0
                while bytes_sent < filesize:
                    chunk = f.read(min(65536, filesize - bytes_sent))
                    if not chunk:
                        break
                    client_socket.sendall(chunk)
                    bytes_sent += len(chunk)

            self.log_message(f"File sent: {filename} ({username}) - {self.format_size(filesize)}")

        except Exception as e:
            error_msg = f"File downloading error\u0131: {str(e)}"
            self.log_message(error_msg, "ERROR")
            try:
                client_socket.send(error_msg.encode())
            except Exception:
                pass

        finally:
            # You can reset the timeout (optional)
            # client_socket.settimeout(original_timeout)
            pass


    
    def handle_delete(self, client_socket, username, data):
        try:
            # Parse the command to get the filename
            _, filename = data.split('|')
            filepath = os.path.join(self.upload_dir, filename)
            
            # Check file ownership by verifying the prefix of the filename
            owner = filename.split('_')[0]  
            
            # If the user is not the owner, they don't have permission to delete the file
            if owner != username:
                self.safe_send(client_socket, "ERROR: You do not have permission on this file.")
                
                # Notify the file owner about the unauthorized delete attempt
                if owner in self.clients:
                    notification = f"NOTIFICATION|{username} tried to delete your {filename} named file."
                    self.clients[owner].send(notification.encode())
                return

            # Attempt to delete the file 
            try:
                os.remove(filepath)
                # Notify the client of the successful deletion
                self.safe_send(client_socket, "SUCCESS: File successfully deleted.")
                # Log the file deletion event
                self.log_message(f"File deleted: {filename} ({username})")
            except PermissionError as e:
                # Raise an exception if there are issues with file permissions
                raise Exception("File is not deletable: Access denied")
            except FileNotFoundError as e:
                # Raise an exception if the file doesn't exist
                raise Exception("File could not found.")
                
        except Exception as e:
            # Handle any errors that occur during the delete process
            error_msg = f"File deletion error: {str(e)}"
            # Send an error message back to the client
            self.safe_send(client_socket, f"ERROR: {error_msg}")
            # Log the error
            self.log_message(error_msg, "ERROR")

    def handle_update(self, client_socket, username, data):
        try:
            # Parse the command to get the old filename, new filename, and file size
            _, old_filename, new_filename, filesize = data.split('|')
            filesize = int(filesize)
            filepath = os.path.join(self.upload_dir, old_filename)
             # Check file ownership to ensure user has permission to update the file
            is_owner, message = self.verify_file_ownership(username, old_filename)
            if not is_owner:
                # Send an error message if the user does not own the file
                self.safe_send(client_socket, f"ERROR: {message}")
                return
            
            filepath = os.path.join(self.upload_dir, old_filename)
            
            self.log_message(f"File updating started: {old_filename}")
            
             # Start receiving the new version of the file
            total_received = 0
            start_time = time.time()
            
             # Open the file in write-binary mode to overwrite the content
            with open(filepath, 'wb') as f:
                while total_received < filesize and self.is_running:
                    # Determine the chunk size to receive
                    chunk_size = min(self.chunk_size, filesize - total_received)
                    try:
                        # Receive a chunk of the file from the client
                        chunk = client_socket.recv(chunk_size)
                        if not chunk:
                            raise Exception("Connection failed")
                        
                        # Write the received chunk to the file
                        f.write(chunk)
                        total_received += len(chunk)
                        
                        # Update progress log every 10 chunks
                        if total_received % (self.chunk_size * 10) == 0:
                            progress = (total_received / filesize) * 100
                            speed = total_received / (time.time() - start_time)
                            status = f"Updating: %{progress:.1f} - Hız: {self.format_size(speed)}/s"
                            self.log_message(status)
                            
                    except socket.timeout as e:
                        # Continue if a socket timeout occurs during receiving
                        continue
                    except Exception as e:
                        # Raise an exception if any other error occurs while receiving data
                        raise Exception(f"Data receiving error: {str(e)}")
            
            # Send success message to client once the file is successfully updated
            self.safe_send(client_socket, "SUCCESS: File successfully updated!")
            self.log_message(f"File successfully updated: {old_filename}")
            
        except Exception as e:
            # Handle any errors that occur during the update process
            error_msg = f"File updating error: {str(e)}"
            # Send an error message back to the client
            self.safe_send(client_socket, f"ERROR: {error_msg}")
            # Log the error
            self.log_message(error_msg, "ERROR")

    def start_auto_cleanup(self):
        # Define a function to run in a separate thread to clean up disconnected clients
        def cleanup_loop():
            while self.is_running:
                disconnected_users = []
                # Iterate through all connected clients
                for username, client in self.clients.items():
                    try:
                        # Check if the connection is still alive by setting a short timeout
                        client.settimeout(1)
                        client.send(b'') # Send an empty byte to verify connection
                    except Exception as e:
                        # If an error occurs, consider the client disconnected
                        disconnected_users.append(username)
                
                # Remove all disconnected clients from the list of active clients
                for username in disconnected_users:
                    if username in self.clients:
                        del self.clients[username]
                        self.log_message(f"Connection failed: {username}")
                        
                
                time.sleep(30)  # Wait for 30 seconds before the next cleanup check
        
        # Start the cleanup process in a separate thread
        cleanup_thread = threading.Thread(target=cleanup_loop)
        cleanup_thread.daemon = True # Set thread as a daemon to run in the background
        cleanup_thread.start()

    def format_size(self, size):
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size)
        unit = 0
        while size >= 1024 and unit < len(units) - 1:
            size /= 1024
            unit += 1
        return f"{size:.2f} {units[unit]}"

if __name__ == "__main__":
    try:
        # Create an instance of the FileServer class
        server = FileServer()
        # Start the automatic cleanup process
        server.start_auto_cleanup()
        # Run the server application
        server.run()
    except Exception as e:
        # Print any critical errors that occur during the server operation
        print(f"Critical error: {str(e)}")