import { useState } from "react";
import { api } from "../api";
import { setToken } from "../auth";

export function Login({ onLoggedIn }: { onLoggedIn: () => void }) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { access_token } = await api.devLogin(email, name || undefined);
      setToken(access_token);
      onLoggedIn();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-card">
      <h1>LeBox</h1>
      <p style={{ color: "#666" }}>Dev mode — enter any email to sign in.</p>
      <form onSubmit={submit}>
        <div style={{ marginBottom: 12 }}>
          <input
            type="email" required placeholder="you@example.com"
            value={email} onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <input
            type="text" placeholder="Display name (optional)"
            value={name} onChange={(e) => setName(e.target.value)}
            style={{ width: "100%" }}
          />
        </div>
        {error && <div className="error">{error}</div>}
        <button className="primary" type="submit" disabled={loading}>
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
