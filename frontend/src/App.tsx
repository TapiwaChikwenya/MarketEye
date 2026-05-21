import {
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  useNavigate,
  useLocation,
} from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Toaster } from 'sonner';
import { Landing } from './pages/Landing';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';
import { Dashboard } from './pages/Dashboard';
import { Admin } from './pages/Admin';
import { authService } from './services/auth';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const location = useLocation();
  if (!authService.isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <>{children}</>;
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const [gate, setGate] = useState<'loading' | 'allow' | 'deny'>('loading');

  useEffect(() => {
    if (!authService.isAuthenticated()) {
      navigate('/login', {
        replace: true,
        state: { from: { pathname: '/admin' } },
      });
      return;
    }
    let cancelled = false;
    authService
      .getCurrentUser()
      .then((u) => {
        if (cancelled) return;
        if (u.is_superuser) setGate('allow');
        else setGate('deny');
      })
      .catch(() => {
        if (!cancelled) setGate('deny');
      });
    return () => {
      cancelled = true;
    };
  }, [navigate]);

  if (gate === 'loading') {
    return (
      <div className="flex min-h-dvh items-center justify-center bg-background text-muted-foreground">
        Loading…
      </div>
    );
  }
  if (gate === 'deny') {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route
            path="/dashboard"
            element={
              <PrivateRoute>
                <Dashboard />
              </PrivateRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <PrivateRoute>
                <AdminRoute>
                  <Admin />
                </AdminRoute>
              </PrivateRoute>
            }
          />
        </Routes>
        <Toaster position="top-right" theme="dark" />
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
