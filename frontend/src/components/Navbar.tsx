import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, Home, LayoutDashboard, LogIn, UserPlus, LogOut, Shield } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authService } from '@/services/auth';
import type { User } from '@/types';
import { cn } from '@/lib/utils';

interface NavbarProps {
  transparent?: boolean;
  showAuthButtons?: boolean;
  /** Dark shell — white typography (marketing hero) */
  appearance?: 'default' | 'dark';
}

export function Navbar({
  transparent = false,
  showAuthButtons = true,
  appearance = 'default',
}: NavbarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isAuthenticated = authService.isAuthenticated();
  const isDark = appearance === 'dark';
  const [me, setMe] = useState<User | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      setMe(null);
      return;
    }
    let cancelled = false;
    authService
      .getCurrentUser()
      .then((u) => {
        if (!cancelled) setMe(u);
      })
      .catch(() => {
        if (!cancelled) setMe(null);
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className={cn(
        'sticky top-0 z-50',
        isDark
          ? 'glass-dark border-b border-white/[0.06]'
          : transparent
            ? 'glass border-b border-foreground/[0.06]'
            : 'border-b border-border bg-card/90 backdrop-blur-xl supports-[backdrop-filter]:bg-card/85'
      )}
    >
      <div className="container mx-auto px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-4 md:gap-8">
            <Link to="/" className="flex min-w-0 items-center gap-2 sm:gap-3 group">
              <div
                className={cn(
                  'h-11 w-11 shrink-0 rounded-xl flex items-center justify-center transition-transform group-hover:scale-[1.02]',
                  isDark
                    ? 'bg-gradient-to-br from-primary to-ink-elevated ring-1 ring-brass/35 shadow-lg shadow-black/30'
                    : 'bg-gradient-to-br from-primary to-primary/85 shadow-md shadow-primary/15'
                )}
              >
                <Eye className="text-white" size={20} />
              </div>
              <h1
                className={cn(
                  'truncate font-display text-xl sm:text-2xl font-semibold tracking-tight',
                  isDark ? 'text-white' : 'text-foreground'
                )}
              >
                MarketEye
              </h1>
            </Link>

            <nav className="hidden md:flex items-center gap-6">
              <Link
                to="/"
                className={cn(
                  'flex items-center gap-2 text-sm font-medium transition-colors',
                  isDark
                    ? location.pathname === '/'
                      ? 'text-brass'
                      : 'text-white/65 hover:text-white'
                    : location.pathname === '/'
                      ? 'text-primary'
                      : 'text-muted-foreground hover:text-primary'
                )}
              >
                <Home size={16} />
                Home
              </Link>

              {isAuthenticated && (
                <Link
                  to="/dashboard"
                  className={cn(
                    'flex items-center gap-2 text-sm font-medium transition-colors',
                    isDark
                      ? location.pathname === '/dashboard'
                        ? 'text-brass'
                        : 'text-white/65 hover:text-white'
                      : location.pathname === '/dashboard'
                        ? 'text-primary'
                        : 'text-muted-foreground hover:text-primary'
                  )}
                >
                  <LayoutDashboard size={16} />
                  Dashboard
                </Link>
              )}
              {isAuthenticated && me?.is_superuser && (
                <Link
                  to="/admin"
                  className={cn(
                    'flex items-center gap-2 text-sm font-medium transition-colors',
                    isDark
                      ? location.pathname === '/admin'
                        ? 'text-brass'
                        : 'text-white/65 hover:text-white'
                      : location.pathname === '/admin'
                        ? 'text-primary'
                        : 'text-muted-foreground hover:text-primary'
                  )}
                >
                  <Shield size={16} />
                  Admin
                </Link>
              )}
            </nav>
          </div>

          {showAuthButtons && (
            <div className="flex items-center gap-2 sm:gap-3">
              {isAuthenticated ? (
                <>
                  <Button
                    variant={isDark ? 'dark-ghost' : 'ghost'}
                    size="sm"
                    onClick={() => navigate('/dashboard')}
                    className="hidden md:flex"
                  >
                    <LayoutDashboard size={16} className="mr-2" />
                    Dashboard
                  </Button>
                  {me?.is_superuser && (
                    <Button
                      variant={isDark ? 'dark-ghost' : 'ghost'}
                      size="sm"
                      onClick={() => navigate('/admin')}
                      className="hidden lg:flex"
                      title="Admin"
                    >
                      <Shield size={16} className="mr-2" />
                      Admin
                    </Button>
                  )}
                  <Button
                    variant={isDark ? 'dark-ghost' : 'ghost'}
                    size="icon"
                    onClick={handleLogout}
                    title="Logout"
                    aria-label="Logout"
                  >
                    <LogOut size={18} />
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant={isDark ? 'dark-ghost' : 'ghost'}
                    size="icon"
                    onClick={() => navigate('/login')}
                    className="sm:hidden shrink-0"
                    title="Sign in"
                    aria-label="Sign in"
                  >
                    <LogIn size={22} />
                  </Button>
                  <Button
                    variant={isDark ? 'dark-ghost' : 'ghost'}
                    onClick={() => navigate('/login')}
                    className="hidden sm:inline-flex"
                  >
                    <LogIn size={16} className="mr-2" />
                    Sign In
                  </Button>
                  <Button
                    variant={isDark ? 'dark-solid' : 'default'}
                    onClick={() => navigate('/register')}
                    className="shrink-0 px-3 sm:px-4"
                  >
                    <UserPlus size={16} className="sm:mr-2" />
                    <span className="sm:hidden">Start</span>
                    <span className="hidden sm:inline">Get Started</span>
                  </Button>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </motion.header>
  );
}
