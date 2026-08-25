import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { clearToken, fetchMe, getToken, logoutSession, setToken, wakeApi } from "./api";

interface User {
  id: number;
  email: string;
  name: string;
  picture?: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    wakeApi();
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }
    fetchMe()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false));
  }, []);

  async function login(token: string) {
    setToken(token);
    const me = await fetchMe();
    setUser(me);
  }

  function logout() {
    logoutSession().finally(() => {
      clearToken();
      setUser(null);
    });
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
