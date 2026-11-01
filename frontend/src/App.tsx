import { lazy, Suspense } from 'react';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { AppShell } from './components/AppShell';
import { ProtectedRoute } from './components/ProtectedRoute';
import { AnalysesPage } from './pages/AnalysesPage';
import { AuthCallbackPage } from './pages/AuthCallbackPage';
import { LandingPage } from './pages/LandingPage';

const AnalysisDetailPage = lazy(() =>
  import('./pages/AnalysisDetailPage').then((module) => ({ default: module.AnalysisDetailPage })),
);

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/analyses" element={<AnalysesPage />} />
              <Route
                path="/analyses/:analysisId"
                element={
                  <Suspense fallback={<div className="state-panel">Loading analysis workspace…</div>}>
                    <AnalysisDetailPage />
                  </Suspense>
                }
              />
            </Route>
          </Route>
          <Route path="*" element={<LandingPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
