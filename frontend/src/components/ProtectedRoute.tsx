import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { LoadingState } from './States';

export function ProtectedRoute() {
  const { state } = useAuth();
  const location = useLocation();

  if (state === 'loading') {
    return <LoadingState label="Restoring your SystemLab session" fullPage />;
  }

  if (state === 'anonymous') {
    return <Navigate to="/" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
