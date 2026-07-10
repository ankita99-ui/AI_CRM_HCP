import axios from 'axios';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? `${typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8001` : 'http://localhost:8001'}`,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    let message = 'Unexpected error';
    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map((item) => item?.msg ?? JSON.stringify(item)).join('; ');
    } else if (detail) {
      message = JSON.stringify(detail);
    } else if (error.message) {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  },
);
