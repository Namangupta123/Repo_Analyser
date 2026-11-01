import { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { LoadingState } from '../components/States';

export function AuthCallbackPage() {
  const { state } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (state === 'authenticated') {
      navigate('/analyses', { replace: true });
    }
  }, [navigate, state]);

  if (state === 'anonymous') {
    return (
      <main className="state-screen callback-error">
        <p className="eyebrow">Authentication interrupted</p>
        <h1>We could not restore your GitHub session.</h1>
        <p>Return to the login page and start the sign-in flow again.</p>
        <Link className="button button-primary" to="/">
          Back to login
        </Link>
      </main>
    );
  }

  return <LoadingState label="Completing secure GitHub sign-in" fullPage />;
}
