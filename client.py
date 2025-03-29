import tkinter as tk
from tkinter import ttk, filedialog
import socket
import os
import threading
import time

class FileClient:
    def __init__(self, root):
        # Initialize the main GUI window
        self.root = root
        self.root.title("Cloud File System Client")  # Set the window title
        
        # Initialize socket and connection status
        self.socket = None
        self.connected = False
        self.username = ""  # Store the client's username
        self.is_downloading = False
        self.chunk_size = 4096  # Set the chunk size for data transfer
        
        # Set up the GUI components for the client application
        self.setup_gui()
        
        # Start a separate thread to check for notifications from the server
        self.notification_thread = threading.Thread(target=self.check_notifications, daemon=True)
        self.notification_thread.start()
        
        # Capture the event for closing the window and handle it properly
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
    def download_file(self):
        if not self.connected:
            self.log_message("You are not connected to server!", "ERROR")
            return

        try:
            # Get file list from server
            self.socket.send("LIST".encode())
            response = self.socket.recv(4096).decode()

            if "There is no file in server." in response:
                self.log_message("There is no file in server.")
                return

            # Window for file selection
            file_window = tk.Toplevel(self.root)
            file_window.title("Download File")
            file_window.geometry("400x300")
            file_window.transient(self.root)

            frame = ttk.Frame(file_window)
            frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            scrollbar = ttk.Scrollbar(frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            listbox = tk.Listbox(frame, yscrollcommand=scrollbar.set)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)

            files = [f.strip() for f in response.split('\n') if f.strip()]
            for file in files:
                listbox.insert(tk.END, file)

            def start_download():
                if not listbox.curselection():
                    self.log_message("Please choose a file!", "ERROR")
                    return

                selected_file = listbox.get(listbox.curselection())
                file_window.destroy()

                try:
                    ### 1) Increase the timeout (e.g. 600 sec = 10 minutes) or remove it
                    original_timeout = self.socket.gettimeout()
                    self.socket.settimeout(600)  # Örnek: 10 dakika

                    try:
                        # Send DOWNLOAD request
                        self.socket.send(f"DOWNLOAD|{selected_file}".encode())

                        # Get response from server: "DOWNLOAD|filename|filesize" or "ERROR: ..."
                        response = self.socket.recv(1024).decode()
                        if not response:
                            raise Exception("No response from server")
                        if response.startswith("ERROR"):
                            raise Exception(response)

                        # 2) Parse file information
                        parts = response.split('|')
                        if len(parts) != 3:
                            raise Exception("Invalid server response")

                        _, filename, filesize_str = parts
                        filesize = int(filesize_str.strip())

                        # 3) Save location
                        save_path = filedialog.asksaveasfilename(
                            initialfile=filename,
                            defaultextension=os.path.splitext(filename)[1]
                        )
                        if not save_path:
                            return

                        self.log_message(f"{filename} downloading...")

                        # 4) İndirme ilerlemesi penceresi
                        progress_window = tk.Toplevel(self.root)
                        progress_window.title("Download Progress")
                        progress_window.geometry("300x150")

                        progress_var = tk.DoubleVar()
                        progress_bar = ttk.Progressbar(progress_window, variable=progress_var, maximum=100)
                        progress_bar.pack(pady=10, padx=10, fill=tk.X)

                        status_label = ttk.Label(progress_window, text="0%")
                        status_label.pack(pady=5)

                        # 5) Send "READY" message to server
                        self.socket.send("READY".encode())

                        ### 2) Large file import
                        try:
                            received = 0
                            start_time = time.time()
                            last_update_time = start_time

                            with open(save_path, 'wb') as f:
                                # recv until the file is completely downloaded
                                while received < filesize:
                                    # You can make the chunk size (8192) even larger (e.g. 65536)
                                    chunk_size = min(65536, filesize - received)
                                    chunk = self.socket.recv(chunk_size)
                                    if not chunk:
                                        # In case of disconnection
                                        break

                                    f.write(chunk)
                                    received += len(chunk)

                                    # 6) Progress update
                                    current_time = time.time()
                                    if current_time - last_update_time >= 0.1:
                                        if progress_window.winfo_exists():
                                            progress = (received / filesize) * 100
                                            progress_var.set(progress)

                                            speed = received / (current_time - start_time)
                                            status = (f"%{progress:.1f} - "
                                                    f"{self.format_size(received)}/"
                                                    f"{self.format_size(filesize)} - "
                                                    f"{self.format_size(speed)}/s")
                                            status_label.config(text=status)
                                            progress_window.update()

                                            last_update_time = current_time

                            # 7) Dosya tam inmiş mi?
                            if received == filesize:
                                self.log_message(f"File downloaded successfully: {filename}")
                            else:
                                raise Exception("File downloaded incompletely")

                        except Exception as e:
                            if os.path.exists(save_path):
                                os.remove(save_path)
                            raise Exception(f"Download error: {str(e)}")
                        finally:
                            if progress_window.winfo_exists():
                                progress_window.destroy()

                    finally:
                        ### 3) Revert timeout
                        self.socket.settimeout(original_timeout)

                except Exception as e:
                    self.log_message(f"Download error: {str(e)}", "ERROR")

            button_frame = ttk.Frame(file_window)
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            ttk.Button(button_frame, text="Download", command=start_download).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="Cancel", command=file_window.destroy).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            self.log_message(f"Download error: {str(e)}", "ERROR")

            
    def setup_gui(self):
        # Set the window dimensions and minimum size
        self.root.geometry("800x600")
        self.root.minsize(600, 400)
        
         # Create the main container frame
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create the connection frame for server connection details
        connection_frame = ttk.LabelFrame(main_container, text="Server Connection")
        connection_frame.pack(fill=tk.X, padx=5, pady=5)
        
         # Server details entry fields grid
        self.entries = {}
        for i, (label, default) in enumerate([
            ("Server IP:", ""),  # Default to an empty string
            ("Port:", ""),       # Default to an empty string
            ("Username:", "")
        ]):
            # Create label and entry for each server detail
            ttk.Label(connection_frame, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            entry = ttk.Entry(connection_frame)
            entry.insert(0, default)  # Insert the default value (empty here)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            self.entries[label] = entry
        
        # Configure column to expand with window resizing
        connection_frame.grid_columnconfigure(1, weight=1)
        
        # Create a button to connect to the server
        self.connect_button = ttk.Button(connection_frame, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=len(self.entries), column=0, columnspan=2, pady=10)
        
        # Create a frame for file operations
        operations_frame = ttk.LabelFrame(main_container, text="File Operations")
        operations_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create a button frame inside the file operations frame
        button_frame = ttk.Frame(operations_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Create buttons for file operations and add them to the button frame
        self.operation_buttons = []
        for text, command in [
            ("Upload File", self.upload_file),
            ("Download File", self.download_file),
            ("File List", self.list_files),
            ("Delete File", self.delete_file),
            ("Update File", self.update_file)
        ]:
            btn = ttk.Button(button_frame, text=text, command=command, state=tk.DISABLED)
            btn.pack(side=tk.LEFT, padx=2)
            self.operation_buttons.append(btn)
        
        # Create an exit button
        ttk.Button(button_frame, text="Disconnect", command=self.disconnect_from_server).pack(side=tk.RIGHT, padx=2)
        
        # Create a frame for operation logs
        log_frame = ttk.LabelFrame(main_container, text="Operation Logs")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add a scrollbar to the log frame
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
       # Create a text widget for displaying logs and attach the scrollbar
        self.log_text = tk.Text(log_frame, yscrollcommand=scrollbar.set)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.config(command=self.log_text.yview)
        
    def log_message(self, message, level="INFO"):
            # Create a timestamp for the log message
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            formatted_message = f"[{timestamp}] {level}: {message}\n"
            
            # Insert the formatted message into the log text area in the GUI
            self.log_text.insert(tk.END, formatted_message)
            self.log_text.see(tk.END)  # Scroll to the end to show the latest log message
            
            # Update the GUI to reflect changes immediately
            self.root.update_idletasks()

    def connect_to_server(self):
        # Check if the client is already connected to the server
        if self.connected:
            self.log_message("You are already connected to the server.")
            return
        
        try:
            # Get server IP, port, and username from the input fields
            ip = self.entries["Server IP:"].get()
            port = int(self.entries["Port:"].get())
            self.username = self.entries["Username:"].get()
            
             # Ensure the username is not empty
            if not self.username:
                self.log_message("Username cannot be empty!", "ERROR")
                return
            
            # Create a socket and connect to the server
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # Set a 10-second timeout for the connection attempt
            self.socket.connect((ip, port))
            
            # Send the username to the server
            self.socket.send(self.username.encode())
            response = self.socket.recv(1024).decode()
            
            # Handle error responses from the server
            if response.startswith("ERROR"):
                raise Exception(response)
            
            # Set the connection status to True if connection is successful
            self.connected = True
             # Update the connect button to show that the client is connected
            self.connect_button.config(text="Connected", state="disabled")
            
            # Enable file operation buttons since the client is now connected
            for button in self.operation_buttons:
                button.config(state=tk.NORMAL)
            
            # Disable entry fields to prevent changes after connection
            for entry in self.entries.values():
                entry.config(state="disabled")
            
            # Log the successful connection message
            self.log_message(response)

        # Handle various connection errors   
        except socket.timeout as e:
            # Log timeout errors if the server does not respond in time
            self.log_message(f"Connection timeout: {str(e)}", "ERROR")
            self.cleanup_connection()
        except socket.error as e:
            # Log socket errors that may occur during connection attempts
            self.log_message(f"Socket error: {str(e)}", "ERROR")
            self.cleanup_connection()
        except ValueError as e:
            # Log errors related to invalid port numbers
            self.log_message(f"Invalid port number: {str(e)}", "ERROR")
            self.cleanup_connection()
        except Exception as e:
            # Log any other exceptions that occur
            self.log_message(f"Connection error: {str(e)}", "ERROR")
            self.cleanup_connection()


    def cleanup_connection(self):
        # Reset connection status to False
        self.connected = False
        
        # Close the socket if it is open
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                # Log any errors that occur while closing the socket
                self.log_message(f"Error: {str(e)}", "ERROR")
            # Set socket to None to mark it as closed
            self.socket = None
        
        # Reset GUI components to allow reconnection
        self.connect_button.config(text="Connect", state="normal")
        
        # Enable the server entry fields for IP, port, and username
        for entry in self.entries.values():
            entry.config(state="normal")
        
        # Disable all file operation buttons
        for button in self.operation_buttons:
            button.config(state=tk.DISABLED)

    def format_size(self, size):
        # Convert the file size into a human-readable format (B, KB, MB, GB, TB)
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        size = float(size)
        unit = 0
        # Divide by 1024 to get to the next unit until size is less than 1024
        while size >= 1024 and unit < len(units) - 1:
            size /= 1024
            unit += 1
        # Return the size formatted to 2 decimal places with the appropriate unit
        return f"{size:.2f} {units[unit]}"

    def safe_send(self, socket, message, retries=3, timeout=10.0):
        # Store the original socket timeout to restore later
        original_timeout = socket.gettimeout()
        socket.settimeout(timeout)

        try:
            # Attempt to send the message a specified number of retries
            for attempt in range(retries):
                try:
                    # Convert the message to bytes if it is a string
                    if isinstance(message, str):
                        message = message.encode()
                    # Send the entire message using socket.sendall()
                    socket.sendall(message) # Return True if send is successfu
                    return True
                except socket.timeout as e:
                     # If timeout occurs, check remaining attempts
                    remaining = retries - attempt - 1
                    if remaining > 0:
                        # Log a warning and retry after waiting
                        self.log_message(f"Sending timeout - {remaining} deneme kaldı", "WARNING")
                        time.sleep(min(2 ** attempt, 5))  # Exponential backoff, max wait of 5 seconds
                    else:
                        # Log warning if last send fails
                        self.log_message("Last send failed", "WARNING")
                except Exception as e:
                     # Log any other sending errors
                    self.log_message(f"Sending error: {str(e)}", "ERROR")
                    break
            # Return False if all send attempts fail
            return False
        finally:
            # Restore the original socket timeout
            socket.settimeout(original_timeout)

    def safe_receive(self, socket, buffer_size=4096, retries=3, timeout=10.0):
        # Store the original timeout value of the socket to restore it later
        original_timeout = socket.gettimeout()
        socket.settimeout(timeout)  # Set a new timeout for the receive operation
        
        try:
            # Attempt to receive data a specified number of times
            for attempt in range(retries):
                try:
                    # Receive data from the socket
                    data = socket.recv(buffer_size)
                    if data:
                        # Decode the data if it is in bytes, otherwise return the data as-is
                        return data.decode() if isinstance(data, bytes) else data
                    # Return None if no data is received
                    return None
                except socket.timeout as e:
                    # If a timeout occurs, check remaining attempts
                    remaining = retries - attempt - 1
                    if remaining > 0:
                        # Log a warning and retry after waiting
                        self.log_message(f"Receiving timeout - {remaining} attempts left", "WARNING")
                        time.sleep(min(2 ** attempt, 5))  # Exponential backoff, max wait of 5 seconds
                    else:
                        # Log a warning if the last receive attempt fails
                        self.log_message("Last import attempt failed", "WARNING")
                except Exception as e:
                    # Log any other error that occurs during receiving
                    self.log_message(f"Receiving error: {str(e)}", "ERROR")
                    break
            # Return None if all attempts to receive data fail
            return None
        finally:
            # Restore the original socket timeout
            socket.settimeout(original_timeout)

    

    def update_progress(self, total_processed, total_size, start_time):
        # If the total size is zero, there's nothing to process, so return "0%"
        if total_size == 0:
            return "0%"
        
        # Calculate the progress percentage
        progress = (total_processed / total_size) * 100
        
        # Calculate the processing speed in bytes per second
        # Ensure no division by zero by checking if the current time is greater than start time
        speed = total_processed / (time.time() - start_time) if time.time() > start_time else 0
        
        # Format the status message
        status = (
            f"Processing: {progress:.1f}% "
            f"({self.format_size(total_processed)} / {self.format_size(total_size)}) "
            f"- Speed: {self.format_size(speed)}/s"
        )
        
        # Log the status to the GUI log text area
        self.log_message(status)
        
        # Return the formatted status message
        return status


    def check_notifications(self):
        """
    It reads messages coming in the form of "NOTIFICATION|..."
    on the server side at all times and prints them in the log. 
    We removed the 'if self.is_downloading:' line so that 
    it can also be read if a notification arrives during downloading.  
        """
        while True:
            if not self.connected:
                time.sleep(0.1)
                continue

            try:
                # Let's wait for data with 0.1 sec timeout
                self.socket.settimeout(0.1)
                data = self.socket.recv(1024)
                if data:
                    decoded = data.decode(errors='ignore')
                    # 1) NOTIFICATION?
                    if decoded.startswith("NOTIFICATION|"):
                        _, message = decoded.split("|", 1)
                        self.log_message(f"Notification: {message}")
                    else:
                        # Download chunk or another message?
                        # This is a complicated situation. If you want to separate the protocol completely, 
                        # you can put an extra control here.
                        pass

            except socket.timeout:
                pass
            except ConnectionResetError as e:
                self.log_message(f"Connection reset by peer: {str(e)}", "ERROR")
                self.cleanup_connection()
                break
            except Exception as e:
                if self.connected:
                    self.log_message(f"Connection closed: {str(e)}", "ERROR")
                    self.cleanup_connection()
                break

            time.sleep(0.1)

            
    def upload_file(self):
        # Check if the client is connected to the server
        if not self.connected:
            self.log_message("You are not connected to server!", "ERROR")
            return
        
        try:
            # Open a file dialog for the user to choose a file to upload
            filepath = filedialog.askopenfilename(
                title="Choose the uploading file:",
                filetypes=[("All files", "*.*")]
            )
            
            # If no file is selected, exit the function
            if not filepath:
                return
                
            # Get the file size and file name
            filesize = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            
            # Send an upload request to the server with the filename and file size
            if not self.safe_send(self.socket, f"UPLOAD|{filename}|{filesize}"):
                raise Exception("Upload request cannot send")
                
            # Log the start of the file upload
            self.log_message(f"File uploading: {filename}")
            start_time = time.time()  # Track the start time for calculating progress
            total_sent = 0
            retry_count = 0
            max_retries = 3
            
            # Open the selected file in binary read mode
            with open(filepath, 'rb') as f:
                # Continue sending chunks of the file until the whole file is uploaded or retries are exhausted
                while total_sent < filesize and retry_count < max_retries:
                    # Read a chunk of the file, either up to chunk_size or the remaining part of the file
                    chunk = f.read(min(self.chunk_size, filesize - total_sent))
                    if not chunk:
                        break
                        
                    try:
                        # Send the chunk through the socket
                        self.socket.send(chunk)
                        total_sent += len(chunk)
                        # Update the progress based on the amount of data sent
                        self.update_progress(total_sent, filesize, start_time)
                        # Reset retry count after a successful send
                        retry_count = 0
                    except socket.timeout as e:
                        # Handle a timeout during sending, retry if not exceeded max retries
                        retry_count += 1
                        if retry_count < max_retries:
                            self.log_message(f"Upload interruption - Retrying ({retry_count}/{max_retries})", "WARNING")
                            time.sleep(1)  # Wait for a second before retrying
                        else:
                            # Raise an exception if the maximum number of retries is reached
                            raise Exception("Maximum number of retries reached")
            
            # Receive response from the server about the upload status
            response = self.safe_receive(self.socket)
            if not response:
                raise Exception("No response from server!")
            if response.startswith("ERROR"):
                raise Exception(response)
            
            # Log successful upload completion
            self.log_message(f"File uploading completed: {filename}")
            
        except Exception as e:
            # Log any errors that occur during the upload process
            self.log_message(f"File uploading error: {str(e)}", "ERROR")



    
    def list_files(self):
        # Check if the client is connected to the server
        if not self.connected:
            self.log_message("You are not connected to the server!", "ERROR")
            return
        
        try:
            # Send the list request to the server
            if not self.safe_send(self.socket, "LIST"):
                raise Exception("Failed to send list request to server.")
            
            # Receive the server's response
            response = self.safe_receive(self.socket)
            if response is None:
                raise Exception("No response from server")
            
            # Log the list of files available on the server
            self.log_message("\n=== Files in Server ===")
            files = response.split('\n')
            for file in files:
                if file.strip():  # Check for non-empty lines and log them
                    self.log_message(file.strip())
                    
        except Exception as e:
            # Log any errors that occur during the listing process
            self.log_message(f"File listing error: {str(e)}", "ERROR")


    def delete_file(self):
        # Check if the client is connected to the server
        if not self.connected:
            self.log_message("You are not connected to server!", "ERROR")
            return
        
        try:
            # Send a request to the server to list all available files
            self.socket.send("LIST".encode())
            response = self.socket.recv(4096).decode()
            
            # If no files are available, log a message and return
            if "There is no file in server." in response:
                self.log_message("There is no file in server.")
                return
            
            # Create a new window to display the list of files
            file_window = tk.Toplevel(self.root)
            file_window.title("Delete File")
            file_window.geometry("400x300")
            file_window.transient(self.root)  # Make this window a child of the main window
            
            # Create a frame to hold the list of files and other components
            file_frame = ttk.Frame(file_window)
            file_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Add a label to notify the user that they can only delete their own files
            title_label = ttk.Label(file_frame, 
                text="Note: You can only delete your own files!", 
                foreground='red')
            title_label.pack(pady=5)
            
            # Create a scrollbar and a listbox to display the files
            scrollbar = ttk.Scrollbar(file_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(file_frame, yscrollcommand=scrollbar.set)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            scrollbar.config(command=listbox.yview)
            
            # Add all files to the listbox and highlight user's own files in blue
            files = [f.strip() for f in response.split('\n') if f.strip()]
            for file in files:
                listbox.insert(tk.END, file)
                # Highlight user's own files in blue
                if file.startswith(f"{self.username}_"):
                    listbox.itemconfig(listbox.size() - 1, {'fg': 'blue'})
            
            # Function to handle file deletion
            def do_delete():
                # Ensure a file is selected
                if not listbox.curselection():
                    self.log_message("Please choose a file!")
                    return
                
                # Get the selected file and close the file selection window
                selected_file = listbox.get(listbox.curselection())
                file_window.destroy()
                
                # Send the delete request to the server and log the request
                self.log_message(f"File deleting request sending: {selected_file}")
                self.socket.send(f"DELETE|{selected_file}".encode())
                response = self.socket.recv(1024).decode()
                
                # Log the response from the server
                if response.startswith("ERROR"):
                    self.log_message(response, "ERROR")
                else:
                    self.log_message(f"File successfully deleted: {selected_file}")
            
            # Create a frame for the delete and cancel buttons
            button_frame = ttk.Frame(file_window)
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Create and pack the delete button
            ttk.Button(button_frame, text="Delete", command=do_delete).pack(side=tk.LEFT, padx=5)
            # Create and pack the cancel button
            ttk.Button(button_frame, text="Cancel", command=file_window.destroy).pack(side=tk.RIGHT, padx=5)
        
        except Exception as e:
            # Log any errors that occur during the delete process
            self.log_message(f"File deleting error: {str(e)}", "ERROR")

    def update_file(self):
        try:
             # Check if the client is connected to the server
            if not self.connected:
                self.log_message("You are not connected to the server!", "ERROR")
                return

            # Send a request to the server to list all available files
            self.socket.send("LIST".encode())
            response = self.safe_receive(self.socket)
            
            # If there are no files on the server, log a message and return
            if not response or "There is no file in server." in response:
                self.log_message("There is no file in server.")
                return
            
            # Filter the list of files to find the ones owned by the user
            files = [f.strip() for f in response.split('\n') if f.strip()]
            user_files = [f for f in files if f.startswith(f"{self.username}_")]
            
            # If the user has no files, log a message and return
            if not user_files:
                self.log_message("There is no updatable file.")
                return

            # Create a new window to display the user's files for updating
            file_window = tk.Toplevel(self.root)
            file_window.title("Update File")
            file_window.geometry("400x300")
            file_window.transient(self.root)
            
            # Create a frame for listing the files and adding a scrollbar
            file_frame = ttk.Frame(file_window)
            file_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            scrollbar = ttk.Scrollbar(file_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            listbox = tk.Listbox(file_frame, yscrollcommand=scrollbar.set)
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=listbox.yview)
            
            # Add the user's files to the listbox
            for file in user_files:
                listbox.insert(tk.END, file)

            # Function to perform the update
            def do_update():
                # Ensure a file is selected from the listbox
                if not listbox.curselection():
                    self.log_message("Please choose a file!", "ERROR")
                    return
                
                # Get the selected file and close the selection window
                selected_file = listbox.get(listbox.curselection())
                file_window.destroy()
                
                # Open a file dialog to select the new file for updating
                new_file = filedialog.askopenfilename(
                    title="Select the new file to update.",
                    filetypes=[("All files", "*.*")]
                )

                # If no file is selected, return
                if not new_file:
                    return
                
                # Get the size of the new file
                filesize = os.path.getsize(new_file)
                
                # Send an update request to the server
                if not self.safe_send(self.socket, f"UPDATE|{selected_file}|{os.path.basename(new_file)}|{filesize}"):
                    raise Exception("Update request could not be sent.")
                
                # Log that the update is starting
                self.log_message(f"Updating files: {selected_file}")
                start_time = time.time()
                total_sent = 0
                retry_count = 0
                max_retries = 3

                # Open the new file in binary mode and send its contents
                with open(new_file, 'rb') as f:
                    while total_sent < filesize and retry_count < max_retries:
                        chunk = f.read(min(self.chunk_size, filesize - total_sent))
                        if not chunk:
                            break
                        
                        try:
                            # Send the chunk through the socket
                            self.socket.send(chunk)
                            total_sent += len(chunk)
                             # Update the progress of the upload
                            self.update_progress(total_sent, filesize, start_time)
                            retry_count = 0
                        except socket.timeout:
                            # Handle socket timeouts by retrying a specified number of times
                            retry_count += 1
                            if retry_count < max_retries:
                                self.log_message(f"Update interruption - Retrying ({retry_count}/{max_retries})", "WARNING")
                                time.sleep(1)
                            else:
                                raise Exception("Maximum number of retries reached.")
                
                # Receive the server's response to the update
                response = self.safe_receive(self.socket)
                if not response:
                    raise Exception("No response from server.")
                if response.startswith("ERROR"):
                    raise Exception(response)
                
                # Log that the file update was completed successfully
                self.log_message(f"File updating completed: {selected_file}")
            
            # Create a frame for the update and cancel buttons
            button_frame = ttk.Frame(file_window)
            button_frame.pack(fill=tk.X, padx=5, pady=5)
            
            # Create and pack the "Update" button
            ttk.Button(button_frame, text="Update", command=do_update).pack(side=tk.LEFT, padx=5)
            # Create and pack the "Cancel" button
            ttk.Button(button_frame, text="Cancel", command=file_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            # Log any errors that occur during the update process
            self.log_message(f"File updating error: {str(e)}", "ERROR")

    def disconnect_from_server(self):
        # If currently connected, send EXIT command and close the socket
        if self.connected and self.socket:
            try:
                self.socket.send("EXIT".encode())
                self.socket.close()
            except Exception as e:
                self.log_message(f"Error while disconnecting: {str(e)}", "ERROR")
            
            # Perform cleanup to revert to disconnected state
            self.cleanup_connection()
            self.log_message("You have disconnected from the server.")
        else:
            self.log_message("You are not connected to the server!")


    def on_closing(self):
        try:
            # If connected, disconnect from server first
            if self.connected:
                self.disconnect_from_server()
                
            # Destroy the root window and exit
            self.root.destroy()
        except Exception as e:
            print(f"Error while closing: {str(e)}")

if __name__ == "__main__":
    # Initialize the main GUI application window
    root = tk.Tk()
    # Create an instance of the FileClient class, passing the root window
    app = FileClient(root)
    # Start the GUI event loop
    root.mainloop()

