import { useEffect, useState } from "react";
import { api, UserOut } from "./api";
import { clearToken, getToken } from "./auth";
import { Login } from "./components/Login";
import { FileBrowser } from "./components/FileBrowser";

export function App() {
  const [user, setUser] = useState<UserOut | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = async () => {
    if (!getToken()) { setUser(null); setLoading(false); return; }
    try {
      setUser(await api.me());
    } catch {
      clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { refresh(); }, []);

  const logout = () => { clearToken(); setUser(null); };

  if (loading) return <div className="container">Loading…</div>;
  if (!user) return <Login onLoggedIn={refresh} />;

  return (
    <>
      <header>
        <strong>LeBox</strong>
        <div>
          <span style={{ marginRight: 12, color: "#666" }}>{user.email}</span>
          <button onClick={logout}>Sign out</button>
        </div>
      </header>
      <FileBrowser />
    </>
  );
}
