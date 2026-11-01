import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PropsWithChildren,
} from 'react';
import { API_URL, ApiError, parseResponse } from '../lib/api';
import type { TokenResponse, User } from '../types/api';

type AuthState = 'loading' | 'authenticated' | 'anonymous';

interface RequestOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
}

interface AuthContextValue {
  state: AuthState;
  user: User | null;
  login: () => void;
  logout: () => Promise<void>;
  refresh: () => Promise<boolean>;
  request: <T>(path: string, options?: RequestOptions) => Promise<T>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<AuthState>('loading');
  const [user, setUser] = useState<User | null>(null);
  const token = useRef<string | null>(null);
  const bootstrapped = useRef(false);

  const clearSession = useCallback(() => {
    token.current = null;
    setUser(null);
    setState('anonymous');
  }, []);

  const refresh = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      const session = await parseResponse<TokenResponse>(response);
      token.current = session.access_token;
      setUser(session.user);
      setState('authenticated');
      return true;
    } catch {
      clearSession();
      return false;
    }
  }, [clearSession]);

  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    void refresh();
  }, [refresh]);

  const request = useCallback(
    async <T,>(path: string, options: RequestOptions = {}): Promise<T> => {
      const execute = () =>
        fetch(`${API_URL}${path}`, {
          ...options,
          credentials: 'include',
          headers: {
            ...(options.body ? { 'Content-Type': 'application/json' } : {}),
            ...options.headers,
            ...(token.current ? { Authorization: `Bearer ${token.current}` } : {}),
          },
        });

      let response = await execute();
      if (response.status === 401 && (await refresh())) {
        response = await execute();
      }
      return parseResponse<T>(response);
    },
    [refresh],
  );

  const login = useCallback(() => {
    window.location.assign(`${API_URL}/api/v1/auth/github`);
  }, []);

  const logout = useCallback(async () => {
    try {
      await request<void>('/api/v1/auth/logout', { method: 'POST' });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) {
        console.error('Logout request failed', error);
      }
    } finally {
      clearSession();
    }
  }, [clearSession, request]);

  const value = useMemo(
    () => ({ state, user, login, logout, refresh, request }),
    [state, user, login, logout, refresh, request],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider.');
  }
  return value;
}
