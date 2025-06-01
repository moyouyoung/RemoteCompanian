# robot_webserver.py
from flask import Flask, render_template, Response, jsonify
import cv2
import threading
import time
import Jetson.GPIO as GPIO  # For controlling motors on Jetson

# Configuration
app = Flask(__name__)

# Camera setup
# gstreamer_pipeline returns a GStreamer pipeline for capturing from the CSI camera
# Defaults to 1280x720 @ 60fps
# Flip the image by setting the flip_method (most common values: 0 and 2)
# display_width and display_height determine the size of the window on the screen


def gstreamer_pipeline(
    capture_width=1280,
    capture_height=720,
    display_width=1280,
    display_height=720,
    framerate=60,
    flip_method=2,
):
    return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
    )


camera = cv2.VideoCapture(gstreamer_pipeline(flip_method=0), cv2.CAP_GSTREAMER)  


# Motor control pins setup
# Adjust these pins based on your specific wiring
MOTOR_A_PIN1 = 21
MOTOR_A_PIN2 = 23
MOTOR_B_PIN1 = 22
MOTOR_B_PIN2 = 24

# Set up GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(MOTOR_A_PIN1, GPIO.OUT)
GPIO.setup(MOTOR_A_PIN2, GPIO.OUT)
GPIO.setup(MOTOR_B_PIN1, GPIO.OUT)
GPIO.setup(MOTOR_B_PIN2, GPIO.OUT)

# Global variable to store current motor state
motor_state = {"left": "stop", "right": "stop"}

def generate_frames():
    """Generate camera frames for streaming"""
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def control_motors(left, right):
    """Control both motors based on commands"""
    # Left motor control
    if left == "forward":
        GPIO.output(MOTOR_A_PIN1, GPIO.HIGH)
        GPIO.output(MOTOR_A_PIN2, GPIO.LOW)
    elif left == "backward":
        GPIO.output(MOTOR_A_PIN1, GPIO.LOW)
        GPIO.output(MOTOR_A_PIN2, GPIO.HIGH)
    else:  # stop
        GPIO.output(MOTOR_A_PIN1, GPIO.LOW)
        GPIO.output(MOTOR_A_PIN2, GPIO.LOW)
    
    # Right motor control
    if right == "forward":
        GPIO.output(MOTOR_B_PIN1, GPIO.HIGH)
        GPIO.output(MOTOR_B_PIN2, GPIO.LOW)
    elif right == "backward":
        GPIO.output(MOTOR_B_PIN1, GPIO.LOW)
        GPIO.output(MOTOR_B_PIN2, GPIO.HIGH)
    else:  # stop
        GPIO.output(MOTOR_B_PIN1, GPIO.LOW)
        GPIO.output(MOTOR_B_PIN2, GPIO.LOW)

@app.route('/')
def index():
    """Render main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/move/<direction>')
def move(direction):
    """Handle movement commands"""
    global motor_state
    
    if direction == "forward":
        motor_state = {"left": "forward", "right": "forward"}
    elif direction == "backward":
        motor_state = {"left": "backward", "right": "backward"}
    elif direction == "left":
        motor_state = {"left": "stop", "right": "forward"}
    elif direction == "right":
        motor_state = {"left": "forward", "right": "stop"}
    elif direction == "stop":
        motor_state = {"left": "stop", "right": "stop"}
    
    control_motors(motor_state["left"], motor_state["right"])

    # If not a stop command, start a timer to stop after 1 second
    if direction != "stop":
        threading.Timer(0.3, auto_stop).start()

    return jsonify({"status": "success", "direction": direction})

def auto_stop():
    """Automatically stop motors after timer expires"""
    global motor_state
    motor_state = {"left": "stop", "right": "stop"}
    control_motors("stop", "stop")
    print("Auto-stopped motors after 1 second")

@app.route('/status')
def status():
    """Return current motor state"""
    return jsonify(motor_state)

def cleanup():
    """Clean up resources"""
    camera.release()
    GPIO.cleanup()

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8000, threaded=True)
    finally:
        cleanup()
