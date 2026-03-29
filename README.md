ARP Spoofing Intrusion Detection System

A real-time IDS that detects ARP spoofing attacks on your local network.
Built with Python Flask backend and React frontend.

Features
- Detects ARP spoofing attacks in real time
- Passive ARP sniffing on network interface
- Active ARP scanning of entire subnet every 10 seconds
- Alerts classified as LOW, MEDIUM, HIGH based on attack frequency
- Live dashboard updates via WebSocket without page refresh
- Local siren sound on attack detection
- All alerts saved to MongoDB
- JWT secured API
- Works on Windows, macOS, Linux

Tech Stack
- Backend: Python, Flask, Flask-SocketIO, Scapy
- Frontend: React, Socket.IO
- Database: MongoDB Atlas
- Auth: JWT

How It Works
1. On startup, sniffer learns MAC addresses of all devices on network
2. Every ARP packet is compared against the learned baseline
3. If MAC mismatch is detected, severity is calculated
4. HIGH and MEDIUM alerts fire immediately
5. LOW alerts go through a verification step before firing
6. Active scanner scans entire subnet every 10 seconds to catch attacks on any device
7. Alert is logged to MongoDB and sent to frontend via WebSocket

Setup
1. Clone the repo
2. Install dependencies: pip install flask flask-socketio flask-cors scapy pymongo python-dotenv
3. Add .env file with MONGO_URI, JWT_SECRET, PORT, IDS_SUBNET
4. Run backend: sudo python app.py (sudo required for packet capture)
5. Run frontend: npm install && npm start

Requirements
- Python 3.10+
- Node.js
- MongoDB Atlas account
- Root/admin privileges for packet capture

Disclaimer
This tool is for educational and authorized network security monitoring only.
Do not use on networks you do not own or have permission to monitor.

Author
Harsh Dixit
