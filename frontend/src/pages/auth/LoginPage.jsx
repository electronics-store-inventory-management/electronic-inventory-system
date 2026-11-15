import { useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import Icon from "../../components/Icon";
import AuthLayout from "./AuthLayout";
import AuthSessionStatus from "./AuthSessionStatus";

export default function LoginPage() {
  const { isAuthenticated, session, signIn } = useAuth();
  const location = useLocation();
  const [username, setUsername] = useState(() => location.state?.registeredUsername ?? "");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  if (isAuthenticated) {
    const from = location.state?.from;
    const destination =
      typeof from === "string" && /^\/(?![/\\])/.test(from)
        ? from
        : "/products";
    return <Navigate to={destination} replace />;
  }

  if (session) return <AuthSessionStatus />;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await signIn(username.trim(), password);
    } catch (loginError) {
      setError(loginError.message || "Unable to sign in. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Welcome back" description="Sign in to your inventory workspace.">
      {location.state?.registeredUsername && (
        <p className="ui-feedback ui-tone-success auth-notice" role="status">Account created. Sign in to get started.</p>
      )}
      <form className="login-form" onSubmit={handleSubmit}>
        <div className="login-field">
          <label htmlFor="username">Username</label>
          <input
            className="ui-field"
            id="username"
            name="username"
            type="text"
            autoComplete="username"
            required
            maxLength={50}
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={loading}
          />
        </div>
        <div className="login-field">
          <label htmlFor="password">Password</label>
          <div className="password-input-wrap">
            <input
              className="ui-field"
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              maxLength={128}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={loading}
            />
            <button
              className="ui-button ui-button--secondary password-toggle"
              type="button"
              onClick={() => setShowPassword((visible) => !visible)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              aria-pressed={showPassword}
              disabled={loading}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>
            </button>
          </div>
        </div>
        {error && (
          <p className="ui-feedback ui-tone-error login-error" role="alert">
            <Icon name="warning" />{error}
          </p>
        )}
        <button className="ui-button login-submit" type="submit" disabled={loading}>
          {loading
            ? <><span className="ui-spinner" aria-hidden="true" />Signing in…</>
            : <>Sign in <Icon name="arrow" /></>}
        </button>
        <div role="status" className="login-status">{loading ? "Signing in…" : ""}</div>
      </form>
      <p className="login-footer">
        New to ElectroStock? <Link to="/signup" state={{ from: location.state?.from }}>Create an account</Link>
      </p>
    </AuthLayout>
  );
}
