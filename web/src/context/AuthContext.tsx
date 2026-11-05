import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiUrl, apiErrorMessage } from '../api/config';

export interface UserProfile {
  id: string;
  username: string;
  full_name: string;
  email: string;
  trip_count: number;
  memory_count: number;
  is_guest: boolean;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isLoading: boolean;
  loginAsGuest: () => Promise<void>;
  login: (usernameOrEmail: string, password: string) => Promise<boolean>;
  register: (email: string, username: string, password: string, fullName?: string) => Promise<{ success: boolean; error?: string }>;
  upgradeGuest: (email: string, username: string, password: string, fullName?: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('yatra_token'));
  const [isLoading, setIsLoading] = useState(true);

  const fetchProfile = async (currentToken: string) => {
    try {
      const res = await fetch(apiUrl('/auth/me'), {
        headers: { Authorization: `Bearer ${currentToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        if (data.is_authenticated && data.user) {
          setUser(data.user);
          return;
        }
      }
      // If invalid token, clear
      localStorage.removeItem('yatra_token');
      setToken(null);
      setUser(null);
    } catch (e) {
      console.error('Profile fetch error:', e);
    }
  };

  const loginAsGuest = async () => {
    try {
      const res = await fetch(apiUrl('/auth/guest'), { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('yatra_token', data.token);
        setToken(data.token);
        setUser(data.user);
      }
    } catch (e) {
      console.error('Guest login error:', e);
    }
  };

  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('yatra_token');
      if (savedToken) {
        setToken(savedToken);
        await fetchProfile(savedToken);
      } else {
        // Auto-initialize frictionless guest explorer
        await loginAsGuest();
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  const login = async (usernameOrEmail: string, password: string): Promise<boolean> => {
    try {
      const res = await fetch(apiUrl('/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username_or_email: usernameOrEmail, password }),
      });
      if (res.ok) {
        const data = await res.json();
        localStorage.setItem('yatra_token', data.token);
        setToken(data.token);
        setUser(data.user);
        return true;
      }
      return false;
    } catch (e) {
      console.error('Login error:', e);
      return false;
    }
  };

  const register = async (
    email: string,
    username: string,
    password: string,
    fullName?: string
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch(apiUrl('/auth/register'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, username, password, full_name: fullName }),
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data?.token) {
        localStorage.setItem('yatra_token', data.token);
        setToken(data.token);
        setUser(data.user);
        return { success: true };
      }
      return { success: false, error: apiErrorMessage(data, 'Registration failed. Please try again.') };
    } catch (e) {
      console.error('Register error:', e);
      return { success: false, error: 'Could not reach the server. Please try again.' };
    }
  };

  const upgradeGuest = async (
    email: string,
    username: string,
    password: string,
    fullName?: string
  ): Promise<{ success: boolean; error?: string }> => {
    try {
      const res = await fetch(apiUrl('/auth/upgrade'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({ email, username, password, full_name: fullName }),
      });
      const data = await res.json().catch(() => null);
      if (res.ok && data?.success) {
        localStorage.setItem('yatra_token', data.token);
        setToken(data.token);
        setUser(data.user);
        return { success: true };
      }
      return { success: false, error: apiErrorMessage(data, 'Upgrade failed') };
    } catch (e: any) {
      console.error('Upgrade error:', e);
      return { success: false, error: e.message || 'Network error' };
    }
  };

  const logout = () => {
    localStorage.removeItem('yatra_token');
    setToken(null);
    setUser(null);
    loginAsGuest();
  };

  const refreshProfile = async () => {
    if (token) {
      await fetchProfile(token);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        loginAsGuest,
        login,
        register,
        upgradeGuest,
        logout,
        refreshProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
