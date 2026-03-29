import axios from 'axios';

// Set default URL to Flask backend (Updated to Port 5001 to avoid MacOS Airplay collision)
const API_URL = 'http://127.0.0.1:5001/api';

const api = axios.create({
  baseURL: API_URL,
});

// Request interceptor to attach JWT token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

export default api;
