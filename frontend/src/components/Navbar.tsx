import { Link, useLocation, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Eye, Home, LayoutDashboard, LogIn, UserPlus, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { authService } from '@/services/auth';
import { cn } from '@/lib/utils';

interface NavbarProps {
  transparent?: boolean;
  showAuthButtons?: boolean;
}

export function Navbar({ transparent = false, showAuthButtons = true }: NavbarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const isAuthenticated = authService.isAuthenticated();

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      className={cn(
        "sticky top-0 z-50 border-b",
        transparent 
          ? "glass border-neon-cyan/20" 
          : "bg-cyber-darker/95 backdrop-blur-md border-neon-cyan/20"
      )}
    >
      <div className="container mx-auto px-4 sm:px-6 py-3 sm:py-4">
        <div className="flex items-center justify-between gap-2">
          {/* Logo and Navigation */}
          <div className="flex min-w-0 items-center gap-4 md:gap-8">
            <Link to="/" className="flex min-w-0 items-center gap-2 sm:gap-3 group">
              <div className="h-11 w-11 shrink-0 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-magenta flex items-center justify-center group-hover:scale-105 transition-transform">
                <Eye className="text-white" size={20} />
              </div>
              <h1 className="truncate text-xl sm:text-2xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
                MarketEye
              </h1>
            </Link>

            {/* Navigation */}
            <nav className="hidden md:flex items-center gap-6">
              <Link 
                to="/" 
                className={cn(
                  "flex items-center gap-2 text-sm font-medium transition-colors hover:text-neon-cyan",
                  location.pathname === "/" ? "text-neon-cyan" : "text-muted-foreground"
                )}
              >
                <Home size={16} />
                Home
              </Link>
              
              {isAuthenticated && (
                <Link 
                  to="/dashboard" 
                  className={cn(
                    "flex items-center gap-2 text-sm font-medium transition-colors hover:text-neon-cyan",
                    location.pathname === "/dashboard" ? "text-neon-cyan" : "text-muted-foreground"
                  )}
                >
                  <LayoutDashboard size={16} />
                  Dashboard
                </Link>
              )}
            </nav>
          </div>

          {/* Auth Buttons */}
          {showAuthButtons && (
            <div className="flex items-center gap-3">
              {isAuthenticated ? (
                <>
                  <Button 
                    variant="ghost" 
                    size="sm"
                    onClick={() => navigate('/dashboard')}
                    className="hidden md:flex"
                  >
                    <LayoutDashboard size={16} className="mr-2" />
                    Dashboard
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="icon"
                    onClick={handleLogout}
                    title="Logout"
                  >
                    <LogOut size={18} />
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => navigate('/login')}
                    className="sm:hidden shrink-0"
                    title="Sign in"
                    aria-label="Sign in"
                  >
                    <LogIn size={22} />
                  </Button>
                  <Button 
                    variant="ghost" 
                    onClick={() => navigate('/login')}
                    className="hidden sm:inline-flex"
                  >
                    <LogIn size={16} className="mr-2" />
                    Sign In
                  </Button>
                  <Button 
                    variant="neon" 
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

