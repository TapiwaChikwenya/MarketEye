import { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Navbar } from '@/components/Navbar';
import { isAxiosError } from 'axios';
import { authService } from '@/services/auth';

function apiErrorMessage(err: unknown, fallback: string): string {
  if (!isAxiosError(err)) return fallback;
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return fallback;
}

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) {
      setError('Invalid or missing reset link. Request a new one from the forgot password page.');
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await authService.resetPassword(token, password);
      setDone(true);
      setTimeout(() => navigate('/login'), 2500);
    } catch (err: unknown) {
      setError(
        apiErrorMessage(err, 'This link may be invalid or expired. Request a new reset email.')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-dvh flex-col bg-background">
      <Navbar />
      <div className="relative flex flex-1 items-center justify-center p-6">
        <div className="pointer-events-none absolute inset-0 bg-mesh-hero opacity-40" />
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative z-10 w-full max-w-md"
        >
          <Card className="border-border/80 bg-card/95 shadow-lift-lg backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="font-display text-2xl">Set new password</CardTitle>
              <CardDescription>Choose a strong password you haven&apos;t used elsewhere.</CardDescription>
            </CardHeader>
            <CardContent>
              {done ? (
                <p className="text-sm text-muted-foreground">
                  Password updated. Redirecting to sign in…
                </p>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-4">
                  {error && (
                    <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                      {error}
                    </div>
                  )}
                  <div className="space-y-2">
                    <label htmlFor="password" className="text-sm font-medium text-foreground">
                      New password
                    </label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="new-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={8}
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="confirm" className="text-sm font-medium text-foreground">
                      Confirm password
                    </label>
                    <Input
                      id="confirm"
                      type="password"
                      autoComplete="new-password"
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      required
                      minLength={8}
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={loading || !token}>
                    {loading ? 'Saving…' : 'Update password'}
                  </Button>
                </form>
              )}
              <p className="mt-6 text-center text-sm text-muted-foreground">
                <Link to="/login" className="font-medium text-primary hover:underline">
                  Sign in
                </Link>
              </p>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}
