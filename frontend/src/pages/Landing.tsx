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
import { cn } from '@/lib/utils';

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

const featureStyles = [
  { iconBox: 'bg-[#0071e3]/10 text-[#0071e3]' },
  { iconBox: 'bg-violet-500/10 text-violet-600' },
  { iconBox: 'bg-[#34c759]/10 text-[#34c759]' },
  { iconBox: 'bg-[#0071e3]/10 text-[#0071e3]' },
  { iconBox: 'bg-violet-500/10 text-violet-600' },
  { iconBox: 'bg-[#34c759]/10 text-[#34c759]' },
];

export function Landing() {
  const navigate = useNavigate();
  const [trendingData, setTrendingData] = useState<PublicTrendingPayload | null>(null);
  const [stats, setStats] = useState<PublicMarketStats | null>(null);

  useEffect(() => {
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
    const interval = setInterval(fetchData, 60000);

    return () => clearInterval(interval);
  }, []);

  const features = [
    {
      icon: Eye,
      title: '24/7 Market Monitoring',
      description: 'Track stocks, crypto, and ETFs around the clock with real-time updates',
    },
    {
      icon: Bell,
      title: 'Smart Alerts',
      description: 'Get instant notifications via SMS, call, or email when conditions are met',
    },
    {
      icon: TrendingUp,
      title: 'Portfolio Tracking',
      description: 'Monitor your investments with real-time P&L calculations',
    },
    {
      icon: Shield,
      title: 'Secure & Private',
      description: 'Bank-level encryption and security for your data',
    },
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: 'Sub-100ms response times for real-time market data',
    },
    {
      icon: Target,
      title: 'Precision Alerts',
      description: 'Set custom conditions with price, percentage, and volume triggers',
    },
  ];

  const rowClass =
    'flex items-center justify-between p-3 rounded-xl bg-muted/50 hover:bg-muted/80 transition-colors border border-black/[0.04]';

  return (
    <div className="min-h-dvh bg-background cyber-grid-bg overflow-hidden">
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{
            scale: [1, 1.08, 1],
            opacity: [0.35, 0.5, 0.35],
          }}
          transition={{ duration: 12, repeat: Infinity }}
          className="absolute -top-20 -left-20 w-[28rem] h-[28rem] bg-[#0071e3]/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1, 1.1, 1],
            opacity: [0.25, 0.4, 0.25],
          }}
          transition={{ duration: 14, repeat: Infinity, delay: 1 }}
          className="absolute bottom-0 right-0 w-[32rem] h-[32rem] bg-violet-400/15 rounded-full blur-3xl"
        />
      </div>

      <Navbar transparent />

      <section className="relative z-10 container mx-auto px-6 py-16 md:py-24">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-black/[0.08] bg-white/80 mb-8 shadow-sm">
              <div className="w-2 h-2 rounded-full bg-[#34c759] animate-pulse" />
              <span className="text-sm text-muted-foreground">Live market data · Free to start</span>
            </div>

            <h1 className="text-4xl sm:text-5xl md:text-6xl font-semibold tracking-tight text-foreground mb-6 leading-[1.07]">
              Never miss a{' '}
              <span className="text-[#0071e3]">market move</span>
            </h1>

            <p className="text-lg md:text-xl text-muted-foreground mb-10 max-w-xl leading-relaxed">
              24/7 monitoring with intelligent alerts. Track stocks, crypto, and ETFs with notifications
              via SMS, voice, and email.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 mb-12">
              <Button variant="default" size="lg" className="gap-2" onClick={() => navigate('/register')}>
                <Sparkles size={20} />
                Start monitoring
                <ArrowRight size={20} />
              </Button>
              <Button
                variant="outline"
                size="lg"
                onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
              >
                See how it works
              </Button>
            </div>

            {stats && (
              <div className="grid grid-cols-3 gap-6 max-w-md">
                <div>
                  <div className="text-3xl font-semibold tracking-tight tabular-nums">{stats.total_users}</div>
                  <div className="text-sm text-muted-foreground">Active users</div>
                </div>
                <div>
                  <div className="text-3xl font-semibold tracking-tight tabular-nums text-[#ff9500]">
                    {stats.alerts_triggered_today}
                  </div>
                  <div className="text-sm text-muted-foreground">Alerts today</div>
                </div>
                <div>
                  <div className="text-3xl font-semibold tracking-tight tabular-nums text-[#34c759]">
                    {stats.uptime}
                  </div>
                  <div className="text-sm text-muted-foreground">Uptime</div>
                </div>
              </div>
            )}
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <Card className="p-6 md:p-8 border-black/[0.06] shadow-lg bg-white/90 backdrop-blur-sm">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-foreground">Live markets</h3>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-[#34c759] rounded-full animate-pulse" />
                  <span className="text-sm text-muted-foreground">Updating</span>
                </div>
              </div>

              {trendingData ? (
                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
                      Top stocks
                    </h4>
                    <div className="space-y-2">
                      {trendingData.stocks.slice(0, 3).map((asset: TrendingAsset) => (
                        <motion.div
                          key={asset.symbol}
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          className={rowClass}
                        >
                          <div>
                            <div className="font-semibold text-foreground">{asset.symbol}</div>
                            <div className="text-xs text-muted-foreground truncate max-w-[150px]">{asset.name}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium tabular-nums">${parseFloat(asset.current_price).toFixed(2)}</div>
                            <div
                              className={cn(
                                'text-sm flex items-center justify-end gap-1',
                                parseFloat(asset.change_percent_24h) >= 0 ? 'text-[#34c759]' : 'text-[#ff3b30]'
                              )}
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

                  <div>
                    <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
                      Top crypto
                    </h4>
                    <div className="space-y-2">
                      {trendingData.crypto.slice(0, 3).map((asset: TrendingAsset) => (
                        <motion.div
                          key={asset.symbol}
                          initial={{ opacity: 0, x: -12 }}
                          animate={{ opacity: 1, x: 0 }}
                          className={rowClass}
                        >
                          <div>
                            <div className="font-semibold text-violet-700">{asset.symbol}</div>
                            <div className="text-xs text-muted-foreground truncate max-w-[150px]">{asset.name}</div>
                          </div>
                          <div className="text-right">
                            <div className="font-medium tabular-nums">${parseFloat(asset.current_price).toLocaleString()}</div>
                            <div
                              className={cn(
                                'text-sm flex items-center justify-end gap-1',
                                parseFloat(asset.change_percent_24h) >= 0 ? 'text-[#34c759]' : 'text-[#ff3b30]'
                              )}
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

                  {trendingData.funds && trendingData.funds.length > 0 && (
                    <div>
                      <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
                        Popular funds
                      </h4>
                      <div className="space-y-2">
                        {trendingData.funds.slice(0, 2).map((asset: TrendingAsset) => (
                          <motion.div
                            key={asset.symbol}
                            initial={{ opacity: 0, x: -12 }}
                            animate={{ opacity: 1, x: 0 }}
                            className={rowClass}
                          >
                            <div>
                              <div className="font-semibold text-foreground">{asset.symbol}</div>
                              <div className="text-xs text-muted-foreground truncate max-w-[150px]">{asset.name}</div>
                            </div>
                            <div className="text-right">
                              <div className="font-medium tabular-nums">${parseFloat(asset.current_price).toFixed(2)}</div>
                              <div
                                className={cn(
                                  'text-sm flex items-center justify-end gap-1',
                                  parseFloat(asset.change_percent_24h) >= 0 ? 'text-[#34c759]' : 'text-[#ff3b30]'
                                )}
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

                  <div className="pt-4 border-t border-black/[0.06]">
                    <div className="grid grid-cols-2 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-semibold text-[#34c759] tabular-nums">
                          {trendingData.market_summary.gainers}
                        </div>
                        <div className="text-xs text-muted-foreground">Gainers</div>
                      </div>
                      <div>
                        <div className="text-2xl font-semibold text-[#ff3b30] tabular-nums">
                          {trendingData.market_summary.losers}
                        </div>
                        <div className="text-xs text-muted-foreground">Losers</div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-14 bg-muted/60 rounded-xl animate-pulse" />
                  ))}
                </div>
              )}
            </Card>
          </motion.div>
        </div>
      </section>

      <section id="features" className="relative z-10 container mx-auto px-6 py-20 md:py-28">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center mb-16 md:mb-20"
        >
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-4">
            Everything you need to <span className="text-[#0071e3]">stay ahead</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Clear tools for investors who want signal, not noise.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => {
            const Icon = feature.icon;
            const box = featureStyles[index % featureStyles.length];
            return (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.05 }}
              >
                <Card className="p-6 md:p-8 h-full border-black/[0.06] bg-white hover:shadow-md transition-shadow duration-300">
                  <div
                    className={cn(
                      'w-12 h-12 rounded-2xl flex items-center justify-center mb-5',
                      box.iconBox
                    )}
                  >
                    <Icon size={24} strokeWidth={1.75} />
                  </div>
                  <h3 className="text-lg font-semibold mb-2 tracking-tight">{feature.title}</h3>
                  <p className="text-muted-foreground text-sm leading-relaxed">{feature.description}</p>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </section>

      <section className="relative z-10 container mx-auto px-6 pb-24">
        <motion.div initial={{ opacity: 0, y: 12 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}>
          <Card className="p-10 md:p-14 text-center border-black/[0.06] bg-[#f5f5f7] overflow-hidden relative">
            <div className="absolute inset-0 bg-gradient-to-b from-white/0 via-white/40 to-white/80 pointer-events-none" />
            <div className="relative z-10 max-w-2xl mx-auto">
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-4">
                Ready to take control?
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                Create a free account and start monitoring in minutes.
              </p>
              <Button variant="default" size="lg" className="gap-2" onClick={() => navigate('/register')}>
                <Sparkles size={20} />
                Get started — no card required
                <ArrowRight size={20} />
              </Button>
            </div>
          </Card>
        </motion.div>
      </section>

      <footer className="relative z-10 border-t border-black/[0.06] bg-white/80 backdrop-blur-xl">
        <div className="container mx-auto px-6 py-10">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-xl bg-[#0071e3] flex items-center justify-center">
                <Eye className="text-white" size={18} />
              </div>
              <span className="text-base font-semibold tracking-tight">MarketEye</span>
            </div>
            <p className="text-sm text-muted-foreground text-center md:text-right">
              © {new Date().getFullYear()} MarketEye. Not financial advice.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
