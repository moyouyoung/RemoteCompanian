import os
import cv2
import threading
import time
from flask import Flask, render_template, Response, jsonify, request
import RPi.GPIO as GPIO  # For controlling GPIO pins on Jetson/RPi

# GPIO pin setup for motors
# Using standard GPIO pin numbering
LEFT_MOTOR_PIN1 = 21
LEFT_MOTOR_PIN2 = 23
RIGHT_MOTOR_PIN1 = 22
RIGHT_MOTOR_PIN2 = 24
# MOTOR_ENABLE_PIN = 27  # PWM pin for speed control

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(LEFT_MOTOR_PIN1, GPIO.OUT)
GPIO.setup(LEFT_MOTOR_PIN2, GPIO.OUT)
GPIO.setup(RIGHT_MOTOR_PIN1, GPIO.OUT)
GPIO.setup(RIGHT_MOTOR_PIN2, GPIO.OUT)
# GPIO.setup(MOTOR_ENABLE_PIN, GPIO.OUT)

# Setup PWM for speed control
# pwm = GPIO.PWM(MOTOR_ENABLE_PIN, 100)  # 100 Hz frequency
# pwm.start(50)  # Start with 50% duty cycle

# Camera setup
camera = cv2.VideoCapture(0)  # Use default camera (may need to change index)
if not camera.isOpened():
    print("Error: Could not open camera")
    exit()

# Set resolution to 640x480 for better performance
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Initialize Flask app
app = Flask(__name__)

# Variables to control motors
is_moving = False
current_direction = "stop"

def generate_frames():
    """Generate camera frames with OpenCV"""
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            # Yield the frame in the MJPEG format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

def control_motors(direction):
    """Control the robot's motors based on direction"""
    global current_direction
    current_direction = direction
    
    if direction == "forward":
        GPIO.output(LEFT_MOTOR_PIN1, GPIO.HIGH)
        GPIO.output(LEFT_MOTOR_PIN2, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_PIN1, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_PIN2, GPIO.LOW)
    elif direction == "backward":
        GPIO.output(LEFT_MOTOR_PIN1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_PIN2, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_PIN1, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_PIN2, GPIO.HIGH)
    elif direction == "left":
        GPIO.output(LEFT_MOTOR_PIN1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_PIN2, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_PIN1, GPIO.HIGH)
        GPIO.output(RIGHT_MOTOR_PIN2, GPIO.LOW)
    elif direction == "right":
        GPIO.output(LEFT_MOTOR_PIN1, GPIO.HIGH)
        GPIO.output(LEFT_MOTOR_PIN2, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_PIN1, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_PIN2, GPIO.HIGH)
    elif direction == "stop":
        GPIO.output(LEFT_MOTOR_PIN1, GPIO.LOW)
        GPIO.output(LEFT_MOTOR_PIN2, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_PIN1, GPIO.LOW)
        GPIO.output(RIGHT_MOTOR_PIN2, GPIO.LOW)

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Stream the video feed from the camera"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/control', methods=['POST'])
def control():
    """Endpoint to control the robot's movement"""
    direction = request.json.get('direction')
    if direction in ["forward", "backward", "left", "right", "stop"]:
        control_motors(direction)
        return jsonify({"status": "success", "direction": direction})
    return jsonify({"status": "error", "message": "Invalid direction"})

@app.route('/status')
def status():
    """Return the current status of the robot"""
    return jsonify({
        "direction": current_direction,
        "speed": pwm.ChangeDutyCycle,
        "is_moving": is_moving
    })

@app.route('/speed', methods=['POST'])
def set_speed():
    """Set the motor speed (PWM duty cycle)"""
    speed = request.json.get('speed')
    if 0 <= speed <= 100:
        pwm.ChangeDutyCycle(speed)
        return jsonify({"status": "success", "speed": speed})
    return jsonify({"status": "error", "message": "Invalid speed"})

# Create templates directory if it doesn't exist
if not os.path.exists('templates'):
    os.makedirs('templates')

