# Remote Device Control System - Installation Guide

This guide will help you set up your remote device control system with authentication.

## Prerequisites

### For the Server
- Node.js (version 14 or later)
- npm (comes with Node.js)

### For the Remote Device
- Python 3.7 or later
- Webcam or camera module
- Required Python packages (listed below)

## Server Setup

1. **Create the project directory structure:**

```
remote-control-system/
├── server.js        # Main server file
├── users.json       # User authentication file
├── public/          # Web client files
│   ├── login.html   # Login page
│   └── app/         # Protected application files
│       └── index.html # Main application page
```

2. **Install required Node.js packages:**

```bash
cd remote-control-system
npm init -y
npm install express@4.21.2 ws http express-session body-parser
```

3. **Create the configuration files:**

Copy the server.js code from the "Remote Device Control Website with Authentication" artifact.

Create a users.json file with the contents from the "Users Configuration File" artifact.

Create the login.html file in the public directory with the contents from the "Login Page" artifact.

Create the app/index.html file in the public directory with the contents from the "Main Application Page" artifact.

4. **Start the server:**

```bash
node server.js
```

The server will start on port 3000 by default. You can access the login page at http://localhost:3000/login

## Remote Device Setup

1. **Install required Python packages:**

```bash
pip install aiortc opencv-python websockets numpy av
```

Note: Installing aiortc might require additional system dependencies. Please refer to the aiortc documentation for your specific operating system.

2. **Create the Python script:**

Create a file named `device.py` with the contents from the "Remote Device Python Implementation with Authentication" artifact.

3. **Run the device client:**

```bash
python device.py --server ws://your-server-address:3000/signaling?deviceAuth=your-device-secret-key --device-id unique-device-id --camera 0
```

Replace:
- `your-server-address` with your server's IP or domain
- `your-device-secret-key` with the secret key you defined in the server.js file
- `unique-device-id` with the device ID that matches one in your users.json
- `camera 0` with the appropriate camera index (0 is usually the default camera)

## Security Considerations

1. **Change default credentials:**
   - Modify the default usernames and passwords in users.json
   - Replace "your-secret-key" in the session configuration
   - Replace "your-device-secret-key" with a strong random string

2. **Use HTTPS in production:**
   - Generate or obtain SSL certificates
   - Configure the Express server to use HTTPS
   - Update WebSocket URLs to use WSS (secure WebSocket)

3. **Implement rate limiting to prevent brute force attacks**

4. **Consider implementing two-factor authentication for additional security**

## Network Configuration

To allow access to your system from outside your local network:

1. **Configure port forwarding on your router** to forward port 3000 (or your chosen port) to the server's local IP address

2. **Consider using a dynamic DNS service** if you don't have a static IP address

3. **Use a proper TURN server** for reliable WebRTC connections across different networks

## Customization Options

### Adding More Command Controls

1. Modify the control buttons in the HTML frontend
2. Add corresponding command handlers in the DeviceController class in the Python code

### Supporting Multiple Cameras

1. Modify the CameraVideoTrack class to switch between cameras
2. Add camera selection UI to the web interface

### Implementing Video Recording

1. Add recording functionality to the server
2. Create recording controls in the web interface
3. Implement server-side storage of recorded video