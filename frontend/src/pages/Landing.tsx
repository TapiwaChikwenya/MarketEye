import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Eye,
  TrendingUp,
  TrendingDown,
  Bell,
  Shield,
  Zap,
  ArrowRight,
  Sparkles,
  Target,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Navbar } from '@/components/Navbar';
import { API_URL } from '@/lib/api-config';
import axios from 'axios';

interface TrendingAsset {
  symbol: string;
  name: string;
  current_price: string;
  change_percent_24h: string;
}

interface PublicTrendingPayload {
  stocks: TrendingAsset[];
  crypto: TrendingAsset[];
  funds?: TrendingAsset[];
  market_summary: {
    gainers: number;
    losers: number;
  };
}

interface PublicMarketStats {
  uptime: string;
  total_users: number;
  alerts_triggered_today: number;
}

export function Landing() {
  const navigate = useNavigate();
  const [trendingData, setTrendingData] = useState<PublicTrendingPayload | null>(null);
  const [stats, setStats] = useState<PublicMarketStats | null>(null);

  useEffect(() => {
    // Fetch trending assets and stats
    const fetchData = async () => {
      try {
        const [trendingRes, statsRes] = await Promise.all([
          axios.get(`${API_URL}/api/v1/public/trending`),
          axios.get(`${API_URL}/api/v1/public/market-stats`),
        ]);
        setTrendingData(trendingRes.data);
        setStats(statsRes.data);
      } catch (error) {
        console.error('Error fetching data:', error);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // Update every minute

    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      icon: Eye,
      title: '24/7 Market Monitoring',
      description: 'Track stocks, crypto, and ETFs around the clock with real-time updates',
      color: 'neon-cyan',
    },
    {
      icon: Bell,
      title: 'Smart Alerts',
      description: 'Get instant notifications via SMS, call, or email when conditions are met',
      color: 'neon-magenta',
    },
    {
      icon: TrendingUp,
      title: 'Portfolio Tracking',
      description: 'Monitor your investments with real-time P&L calculations',
      color: 'neon-lime',
    },
    {
      icon: Shield,
      title: 'Secure & Private',
      description: 'Bank-level encryption and security for your data',
      color: 'neon-cyan',
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Sub-100ms response times for real-time market data',
      color: 'neon-magenta',
    },
    {
      icon: Target,
      title: 'Precision Alerts',
      description: 'Set custom conditions with price, percentage, and volume triggers',
      color: 'neon-lime',
    },
  ];

  return (
    <div className="min-h-dvh bg-cyber-darker cyber-grid-bg overflow-hidden">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.1, 0.15, 0.1],
          }}
          transition={{ duration: 8, repeat: Infinity }}
          className="absolute top-20 left-10 w-96 h-96 bg-neon-cyan rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 1.3, 1],
            opacity: [0.1, 0.15, 0.1],
          }}
          transition={{ duration: 10, repeat: Infinity, delay: 1 }}
          className="absolute bottom-20 right-10 w-96 h-96 bg-neon-magenta rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 1.15, 1],
            opacity: [0.05, 0.1, 0.05],
          }}
          transition={{ duration: 12, repeat: Infinity, delay: 2 }}
          className="absolute top-1/2 left-1/2 w-96 h-96 bg-neon-lime rounded-full blur-3xl"
        />
      </div>

      {/* Header with Navbar */}
      <Navbar transparent />

      {/* Hero Section */}
      <section className="relative z-10 container mx-auto px-6 py-20">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="inline-block px-4 py-2 rounded-full glass border border-neon-cyan/30 mb-6">
              <div className="flex items-center gap-2 text-sm">
                <div className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse" />
                <span className="text-neon-cyan">Live Market Data • Free Forever</span>
              </div>
            </div>

            <h2 className="text-6xl font-bold mb-6 leading-tight">
              Never Miss a
              <br />
              <span className="bg-gradient-to-r from-neon-cyan via-neon-magenta to-neon-lime bg-clip-text text-transparent animate-gradient">
                Market Move
              </span>
            </h2>

            <p className="text-xl text-muted-foreground mb-8">
              24/7 investment monitoring with intelligent alerts. Track stocks, crypto, and ETFs
              with real-time notifications via SMS, calls, and email.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 mb-8">
              <Button
                variant="neon"
                size="lg"
                className="gap-2"
                onClick={() => navigate('/register')}
              >
                <Sparkles size={20} />
                Start Monitoring Free
                <ArrowRight size={20} />
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={() =>
                  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
                }
              >
                See How It Works
              </Button>
            </div>

            {stats && (
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <div className="text-3xl font-bold text-neon-cyan">{stats.total_users}</div>
                  <div className="text-sm text-muted-foreground">Active Users</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-neon-magenta">
                    {stats.alerts_triggered_today}
                  </div>
                  <div className="text-sm text-muted-foreground">Alerts Today</div>
                </div>
                <div>
                  <div className="text-3xl font-bold text-neon-lime">{stats.uptime}</div>
                  <div className="text-sm text-muted-foreground">Uptime</div>
                </div>
              </div>
            )}
          </motion.div>

          {/* Live Market Data Preview */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.6, delay: 0.2 }}
          >
            <Card className="glass border-neon-cyan/30 p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-xl font-semibold text-neon-cyan">Live Market Data</h3>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse" />
                  <span className="text-sm text-muted-foreground">Updating...</span>
                </div>
              </div>

              {trendingData ? (
                <div className="space-y-4">
                  {/* Stocks */}
                  <div>
                    <h4 className="text-sm font-medium text-muted-foreground mb-3">
                      Top Stocks
                    </h4>
                    <div className="space-y-2">
                      {trendingData.stocks.slice(0, 3).map((asset: TrendingAsset) => (
                        <motion.div
                          key={asset.symbol}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="flex items-center justify-between p-3 rounded-lg bg-cyber-dark/50 hover:bg-cyber-dark transition-colors"
                        >
                          <div>
                            <div className="font-semibold text-neon-cyan">{asset.symbol}</div>
                            <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                              {asset.name}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">
                              ${parseFloat(asset.current_price).toFixed(2)}
                            </div>
                            <div
                              className={`text-sm flex items-center gap-1 ${
                                parseFloat(asset.change_percent_24h) >= 0
                                  ? 'text-neon-lime'
                                  : 'text-neon-magenta'
                              }`}
                            >
                              {parseFloat(asset.change_percent_24h) >= 0 ? (
                                <TrendingUp size={14} />
                              ) : (
                                <TrendingDown size={14} />
                              )}
                              {Math.abs(parseFloat(asset.change_percent_24h)).toFixed(2)}%
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>

                  {/* Crypto */}
                  <div>
                    <h4 className="text-sm font-medium text-muted-foreground mb-3">
                      Top Crypto
                    </h4>
                    <div className="space-y-2">
                      {trendingData.crypto.slice(0, 3).map((asset: TrendingAsset) => (
                        <motion.div
                          key={asset.symbol}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          className="flex items-center justify-between p-3 rounded-lg bg-cyber-dark/50 hover:bg-cyber-dark transition-colors"
                        >
                          <div>
                            <div className="font-semibold text-neon-magenta">{asset.symbol}</div>
                            <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                              {asset.name}
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium">
                              ${parseFloat(asset.current_price).toLocaleString()}
                            </div>
                            <div
                              className={`text-sm flex items-center gap-1 ${
                                parseFloat(asset.change_percent_24h) >= 0
                                  ? 'text-neon-lime'
                                  : 'text-neon-magenta'
                              }`}
                            >
                              {parseFloat(asset.change_percent_24h) >= 0 ? (
                                <TrendingUp size={14} />
                              ) : (
                                <TrendingDown size={14} />
                              )}
                              {Math.abs(parseFloat(asset.change_percent_24h)).toFixed(2)}%
                            </div>
                          </div>
                        </motion.div>
                      ))}
                    </div>
                  </div>

                  {/* Funds */}
                  {trendingData.funds && trendingData.funds.length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-muted-foreground mb-3">
                        Popular Funds
                      </h4>
                      <div className="space-y-2">
                        {trendingData.funds.slice(0, 2).map((asset: TrendingAsset) => (
                          <motion.div
                            key={asset.symbol}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            className="flex items-center justify-between p-3 rounded-lg bg-cyber-dark/50 hover:bg-cyber-dark transition-colors"
                          >
                            <div>
                              <div className="font-semibold text-neon-lime">{asset.symbol}</div>
                              <div className="text-xs text-muted-foreground truncate max-w-[150px]">
                                {asset.name}
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="font-medium">
                                ${parseFloat(asset.current_price).toFixed(2)}
                              </div>
                              <div
                                className={`text-sm flex items-center gap-1 ${
                                  parseFloat(asset.change_percent_24h) >= 0
                                    ? 'text-neon-lime'
                                    : 'text-neon-magenta'
                                }`}
                              >
                                {parseFloat(asset.change_percent_24h) >= 0 ? (
                                  <TrendingUp size={14} />
                                ) : (
                                  <TrendingDown size={14} />
                                )}
                                {Math.abs(parseFloat(asset.change_percent_24h)).toFixed(2)}%
                              </div>
                            </div>
                          </motion.div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Market Summary */}
                  <div className="pt-4 border-t border-neon-cyan/10">
                    <div className="grid grid-cols-2 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold text-neon-lime">
                          {trendingData.market_summary.gainers}
                        </div>
                        <div className="text-xs text-muted-foreground">Gainers</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-neon-magenta">
                          {trendingData.market_summary.losers}
                        </div>
                        <div className="text-xs text-muted-foreground">Losers</div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-16 bg-cyber-dark/30 rounded-lg animate-pulse shimmer" />
                  ))}
                </div>
              )}
            </Card>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative z-10 container mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl font-bold mb-4">
            Everything You Need to
            <span className="text-neon-cyan"> Stay Ahead</span>
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Powerful features designed for serious investors
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="glass border-neon-cyan/20 p-6 h-full hover:border-neon-cyan/50 transition-all duration-300 group">
                  <div
                    className={`w-14 h-14 rounded-lg bg-${feature.color}/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}
                  >
                    <Icon className={`text-${feature.color}`} size={28} />
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground">{feature.description}</p>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 container mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
        >
          <Card className="glass border-neon-cyan/30 p-12 text-center relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-neon-cyan/10 via-neon-magenta/10 to-neon-lime/10" />
            <div className="relative z-10">
              <h2 className="text-4xl font-bold mb-4">
                Ready to Take Control of Your Investments?
              </h2>
              <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
                Join thousands of investors who never miss a market opportunity
              </p>
              <Button
                variant="neon"
                size="lg"
                className="gap-2"
                onClick={() => navigate('/register')}
              >
                <Sparkles size={20} />
                Get Started Free - No Credit Card Required
                <ArrowRight size={20} />
              </Button>
            </div>
          </Card>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-neon-cyan/20 glass">
        <div className="container mx-auto px-6 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between">
            <div className="flex items-center gap-3 mb-4 md:mb-0">
              <Eye className="text-neon-cyan" size={24} />
              <span className="text-lg font-semibold">MarketEye</span>
            </div>
            <p className="text-sm text-muted-foreground">
              © 2025 MarketEye. Built with open-source technologies. Not financial advice.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
