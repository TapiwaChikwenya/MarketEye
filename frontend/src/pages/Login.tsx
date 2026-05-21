import { useState } from 'react';
import { useNavigate, useLocation, Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, TrendingUp, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Navbar } from '@/components/Navbar';
import { isAxiosError } from 'axios';
import { authService } from '@/services/auth';

function postLoginPath(location: ReturnType<typeof useLocation>, searchParams: URLSearchParams): string {
  const fromState = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;
  const returnTo = searchParams.get('returnTo');
  const candidate = fromState || returnTo;
  if (candidate && candidate.startsWith('/') && !candidate.startsWith('//')) {
    return candidate;
  }
  return '/dashboard';
}

export function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await authService.login({ username: email, password });
      navigate(postLoginPath(location, searchParams), { replace: true });
    } catch (err: unknown) {
      if (!isAxiosError(err)) {
        setError('Login failed. Please try again.');
        return;
      }
      const detail = err.response?.data && typeof err.response.data === 'object' && err.response.data !== null && 'detail' in err.response.data
        ? (err.response.data as { detail?: unknown }).detail
        : undefined;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        type ValidationItem = { msg?: string; message?: string };
        setError(
          detail
            .map((e) => (typeof e === 'object' && e !== null ? (e as ValidationItem).msg || (e as ValidationItem).message : undefined) || JSON.stringify(e))
            .join('. ')
        );
      } else if (typeof detail === 'object' && detail !== null) {
        const d = detail as { msg?: string; message?: string };
        setError(d.msg || d.message || 'Login failed. Please try again.');
      } else {
        setError('Login failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <Navbar />

      <div className="relative flex flex-1">
        <div className="pointer-events-none absolute inset-0 bg-mesh-hero opacity-40" />
        <div className="pointer-events-none absolute inset-0 cyber-grid-bg opacity-50" />

        <div className="relative z-10 mx-auto grid w-full max-w-6xl flex-1 grid-cols-1 gap-0 p-6 md:grid-cols-2 md:gap-12 md:p-10 lg:items-center">
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            className="relative hidden overflow-hidden rounded-2xl border border-white/10 bg-ink p-10 text-white shadow-2xl md:flex md:flex-col md:justify-center"
          >
            <div className="pointer-events-none absolute inset-0 bg-hero-dark opacity-90" />
            <div className="pointer-events-none absolute -right-20 top-0 h-64 w-64 rounded-full bg-brass/15 blur-3xl" />
            <div className="relative">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brass">MarketEye</p>
              <h1 className="font-display mt-4 text-4xl font-semibold leading-tight tracking-tight lg:text-5xl">
                Sign in to your workspace
              </h1>
              <p className="mt-4 text-base leading-relaxed text-white/60">
                Same alerting surface as the public product — tuned for operators who live in tick data.
              </p>
              <div className="mt-10 space-y-6">
                <div className="flex gap-4">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/10">
                    <Eye className="text-brass" size={22} />
                  </div>
                  <div>
                    <h3 className="font-medium text-white">Real-time marks</h3>
                    <p className="text-sm text-white/55">Stocks, crypto, and funds in one stream.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/10">
                    <TrendingUp className="text-primary" size={22} />
                  </div>
                  <div>
                    <h3 className="font-medium text-white">Alerts that scale</h3>
                    <p className="text-sm text-white/55">SMS, voice, email — with guardrails.</p>
                  </div>
                </div>
                <div className="flex gap-4">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 ring-1 ring-white/10">
                    <Shield className="text-success" size={22} />
                  </div>
                  <div>
                    <h3 className="font-medium text-white">Institutional posture</h3>
                    <p className="text-sm text-white/55">Encryption and least-privilege by default.</p>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 24 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center justify-center"
          >
            <Card className="w-full border-border/80 bg-card/95 shadow-lift-lg backdrop-blur-sm">
              <CardHeader>
                <CardTitle className="font-display text-2xl text-foreground">Welcome back</CardTitle>
                <CardDescription>Sign in to continue to your dashboard.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
                    <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                      {error}
                    </div>
                  )}

                  <div className="space-y-2">
                    <label htmlFor="email" className="text-sm font-medium text-foreground">
                      Email
                    </label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="you@example.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                    />
                  </div>

                  <div className="space-y-2">
                    <label htmlFor="password" className="text-sm font-medium text-foreground">
                      Password
                    </label>
                    <Input
                      id="password"
                      type="password"
                      placeholder="••••••••"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                  </div>

                  <Button type="submit" variant="default" className="w-full" disabled={loading}>
                    {loading ? 'Signing in…' : 'Sign in'}
                  </Button>

                <div className="text-center text-sm text-muted-foreground">
                  <Link to="/forgot-password" className="font-medium text-primary hover:underline">
                    Forgot password?
                  </Link>
                </div>

                <div className="text-center text-sm text-muted-foreground">
                  Don&apos;t have an account?{' '}
                  <Link to="/register" className="font-medium text-primary hover:underline">
                    Create one
                  </Link>
                </div>
                </form>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
