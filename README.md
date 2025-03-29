🌐 Cloud File Storage and Publishing System - CS408 Project (Fall 2024)

This project is a Client-Server cloud file storage and publishing system, developed as part of the CS408 - Computer Networks course at Sabancı University.

🛠️ Features
📁 Upload ASCII text files to the server with GUI-based file selection
🔄 Overwrite previously uploaded files with the same name
👀 View all uploaded files and their respective owners
⬇️ Download any shared file by specifying uploader and filename
❌ Delete or update only your own uploaded files
🧠 Handles concurrent TCP connections with multiple clients
🖥️ Graphical User Interfaces for both Client and Server (GUI)
🚫 Username conflict prevention: only one active client per name
📜 Persistent file storage and file list (even after shutdown)
⚠️ Detailed logging and error messages on both sides
🔌 TCP Socket-based file transfer and communication
📤 Automatic notifications on download if uploader is online
🧪 Technologies
Programming Language: Python / Java / C# (specify your choice)
Communication: TCP Sockets
GUI Framework: (e.g., Tkinter, JavaFX, Windows Forms — specify here)
🧑‍💻 Usage
Start Server and set the listening port and storage folder via GUI
Start Client, enter server IP and port, and login with a unique username
Upload, download, list, delete, or update files from the interface
Disconnect anytime — client or server handles it gracefully
