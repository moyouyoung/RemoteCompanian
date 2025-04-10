import asyncio
import json
import cv2
import websockets
import argparse
import os
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer, MediaRelay

# Configuration - These could be loaded from a config file
DEFAULT_SERVER_URL = 'ws://localhost:3000/signaling?deviceAuth=your-device-secret-key'
DEFAULT_DEVICE_ID = 'unique-device-id'

# Custom video track for handling different camera sources
class CameraVideoTrack(VideoStreamTrack):
    def __init__(self, camera_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.cap = cv2.VideoCapture(camera_id)
        if not self.cap.isOpened():
            raise ValueError(f"Could not open camera {camera_id}")
        
        # Set resolution
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Get the actual frame dimensions
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Camera initialized with resolution: {self.width}x{self.height}")
        
        self.task = None
        self.frame = None
        self.last_frame_time = 0
    
    async def recv(self):
        # If the camera isn't open, try to reopen it
        if not self.cap.isOpened():
            try:
                self.cap.release()  # Make sure it's fully closed
                self.cap = cv2.VideoCapture(self.camera_id)
                if not self.cap.isOpened():
                    raise ValueError(f"Could not reopen camera {self.camera_id}")
            except Exception as e:
                print(f"Error reopening camera: {e}")
        
        # Capture frame
        ret, frame = self.cap.read()
        if not ret:
            print("Warning: Could not read from camera")
            # Return a blank frame as fallback
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Convert to RGB (aiortc expects RGB format)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Create VideoFrame object
        pts, time_base = await self.next_timestamp()
        
        # Create and return the frame
        from av import VideoFrame
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame
    
    def stop(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()

# Device control functions
class DeviceController:
    def __init__(self):
        # Initialize any hardware control here
        self.status = "idle"
        print("Device controller initialized")
    
    def move_forward(self):
        print("Moving forward")
        self.status = "moving_forward"
        # Code to control your device hardware
        return {"status": "success", "action": "forward"}
    
    def move_backward(self):
        print("Moving backward")
        self.status = "moving_backward"
        # Code to control your device hardware
        return {"status": "success", "action": "backward"}
    
    def turn_left(self):
        print("Turning left")
        self.status = "turning_left"
        # Code to control your device hardware
        return {"status": "success", "action": "left"}
    
    def turn_right(self):
        print("Turning right")
        self.status = "turning_right"
        # Code to control your device hardware
        return {"status": "success", "action": "right"}
    
    def stop_movement(self):
        print("Stopping")
        self.status = "idle"
        # Code to control your device hardware
        return {"status": "success", "action": "stop"}
    
    def get_status(self):
        return {"status": self.status}
    
    def handle_command(self, command):
        commands = {
            'forward': self.move_forward,
            'backward': self.move_backward,
            'left': self.turn_left,
            'right': self.turn_right,
            'stop': self.stop_movement,
            'status': self.get_status
        }
        
        if command in commands:
            return commands[command]()
        else:
            return {"status": "error", "message": f"Unknown command: {command}"}

# WebRTC connection manager
class RTCConnection:
    def __init__(self, device_controller, camera_id=0):
        self.pc = None
        self.device_controller = device_controller
        self.camera_id = camera_id
        self.video_track = None
    
    async def create_connection(self):
        # Close any existing connection
        if self.pc:
            await self.close_connection()
        
        # Create new peer connection
        self.pc = RTCPeerConnection()
        
        # Set up video track
        self.video_track = CameraVideoTrack(self.camera_id)
        
        # Add video track to peer connection
        self.pc.addTrack(self.video_track)
        
        # Log ICE connection state changes
        @self.pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print(f"ICE connection state changed to {self.pc.iceConnectionState}")
            
            if self.pc.iceConnectionState == "failed":
                await self.close_connection()
        
        return self.pc
    
    async def close_connection(self):
        if self.pc:
            # Close peer connection
            await self.pc.close()
            self.pc = None
        
        # Stop video track
        if self.video_track:
            self.video_track.stop()
            self.video_track = None

# Main device application
class DeviceApplication:
    def __init__(self, server_url, device_id, camera_id=0):
        self.server_url = server_url
        self.device_id = device_id
        self.camera_id = camera_id
        self.device_controller = DeviceController()
        self.rtc_connection = RTCConnection(self.device_controller, camera_id)
        self.websocket = None
        self.reconnect_task = None
        self.running = False
    
    async def connect_to_server(self):
        try:
            self.websocket = await websockets.connect(self.server_url)
            print(f"Connected to signaling server: {self.server_url}")
            
            # Register with server
            await self.websocket.send(json.dumps({
                "type": "register",
                "role": "device",
                "deviceId": self.device_id
            }))
            
            # Start message handling loop
            await self.handle_messages()
            
        except websockets.exceptions.ConnectionClosed as e:
            print(f"WebSocket connection closed: {e}")
            await self.schedule_reconnect()
        except Exception as e:
            print(f"Error connecting to server: {e}")
            await self.schedule_reconnect()
    
    async def schedule_reconnect(self):
        # Cancel any existing reconnect task
        if self.reconnect_task:
            self.reconnect_task.cancel()
        
        print("Scheduling reconnect in 5 seconds...")
        self.reconnect_task = asyncio.create_task(self.delayed_reconnect())
    
    async def delayed_reconnect(self):
        await asyncio.sleep(5)  # Wait before reconnecting
        if self.running:
            print("Attempting to reconnect...")
            await self.connect_to_server()
    
    async def handle_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                print(f"Received: {data['type']}")
                
                if data["type"] == "controller_ready":
                    # Controller is ready to connect
                    print("Controller is ready")
                    
                elif data["type"] == "offer":
                    # Handle incoming WebRTC offer
                    await self.handle_offer(data)
                    
                elif data["type"] == "ice_candidate" and data["candidate"]:
                    # Add ICE candidate
                    if self.rtc_connection.pc:
                        candidate = data["candidate"]
                        await self.rtc_connection.pc.addIceCandidate(candidate)
                    
                elif data["type"] == "command":
                    # Process command
                    await self.handle_command(data)
                
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
            await self.schedule_reconnect()
        except Exception as e:
            print(f"Error handling messages: {e}")
            if self.websocket and self.websocket.open:
                await self.websocket.close()
            await self.schedule_reconnect()
    
    async def handle_offer(self, data):
        try:
            # Create new connection
            pc = await self.rtc_connection.create_connection()
            
            # Set up ICE candidate handling
            @pc.on("icecandidate")
            async def on_icecandidate(candidate):
                if candidate and self.websocket and self.websocket.open:
                    await self.websocket.send(json.dumps({
                        "type": "ice_candidate",
                        "deviceId": self.device_id,
                        "candidate": candidate.to_json()
                    }))
            
            # Set remote description
            offer = RTCSessionDescription(sdp=data["offer"]["sdp"], type=data["offer"]["type"])
            await pc.setRemoteDescription(offer)
            
            # Create answer
            answer = await pc.createAnswer()
            await pc.setLocalDescription(answer)
            
            # Send answer to controller
            if self.websocket and self.websocket.open:
                await self.websocket.send(json.dumps({
                    "type": "answer",
                    "deviceId": self.device_id,
                    "answer": {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
                }))
        except Exception as e:
            print(f"Error handling offer: {e}")
    
    async def handle_command(self, data):
        # Process command
        result = self.device_controller.handle_command(data["command"])
        
        # Send response
        if self.websocket and self.websocket.open:
            await self.websocket.send(json.dumps({
                "type": "command_response",
                "deviceId": self.device_id,
                "command": data["command"],
                "result": result
            }))
    
    async def run(self):
        self.running = True
        await self.connect_to_server()
    
    async def stop(self):
        self.running = False
        
        # Cancel reconnect task if active
        if self.reconnect_task:
            self.reconnect_task.cancel()
            self.reconnect_task = None
        
        # Close WebRTC connection
        await self.rtc_connection.close_connection()
        
        # Close WebSocket
        if self.websocket and self.websocket.open:
            await self.websocket.close()

# Main function
async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Remote Device Client')
    parser.add_argument('--server', default=DEFAULT_SERVER_URL, help='WebSocket server URL')
    parser.add_argument('--device-id', default=DEFAULT_DEVICE_ID, help='Device ID')
    parser.add_argument('--camera', type=int, default=0, help='Camera ID')
    
    args = parser.parse_args()
    
    # Create and run device application
    app = DeviceApplication(args.server, args.device_id, args.camera)
    
    # Handle graceful shutdown
    try:
        await app.run()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        await app.stop()

# Run the application
if __name__ == "__main__":
    # Import here to avoid import errors if not needed
    import numpy as np
    
    # Check if required packages are installed
    try:
        import aiortc
        import av
    except ImportError:
        print("Required packages not installed. Please install with:")
        print("pip install aiortc opencv-python websockets numpy av")
        exit(1)
    
    print("Starting device client...")
    asyncio.run(main())