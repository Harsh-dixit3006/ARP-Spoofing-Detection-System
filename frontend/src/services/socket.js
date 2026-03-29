import { io } from 'socket.io-client';

const SOCKET_URL = 'http://127.0.0.1:5001'; // make sure this matches your backend port

const socket = io(SOCKET_URL, {
  transports: ['websocket', 'polling'], // add polling as fallback
  reconnectionAttempts: 10,
  reconnectionDelay: 1000,
});

socket.on('connect', () => {
  console.log('[SOCKET] Connected to backend:', socket.id);
});

socket.on('disconnect', () => {
  console.log('[SOCKET] Disconnected from backend');
});

socket.on('connect_error', (err) => {
  console.log('[SOCKET] Connection error:', err.message);
});

export default socket;