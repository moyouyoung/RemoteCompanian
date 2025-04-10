// server.js - Node.js server with authentication
const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const fs = require('fs');
const session = require('express-session');
const bodyParser = require('body-parser');

// Create Express app
const app = express();

// Configure express
app.use(bodyParser.urlencoded({ extended: true }));
app.use(bodyParser.json());

// Session configuration
app.use(session({
    secret: 'your-secret-key', // Change this to a secure random string
    resave: false,
    saveUninitialized: false,
    cookie: { 
        secure: process.env.NODE_ENV === 'production', // Use secure cookies in production
        maxAge: 3600000 // Session expiration (1 hour)
    }
}));

// Load users from file
let users = {};
try {
    const usersData = fs.readFileSync(path.join(__dirname, 'users.json'), 'utf8');
    users = JSON.parse(usersData);
    console.log('Users loaded successfully');
} catch (err) {
    console.error('Error loading users:', err);
    // Create a default user if file doesn't exist
    users = {
        "admin": {
            password: "admin123", // Change this default password!
            devices: ["unique-device-id"] // List of devices this user can access
        }
    };
    
    // Write default users to file
    fs.writeFileSync(
        path.join(__dirname, 'users.json'), 
        JSON.stringify(users, null, 2), 
        'utf8'
    );
    console.log('Created default users file');
}

// Authentication middleware
function ensureAuthenticated(req, res, next) {
    if (req.session && req.session.authenticated) {
        return next();
    }
    // If AJAX request
    if (req.xhr) {
        return res.status(401).json({ error: 'Not authenticated' });
    }
    // Store the original URL they were requesting
    req.session.returnTo = req.originalUrl;
    res.redirect('/login');
}

// Serve login page
app.get('/login', (req, res) => {
    if (req.session && req.session.authenticated) {
        // Already logged in, redirect to home
        return res.redirect('/');
    }
    res.sendFile(path.join(__dirname, 'public', 'login.html'));
});

// Process login
app.post('/api/login', (req, res) => {
    const { username, password } = req.body;
    
    if (users[username] && users[username].password === password) {
        // Authentication successful
        req.session.authenticated = true;
        req.session.username = username;
        
        // Redirect to original requested URL or home
        const returnTo = req.session.returnTo || '/';
        delete req.session.returnTo;
        res.json({ success: true, redirect: returnTo });
    } else {
        // Authentication failed
        res.status(401).json({ success: false, message: 'Invalid username or password' });
    }
});

// Logout
app.get('/api/logout', (req, res) => {
    req.session.destroy();
    res.json({ success: true });
});

// Get authorized devices for current user
app.get('/api/devices', ensureAuthenticated, (req, res) => {
    const username = req.session.username;
    if (users[username] && users[username].devices) {
        res.json({ devices: users[username].devices });
    } else {
        res.json({ devices: [] });
    }
});

// Serve static files from 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

// Protected routes
app.use('/app', ensureAuthenticated, express.static(path.join(__dirname, 'public', 'app')));

// Create HTTP server
const server = http.createServer(app);

// Create WebSocket server using the same HTTP server
const wss = new WebSocket.Server({ server, path: '/signaling' });

// WebSocket authentication
wss.on('connection', (ws, req) => {
    // Parse the cookies from the request
    const getCookies = (cookieString) => {
        const cookies = {};
        if (cookieString) {
            cookieString.split(';').forEach(cookie => {
                const parts = cookie.match(/(.*?)=(.*)$/);
                if (parts) {
                    cookies[parts[1].trim()] = decodeURI(parts[2].trim());
                }
            });
        }
        return cookies;
    };
    
    // WebSocket connections don't carry the session directly,
    // so we need to parse the session cookie and verify it
    const cookies = getCookies(req.headers.cookie);
    const sessionId = cookies['connect.sid']; // Adjust based on your session cookie name
    
    // For simplicity, we're assuming if there's a session cookie, the user is authenticated
    // In a production setup, you'd want to verify the session with your session store
    if (!sessionId && req.url.indexOf('?deviceAuth=') === -1) {
        ws.send(JSON.stringify({
            type: 'error',
            message: 'Authentication required'
        }));
        ws.close();
        return;
    }
    
    console.log('Client connected');
    
    // WebSocket signaling logic
    const clients = new Map();
    
    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            
            // Handle registration
            if (data.type === 'register') {
                // For device authentication, you might use a special token
                // For simplicity, we're using a role-based approach here
                if (data.role === 'device') {
                    // Check if device is using device auth token
                    const deviceAuth = req.url.match(/\?deviceAuth=([^&]*)/);
                    if (deviceAuth && deviceAuth[1] === 'your-device-secret-key') { // Replace with secure key
                        clients.set(data.role + '-' + data.deviceId, ws);
                        console.log(`Registered ${data.role} for device ${data.deviceId}`);
                    } else {
                        ws.send(JSON.stringify({
                            type: 'error',
                            message: 'Device authentication failed'
                        }));
                        return;
                    }
                } else {
                    // User authentication already verified by session
                    clients.set(data.role + '-' + data.deviceId, ws);
                    console.log(`Registered ${data.role} for device ${data.deviceId}`);
                }
                
                // If both controller and device are connected, notify them
                if (clients.has('controller-' + data.deviceId) && 
                    clients.has('device-' + data.deviceId)) {
                    
                    const controllerWs = clients.get('controller-' + data.deviceId);
                    controllerWs.send(JSON.stringify({ type: 'device_ready' }));
                    
                    const deviceWs = clients.get('device-' + data.deviceId);
                    deviceWs.send(JSON.stringify({ type: 'controller_ready' }));
                }
                return;
            }
            
            // Forward messages to the appropriate client
            if (data.deviceId) {
                const targetRole = data.type === 'command' ? 'device' : 'controller';
                const target = clients.get(targetRole + '-' + data.deviceId);
                
                if (target && target.readyState === WebSocket.OPEN) {
                    target.send(message);
                } else {
                    ws.send(JSON.stringify({
                        type: 'error',
                        message: `${targetRole} for device ${data.deviceId} not connected`
                    }));
                }
            }
        } catch (e) {
            console.error('Error processing message:', e);
            ws.send(JSON.stringify({
                type: 'error',
                message: 'Invalid message format'
            }));
        }
    });
    
    ws.on('close', () => {
        // Remove client from tracked clients
        for (const [key, value] of clients.entries()) {
            if (value === ws) {
                clients.delete(key);
                console.log(`Client ${key} disconnected`);
                break;
            }
        }
    });
});

// Handle all other routes by sending the main HTML file
// This enables single-page application routing
app.get('/app/*', ensureAuthenticated, (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'app', 'index.html'));
});

// Start the server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`Open http://localhost:${PORT}/login to access the application`);
});