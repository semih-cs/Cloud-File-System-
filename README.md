# 🌐 Cloud File Storage and Publishing System - CS408 Project (Fall 2024)

This project is a **Client-Server cloud file storage and publishing system**, developed as part of the **CS408 - Computer Networks** course at **Sabancı University**.

## 🛠️ Features

- 📁 Upload ASCII text files to the server using a GUI-based file selector  
- 🔄 Overwrite previously uploaded files with the same name  
- 👀 View all uploaded files and their respective owners  
- ⬇️ Download any shared file by specifying uploader and filename  
- ❌ Delete or update only your own uploaded files  
- 🧠 Handles concurrent TCP connections with multiple clients  
- 🖥️ Graphical User Interfaces for both Client and Server  
- 🚫 Username conflict prevention: only one active client per username  
- 📜 Persistent file storage and metadata list (remains after shutdown)  
- ⚠️ Detailed logging and error messages on both Server and Client GUIs  
- 🔌 Reliable TCP Socket-based communication for all operations  
- 📤 Uploaders are notified when their file is downloaded (if online)  

## 🧪 Technologies Used

- **Programming Language**: Python  
- **Communication Protocol**: TCP Sockets  
- **GUI Framework**: Tkinter  

## 🧑‍💻 How to Use

1. **Start the Server Application**
   - Choose the port number and storage folder via the GUI
   - Start listening for incoming client connections

2. **Start the Client Application**
   - Enter the server IP address and port
   - Choose a unique username to connect

3. **Perform File Operations**
   - Upload ASCII `.txt` files via GUI file picker  
   - Download, delete, or update your own files  
   - View a live list of all shared files and their owners  

4. **Disconnect Anytime**
   - Disconnect safely via GUI or by closing the window  
   - Server handles abrupt disconnects without crashing  

## 📁 Project Structure

