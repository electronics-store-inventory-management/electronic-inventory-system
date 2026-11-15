import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/useAuth";
import { register } from "../../services/authService";
import AuthLayout from "./AuthLayout";
import AuthSessionStatus from "./AuthSessionStatus";
import { validateSignup } from "./signupValidation";

export default function SignupPage() {
  const { session, isAuthenticated } = useAuth();
  const { state } = useLocation();
  const navigate = useNavigate();
  const [fields, setFields] = useState({ username: "", password: "", confirmation: "" });
  const [visible, setVisible] = useState(false);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (isAuthenticated) return <Navigate to="/" replace />;
  if (session) return <AuthSessionStatus />;

  function changeField(event) {
    const { name, value } = event.target;
    setFields({ ...fields, [name]: value });
    setErrors({ ...errors, [name]: undefined, ...(name === "password" && { confirmation: undefined }) });
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    if (loading) return;
    const issues = validateSignup(fields);
    setErrors(issues);
    setError("");
    if (Object.keys(issues).length) {
      event.currentTarget.elements[Object.keys(issues)[0]].focus();
      return;
    }
    const username = fields.username.trim();
    setLoading(true);
    try {
      await register(username, fields.password);
      navigate("/login", { replace: true, state: { from: state?.from, registeredUsername: username } });
    } catch (failure) {
      if (failure.status === 409) setErrors({ username: "That username is already taken. Choose another." });
      else setError(failure.message || "Could not create your account. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout title="Create your account" description="Sign up for an employee account in ElectroStock.">
      <form className="login-form" onSubmit={submit} noValidate>
        <div className="login-field">
          <label htmlFor="signup-username">Username</label>
          <input className="ui-field" id="signup-username" name="username" autoComplete="username"
            value={fields.username} onChange={changeField} maxLength={50} required disabled={loading}
            aria-invalid={Boolean(errors.username)} aria-describedby={errors.username ? "signup-username-error" : "signup-username-help"} />
          {errors.username
            ? <small className="auth-field-error" id="signup-username-error" role="alert">{errors.username}</small>
            : <small id="signup-username-help">3–50 letters, numbers, periods, underscores, or hyphens.</small>}
        </div>
        <div className="login-field">
          <label htmlFor="signup-password">Password</label>
          <div className="password-input-wrap">
            <input className="ui-field" id="signup-password" name="password" autoComplete="new-password"
              type={visible ? "text" : "password"} value={fields.password} onChange={changeField} required disabled={loading}
              aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "signup-password-error" : "signup-password-help"} />
            <button className="ui-button ui-button--secondary password-toggle" type="button"
              aria-label={visible ? "Hide passwords" : "Show passwords"} aria-pressed={visible}
              onClick={() => setVisible(!visible)} disabled={loading}>{visible ? "Hide" : "Show"}</button>
          </div>
          {errors.password
            ? <small className="auth-field-error" id="signup-password-error" role="alert">{errors.password}</small>
            : <small id="signup-password-help">12–128 characters with a letter and a number or symbol.</small>}
        </div>
        <div className="login-field">
          <label htmlFor="signup-confirmation">Confirm password</label>
          <input className="ui-field" id="signup-confirmation" name="confirmation" autoComplete="new-password"
            type={visible ? "text" : "password"} value={fields.confirmation} onChange={changeField} required disabled={loading}
            aria-invalid={Boolean(errors.confirmation)} aria-describedby={errors.confirmation ? "signup-confirmation-error" : undefined} />
          {errors.confirmation && <small className="auth-field-error" id="signup-confirmation-error" role="alert">{errors.confirmation}</small>}
        </div>
        {error && <p className="login-error ui-feedback ui-tone-error" role="alert">{error}</p>}
        <button className="ui-button login-submit" type="submit" disabled={loading}>
          {loading && <span className="ui-spinner" aria-hidden="true" />}
          {loading ? "Creating account…" : "Create account"}
        </button>
        <div className="login-status" role="status">{loading ? "Creating account…" : ""}</div>
      </form>
      <p className="login-footer">Already registered? <Link to="/login" state={{ from: state?.from }}>Sign in</Link></p>
    </AuthLayout>
  );
}
