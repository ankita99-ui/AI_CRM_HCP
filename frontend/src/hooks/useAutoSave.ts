import { useEffect } from 'react';

export const useAutoSave = <T>(key: string, value: T) => {
  useEffect(() => {
    const timer = window.setTimeout(() => {
      localStorage.setItem(key, JSON.stringify(value));
    }, 800);

    return () => window.clearTimeout(timer);
  }, [key, value]);
};

export const loadAutoSaved = <T>(key: string, fallback: T): T => {
  const raw = localStorage.getItem(key);
  if (!raw) {
    return fallback;
  }

  try {
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
};
