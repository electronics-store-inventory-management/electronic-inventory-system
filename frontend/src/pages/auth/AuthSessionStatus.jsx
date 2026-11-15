import { useAuth } from "../../auth/useAuth";
import AuthLayout from "./AuthLayout";

export default function AuthSessionStatus() {
  const { sessionError, retrySession, logout } = useAuth();
  return (
    <AuthLayout title="Checking your session">
      {sessionError ? (
        <div className="login-form">
          <p className="ui-feedback ui-tone-error login-error" role="alert">{sessionError}</p>
          <button className="ui-button" type="button" onClick={retrySession}>Retry</button>
          <button className="ui-button ui-button--secondary" type="button" onClick={logout}>Back to sign in</button>
        </div>
      ) : (
        <p className="login-error" role="status"><span className="ui-spinner" aria-hidden="true" /> Connecting to ElectroStock…</p>
      )}
    </AuthLayout>
  );
}
