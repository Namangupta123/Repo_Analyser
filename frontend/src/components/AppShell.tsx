import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const signOut = async () => {
    await logout();
    navigate('/');
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <NavLink className="brand" to="/analyses" aria-label="SystemLab analyses">
          <span className="brand-mark" aria-hidden="true">
            <i />
            <i />
            <i />
          </span>
          <span>SystemLab</span>
          <em>v0</em>
        </NavLink>

        <nav className="topbar-nav" aria-label="Primary navigation">
          <NavLink to="/analyses">Repositories</NavLink>
        </nav>

        <div className="account">
          <div className="account-copy">
            <strong>{user?.display_name ?? user?.email ?? 'Engineer'}</strong>
            <span>{user?.email}</span>
          </div>
          {user?.avatar_url ? (
            <img className="avatar" src={user.avatar_url} alt="" referrerPolicy="no-referrer" />
          ) : (
            <span className="avatar avatar-fallback" aria-hidden="true">
              {(user?.display_name ?? user?.email ?? 'E').charAt(0).toUpperCase()}
            </span>
          )}
          <button className="button button-ghost button-small" type="button" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>
      <main className="app-content">
        <Outlet />
      </main>
    </div>
  );
}
