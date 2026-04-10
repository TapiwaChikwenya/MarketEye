import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, TrendingUp, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Navbar } from '@/components/Navbar';
import { isAxiosError } from 'axios';
import { authService } from '@/services/auth';

export function Login() {
  const navigate = useNavigate();
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
      navigate('/dashboard');
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
    <div className="min-h-dvh bg-background cyber-grid-bg flex flex-col">
      <Navbar transparent />

      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-20 left-10 w-96 h-96 bg-[#0071e3]/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-10 w-96 h-96 bg-violet-400/10 rounded-full blur-3xl" />
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-6xl grid md:grid-cols-2 gap-8 relative z-10">
        {/* Left side - Branding */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          className="hidden md:flex flex-col justify-center"
        >
          <div className="mb-8">
            <h1 className="text-6xl font-semibold tracking-tight mb-4 text-foreground">
              Market<span className="text-[#0071e3]">Eye</span>
            </h1>
            <p className="text-xl text-muted-foreground mb-8">
              24/7 Investment Watcher
            </p>
          </div>

          <div className="space-y-6">
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-[#0071e3]/10 flex items-center justify-center">
                <Eye className="text-[#0071e3]" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Real-time Monitoring</h3>
                <p className="text-sm text-muted-foreground">
                  Track stocks, crypto, and ETFs 24/7 with live price updates
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-violet-500/10 flex items-center justify-center">
                <TrendingUp className="text-violet-600" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Smart Alerts</h3>
                <p className="text-sm text-muted-foreground">
                  Get instant notifications via SMS, call, or email
                </p>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="w-12 h-12 rounded-2xl bg-[#34c759]/10 flex items-center justify-center">
                <Shield className="text-[#34c759]" size={24} />
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-1">Secure & Private</h3>
                <p className="text-sm text-muted-foreground">
                  Your data is encrypted and protected
                </p>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Right side - Login form */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          className="flex items-center"
        >
          <Card className="w-full border-black/[0.06] shadow-lg bg-white/95">
            <CardHeader>
              <CardTitle className="text-2xl text-foreground">Welcome back</CardTitle>
              <CardDescription>
                Sign in to your MarketEye account
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <div className="p-3 rounded-md bg-destructive/20 border border-destructive/50 text-destructive text-sm">
                    {error}
                  </div>
                )}

                <div className="space-y-2">
                  <label htmlFor="email" className="text-sm font-medium">
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
                  <label htmlFor="password" className="text-sm font-medium">
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

                <Button
                  type="submit"
                  variant="default"
                  className="w-full"
                  disabled={loading}
                >
                  {loading ? 'Signing in...' : 'Sign In'}
                </Button>

                <div className="text-center text-sm text-muted-foreground">
                  Don't have an account?{' '}
                  <Link to="/register" className="text-[#0071e3] hover:underline">
                    Sign up
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
