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
  BarChart3,
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
  { iconBox: 'bg-primary/12 text-primary ring-1 ring-primary/20' },
  { iconBox: 'bg-violet-500/12 text-violet-600 ring-1 ring-violet-500/20' },
  { iconBox: 'bg-success/12 text-success ring-1 ring-success/20' },
  { iconBox: 'bg-brass/15 text-brass ring-1 ring-brass/25' },
  { iconBox: 'bg-primary/12 text-primary ring-1 ring-primary/20' },
  { iconBox: 'bg-violet-500/12 text-violet-600 ring-1 ring-violet-500/20' },
];

const heroContainer = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.04 },
  },
};

const heroItem = {
  hidden: { opacity: 0, y: 16 },
  show: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 380, damping: 30 },
  },
};

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
      title: '24/7 market monitoring',
      description: 'Stocks, crypto, and funds — streamed continuously with institutional-grade freshness targets.',
    },
    {
      icon: Bell,
      title: 'Precision alerts',
      description: 'Route signals through SMS, voice, email, or push. Quiet hours and repeat rules included.',
    },
    {
      icon: TrendingUp,
      title: 'Portfolio clarity',
      description: 'Track positions with live marks and change context — fewer tabs, faster decisions.',
    },
    {
      icon: Shield,
      title: 'Security first',
      description: 'Encryption in transit and at rest, least-privilege access, and auditable alert history.',
    },
    {
      icon: Zap,
      title: 'Low-latency stack',
      description: 'Built for snappy search, charts, and alert evaluation when venues are moving.',
    },
    {
      icon: Target,
      title: 'Conditional logic',
      description: 'Price, percent, and custom triggers — compose rules that match how you actually trade.',
    },
  ];

  const rowDark =
    'flex items-center justify-between gap-3 p-3 rounded-lg bg-white/[0.04] hover:bg-white/[0.07] transition-colors border border-white/[0.08]';

  return (
    <div className="relative min-h-dvh bg-background">
      {/* —— Dark institutional shell: nav + hero —— */}
      <div className="relative overflow-hidden bg-ink cyber-grid-dark text-white">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/[0.07] via-transparent to-transparent" />
        <div className="pointer-events-none absolute -top-32 right-0 h-[28rem] w-[28rem] rounded-full bg-brass/10 blur-3xl" />
        <div className="pointer-events-none absolute bottom-0 left-1/4 h-64 w-64 rounded-full bg-primary/20 blur-3xl opacity-40" />

        <Navbar transparent appearance="dark" />

        <section className="relative z-10 container mx-auto px-6 pb-20 pt-10 md:pb-28 md:pt-14">
          <div className="grid items-center gap-14 lg:grid-cols-2 lg:gap-16">
            <motion.div variants={heroContainer} initial="hidden" animate="show" className="max-w-xl">
              <motion.div variants={heroItem}>
                <div className="mb-8 inline-flex items-center gap-3 rounded-full border border-white/10 bg-white/[0.06] px-4 py-2 backdrop-blur-sm">
                  <BarChart3 className="h-4 w-4 text-brass" aria-hidden />
                  <span className="text-xs font-semibold uppercase tracking-[0.2em] text-white/60">
                    Market intelligence
                  </span>
                  <span className="hidden h-3 w-px bg-white/20 sm:block" />
                  <span className="flex items-center gap-2 text-sm text-white/85">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success/70 opacity-60" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
                    </span>
                    Live feed
                  </span>
                </div>
              </motion.div>

              <motion.h1
                variants={heroItem}
                className="font-display text-4xl font-semibold leading-[1.05] tracking-tight text-balance sm:text-5xl md:text-[3.25rem]"
              >
                Clarity when{' '}
                <span className="bg-gradient-to-r from-white via-white to-white/75 bg-clip-text text-transparent">
                  markets move
                </span>
                <span className="text-brass">.</span>
              </motion.h1>

              <motion.p
                variants={heroItem}
                className="mt-6 text-lg leading-relaxed text-white/65 md:text-xl"
              >
                MarketEye is a control layer for your watchlists — monitoring, alerting, and execution-aware
                context without the noise of a retail trading toy.
              </motion.p>

              <motion.div variants={heroItem} className="mt-10 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Button
                  variant="dark-solid"
                  size="lg"
                  className="gap-2 shadow-glow"
                  onClick={() => navigate('/register')}
                >
                  <Sparkles size={18} />
                  Open workspace
                  <ArrowRight size={18} />
                </Button>
                <Button
                  variant="dark-ghost"
                  size="lg"
                  className="border border-white/15 bg-white/[0.04] hover:bg-white/[0.08]"
                  onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
                >
                  View capabilities
                </Button>
              </motion.div>

              <motion.p variants={heroItem} className="mt-4 text-sm text-white/45">
                No credit card required · Cancel anytime
              </motion.p>

              {stats && (
                <motion.div
                  variants={heroItem}
                  className="mt-10 grid max-w-lg grid-cols-3 gap-3 rounded-xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-md"
                >
                  <div>
                    <div className="font-display text-2xl font-semibold tabular-nums text-white sm:text-3xl">
                      {stats.total_users}
                    </div>
                    <div className="mt-1 text-[11px] font-medium uppercase tracking-wider text-white/50">
                      Seats
                    </div>
                  </div>
                  <div className="border-x border-white/10 px-2 text-center sm:text-left">
                    <div className="font-display text-2xl font-semibold tabular-nums text-brass sm:text-3xl">
                      {stats.alerts_triggered_today}
                    </div>
                    <div className="mt-1 text-[11px] font-medium uppercase tracking-wider text-white/50">
                      Alerts today
                    </div>
                  </div>
                  <div className="text-right sm:text-left">
                    <div className="font-display text-2xl font-semibold tabular-nums text-success sm:text-3xl">
                      {stats.uptime}
                    </div>
                    <div className="mt-1 text-[11px] font-medium uppercase tracking-wider text-white/50">
                      Uptime
                    </div>
                  </div>
                </motion.div>
              )}
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scale: 0.98, y: 12 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              transition={{ type: 'spring', stiffness: 320, damping: 28, delay: 0.1 }}
              className="relative"
            >
              <div className="absolute -inset-px rounded-2xl bg-gradient-to-br from-brass/25 via-primary/20 to-transparent opacity-80 blur-sm" />
              <Card className="relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.06] p-6 shadow-2xl shadow-black/40 backdrop-blur-xl md:p-8">
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-primary/[0.08] via-transparent to-brass/[0.05]" />
                <div className="relative mb-6 flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-white/45">
                      Snapshot
                    </p>
                    <h3 className="font-display text-lg font-semibold text-white">Cross-asset tape</h3>
                  </div>
                  <div className="flex items-center gap-2 rounded-full border border-success/30 bg-success/15 px-3 py-1">
                    <div className="h-2 w-2 animate-pulse rounded-full bg-success" />
                    <span className="text-xs font-medium text-success">Streaming</span>
                  </div>
                </div>

                {trendingData ? (
                  <div className="relative space-y-5">
                    <div>
                      <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-white/45">
                        Equities
                      </h4>
                      <div className="space-y-2">
                        {trendingData.stocks.slice(0, 3).map((asset: TrendingAsset, i: number) => (
                          <motion.div
                            key={asset.symbol}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.12 + i * 0.05 }}
                            className={rowDark}
                          >
                            <div className="min-w-0">
                              <div className="font-semibold tracking-tight text-white">{asset.symbol}</div>
                              <div className="truncate text-xs text-white/50">{asset.name}</div>
                            </div>
                            <div className="text-right">
                              <div className="font-tabular font-semibold text-white">
                                ${parseFloat(asset.current_price).toFixed(2)}
                              </div>
                              <div
                                className={cn(
                                  'flex items-center justify-end gap-1 text-sm font-medium',
                                  parseFloat(asset.change_percent_24h) >= 0 ? 'text-success' : 'text-red-400'
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
                      <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-white/45">
                        Digital assets
                      </h4>
                      <div className="space-y-2">
                        {trendingData.crypto.slice(0, 3).map((asset: TrendingAsset, i: number) => (
                          <motion.div
                            key={asset.symbol}
                            initial={{ opacity: 0, x: -8 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.22 + i * 0.05 }}
                            className={rowDark}
                          >
                            <div className="min-w-0">
                              <div className="font-semibold tracking-tight text-violet-300">{asset.symbol}</div>
                              <div className="truncate text-xs text-white/50">{asset.name}</div>
                            </div>
                            <div className="text-right">
                              <div className="font-tabular font-semibold text-white">
                                ${parseFloat(asset.current_price).toLocaleString()}
                              </div>
                              <div
                                className={cn(
                                  'flex items-center justify-end gap-1 text-sm font-medium',
                                  parseFloat(asset.change_percent_24h) >= 0 ? 'text-success' : 'text-red-400'
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
                        <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-white/45">
                          Funds
                        </h4>
                        <div className="space-y-2">
                          {trendingData.funds.slice(0, 2).map((asset: TrendingAsset, i: number) => (
                            <motion.div
                              key={asset.symbol}
                              initial={{ opacity: 0, x: -8 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: 0.35 + i * 0.05 }}
                              className={rowDark}
                            >
                              <div className="min-w-0">
                                <div className="font-semibold tracking-tight text-white">{asset.symbol}</div>
                                <div className="truncate text-xs text-white/50">{asset.name}</div>
                              </div>
                              <div className="text-right">
                                <div className="font-tabular font-semibold text-white">
                                  ${parseFloat(asset.current_price).toFixed(2)}
                                </div>
                                <div
                                  className={cn(
                                    'flex items-center justify-end gap-1 text-sm font-medium',
                                    parseFloat(asset.change_percent_24h) >= 0 ? 'text-success' : 'text-red-400'
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

                    <div className="grid grid-cols-2 gap-3 border-t border-white/10 pt-4">
                      <div className="rounded-lg bg-success/10 py-3 text-center">
                        <div className="font-display text-2xl font-semibold tabular-nums text-success">
                          {trendingData.market_summary.gainers}
                        </div>
                        <div className="text-[11px] font-medium uppercase tracking-wider text-white/45">
                          Gainers
                        </div>
                      </div>
                      <div className="rounded-lg bg-red-500/10 py-3 text-center">
                        <div className="font-display text-2xl font-semibold tabular-nums text-red-300">
                          {trendingData.market_summary.losers}
                        </div>
                        <div className="text-[11px] font-medium uppercase tracking-wider text-white/45">
                          Losers
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="relative space-y-3">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className="h-14 rounded-lg bg-gradient-to-r from-white/[0.06] via-white/[0.1] to-white/[0.06] animate-pulse"
                      />
                    ))}
                  </div>
                )}
              </Card>
            </motion.div>
          </div>
        </section>
      </div>

      {/* —— Light: product narrative —— */}
      <section
        id="features"
        className="relative border-t border-border bg-section-soft py-20 md:py-28 page-grain mesh-backdrop"
      >
        <div className="relative z-10 container mx-auto px-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mb-16 text-center md:mb-20"
          >
            <p className="mb-3 text-xs font-semibold uppercase tracking-[0.25em] text-primary">Platform</p>
            <h2 className="font-display mx-auto max-w-3xl text-3xl font-semibold tracking-tight text-balance text-foreground md:text-4xl">
              Built for operators who{' '}
              <span className="text-primary">cannot afford to miss the print</span>.
            </h2>
            <p className="mx-auto mt-4 max-w-2xl text-lg leading-relaxed text-muted-foreground">
              Every surface is tuned for legibility, speed, and trust — the same bar we set for production
              trading infrastructure.
            </p>
          </motion.div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3 md:gap-8">
            {features.map((feature, index) => {
              const Icon = feature.icon;
              const box = featureStyles[index % featureStyles.length];
              return (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, margin: '-40px' }}
                  transition={{ delay: index * 0.05, type: 'spring', stiffness: 400, damping: 30 }}
                >
                  <Card
                    className={cn(
                      'group relative h-full overflow-hidden border-border/70 bg-card p-6 shadow-lift transition-all duration-300 md:p-8',
                      'hover:-translate-y-1 hover:border-primary/25 hover:shadow-lift-lg'
                    )}
                  >
                    <div
                      className={cn(
                        'mb-5 flex h-12 w-12 items-center justify-center rounded-xl transition-transform duration-300 group-hover:scale-[1.03]',
                        box.iconBox
                      )}
                    >
                      <Icon size={22} strokeWidth={1.75} />
                    </div>
                    <h3 className="font-display mb-2 text-lg font-semibold tracking-tight text-foreground">
                      {feature.title}
                    </h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">{feature.description}</p>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* —— CTA band —— */}
      <section className="relative border-t border-white/5 bg-ink py-16 md:py-24">
        <div className="pointer-events-none absolute inset-0 bg-hero-dark opacity-90" />
        <div className="relative z-10 container mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="mx-auto max-w-2xl"
          >
            <h2 className="font-display text-3xl font-semibold tracking-tight text-white md:text-4xl">
              Deploy your watch layer in minutes
            </h2>
            <p className="mt-4 text-lg text-white/60">
              Connect your universe, define your rules, and let MarketEye keep the first screen of your day
              honest.
            </p>
            <div className="mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Button
                variant="dark-solid"
                size="lg"
                className="gap-2 min-w-[200px]"
                onClick={() => navigate('/register')}
              >
                Create account
                <ArrowRight size={18} />
              </Button>
              <Button
                variant="dark-ghost"
                size="lg"
                className="min-w-[200px] border border-white/15"
                onClick={() => navigate('/login')}
              >
                Sign in
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      <footer className="border-t border-white/10 bg-[hsl(222_47%_5%)] py-10 text-white/90">
        <div className="container mx-auto flex flex-col items-center justify-between gap-6 px-6 md:flex-row">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-ink-elevated ring-1 ring-brass/30">
              <Eye className="text-white" size={18} />
            </div>
            <div>
              <span className="font-display text-base font-semibold tracking-tight">MarketEye</span>
              <p className="text-xs text-white/50">Market data & alerts</p>
            </div>
          </div>
          <p className="text-center text-sm text-white/45 md:text-right">
            © {new Date().getFullYear()} MarketEye. Not investment advice. Past performance does not guarantee
            future results.
          </p>
        </div>
      </footer>
    </div>
  );
}
