import Icon from "../../components/Icon";
import "./LoginPage.css";

export default function AuthLayout({ title, description, children }) {
  return (
    <main className="login-page">
      <div className="ui-card login-card">
        <div className="login-brand">
          <div className="login-wordmark">
            <div className="brand-mark"><Icon name="bolt" /></div>
            <div className="login-brand-text">
              <strong>ElectroStock</strong>
              <span>Inventory management</span>
            </div>
          </div>
          <div className="login-art" aria-hidden="true">
            <div className="login-art-orbit" />
            <div className="login-art-tile login-art-tile--back"><Icon name="inventory" /></div>
            <div className="login-art-tile login-art-tile--front"><Icon name="products" /></div>
            <div className="login-art-status"><Icon name="check" /></div>
          </div>
        </div>
        <section className="login-content" aria-labelledby="auth-title">
          <div className="login-heading">
            <h1 id="auth-title">{title}</h1>
            <p>{description}</p>
          </div>
          {children}
        </section>
      </div>
    </main>
  );
}