# Create the HTML template
with open('templates/index.html', 'w') as f:
    f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Robot Control</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            text-align: center;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }
        .video-container {
            margin: 20px 0;
            border: 1px solid #ccc;
            border-radius: 5px;
            overflow: hidden;
        }
        video, img {
            width: 100%;
            max-width: 640px;
            height: auto;
        }
        .controls {
            display: flex;
            flex-direction: column;
            align-items: center;
            margin-top: 20px;
        }
        .control-row {
            display: flex;
            justify-content: center;
            margin: 5px 0;
        }
        button {
            width: 80px;
            height: 80px;
            margin: 5px;
            border-radius: 10px;
            border: none;
            background-color: #4CAF50;
            color: white;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        button:hover {
            background-color: #45a049;
        }
        button:active {
            background-color: #3e8e41;
        }
        .speed-control {
            margin-top: 20px;
            width: 80%;
            max-width: 300px;
        }
        #status {
            margin-top: 20px;
            font-style: italic;
            color: #666;
        }
        @media (max-width: 600px) {
            button {
                width: 60px;
                height: 60px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Robot Control Panel</h1>
        
        <div class="video-container">
            <img src="{{ url_for('video_feed') }}" alt="Robot Camera Feed">
        </div>
        
        <div class="controls">
            <div class="control-row">
                <button id="forward">▲<br>Forward</button>
            </div>
            <div class="control-row">
                <button id="left">◄<br>Left</button>
                <button id="stop">■<br>Stop</button>
                <button id="right">►<br>Right</button>
            </div>
            <div class="control-row">
                <button id="backward">▼<br>Backward</button>
            </div>
        </div>
        
        <div class="speed-control">
            <label for="speed">Speed: <span id="speed-value">50</span>%</label>
            <input type="range" id="speed" min="0" max="100" value="50">
        </div>
        
        <div id="status">Robot is stopped</div>
    </div>

    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const buttons = {
                forward: document.getElementById('forward'),
                backward: document.getElementById('backward'),
                left: document.getElementById('left'),
                right: document.getElementById('right'),
                stop: document.getElementById('stop')
            };
            
            const speedSlider = document.getElementById('speed');
            const speedValue = document.getElementById('speed-value');
            const statusDiv = document.getElementById('status');
            
            // Function to send control commands
            function sendCommand(direction) {
                fetch('/control', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ direction: direction })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        statusDiv.textContent = `Robot is moving ${direction}`;
                        if (direction === 'stop') {
                            statusDiv.textContent = 'Robot is stopped';
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    statusDiv.textContent = 'Error controlling robot';
                });
            }
            
            // Set up button click events
            for (const [direction, button] of Object.entries(buttons)) {
                button.addEventListener('click', () => sendCommand(direction));
                
                // Add touch events for mobile devices
                button.addEventListener('touchstart', (e) => {
                    e.preventDefault();
                    sendCommand(direction);
                });
            }
            
            // Set up speed control
            speedSlider.addEventListener('input', function() {
                const speed = this.value;
                speedValue.textContent = speed;
            });
            
            speedSlider.addEventListener('change', function() {
                const speed = parseInt(this.value);
                fetch('/speed', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ speed: speed })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        statusDiv.textContent = `Speed set to ${speed}%`;
                        setTimeout(() => {
                            statusDiv.textContent = `Robot is ${buttons.stop.disabled ? 'stopped' : 'moving'}`;
                        }, 1000);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                });
            });
            
            // Add keyboard controls
            document.addEventListener('keydown', function(event) {
                switch(event.key) {
                    case 'ArrowUp':
                        sendCommand('forward');
                        break;
                    case 'ArrowDown':
                        sendCommand('backward');
                        break;
                    case 'ArrowLeft':
                        sendCommand('left');
                        break;
                    case 'ArrowRight':
                        sendCommand('right');
                        break;
                    case ' ':  // Spacebar
                        sendCommand('stop');
                        break;
                }
            });
        });
    </script>
</body>
</html>
    """)

def cleanup():
    """Clean up resources on shutdown"""
    print("Cleaning up resources...")
    GPIO.cleanup()
    camera.release()

# Run the Flask app when this script is executed
if __name__ == '__main__':
    try:
        print("Starting Robot Control Web Server...")
        print("Access the control panel at http://[YOUR_IP_ADDRESS]:5000")
        # Add this to ensure cleanup happens on exit
        import atexit
        atexit.register(cleanup)
        # Run on all network interfaces (0.0.0.0) so you can access it from other devices
        app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
    except KeyboardInterrupt:
        cleanup()