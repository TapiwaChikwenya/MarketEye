import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutDashboard,
  Users,
  Activity,
  BarChart3,
  RefreshCw,
  Shield,
  TrendingUp,
} from 'lucide-react';
import { toast } from 'sonner';
import { Navbar } from '@/components/Navbar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { adminService, type AdminOverview, type AdminUserRow, type AdminSystemHealth } from '@/services/admin';
import { cn } from '@/lib/utils';

function formatUptime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 48) return `${Math.floor(h / 24)}d ${h % 24}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function StatCard({
  label,
  value,
  sub,
  className,
}: {
  label: string;
  value: string | number;
  sub?: string;
  className?: string;
}) {
  return (
    <Card className={cn('border-border/80 bg-card', className)}>
      <CardHeader className="pb-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
      </CardHeader>
      <CardContent>
        <p className="font-display text-2xl font-semibold tabular-nums text-foreground">{value}</p>
        {sub && <p className="mt-1 text-xs text-muted-foreground">{sub}</p>}
      </CardContent>
    </Card>
  );
}

export function Admin() {
  const [tab, setTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [health, setHealth] = useState<AdminSystemHealth | null>(null);
  const [users, setUsers] = useState<AdminUserRow[]>([]);
  const [userTotal, setUserTotal] = useState(0);
  const [stocks, setStocks] = useState<{ symbol: string; track_count: number }[]>([]);
  const [uniqueSyms, setUniqueSyms] = useState(0);
  const [rowBusy, setRowBusy] = useState<Record<string, boolean>>({});

  const loadOverview = useCallback(async () => {
    const [o, h] = await Promise.all([adminService.getOverview(), adminService.getSystemHealth()]);
    setOverview(o);
    setHealth(h);
  }, []);

  const loadUsers = useCallback(async () => {
    const res = await adminService.getUsers(0, 100);
    setUsers(res.items);
    setUserTotal(res.total);
  }, []);

  const loadStocks = useCallback(async () => {
    const res = await adminService.getStocksUsage();
    setStocks(res.top_symbols);
    setUniqueSyms(res.unique_symbols_tracked);
  }, []);

  const refreshAll = useCallback(async () => {
    setRefreshing(true);
    try {
      await loadOverview();
      if (tab === 'users') await loadUsers();
      if (tab === 'stocks') await loadStocks();
      toast.success('Refreshed');
    } catch {
      toast.error('Failed to refresh');
    } finally {
      setRefreshing(false);
    }
  }, [loadOverview, loadUsers, loadStocks, tab]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        await loadOverview();
        if (!cancelled) await loadUsers();
        if (!cancelled) await loadStocks();
      } catch {
        if (!cancelled) toast.error('Failed to load admin data');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadOverview, loadUsers, loadStocks]);

  useEffect(() => {
    if (tab === 'users') loadUsers();
    if (tab === 'stocks') loadStocks();
  }, [tab, loadUsers, loadStocks]);

  const patchUser = async (u: AdminUserRow, field: 'is_active' | 'is_superuser', value: boolean) => {
    const key = `${u.id}-${field}`;
    setRowBusy((b) => ({ ...b, [key]: true }));
    try {
      const updated = await adminService.patchUser(u.id, { [field]: value });
      setUsers((list) => list.map((x) => (x.id === updated.id ? updated : x)));
      toast.success('User updated');
    } catch (e: unknown) {
      const msg =
        e && typeof e === 'object' && 'response' in e
          ? (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      toast.error(typeof msg === 'string' ? msg : 'Update failed');
    } finally {
      setRowBusy((b) => ({ ...b, [key]: false }));
    }
  };

  return (
    <div className="min-h-dvh bg-background cyber-grid-bg">
      <Navbar />

      <div className="container mx-auto max-w-6xl px-6 py-8">
        <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2 text-brass">
              <Shield size={18} />
              <span className="text-xs font-semibold uppercase tracking-widest">Admin</span>
            </div>
            <h1 className="font-display text-3xl font-semibold tracking-tight text-foreground">Operations</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Users, usage, cache, and system health for MarketEye.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" asChild>
              <Link to="/dashboard">
                <LayoutDashboard size={16} className="mr-2" />
                Dashboard
              </Link>
            </Button>
            <Button variant="default" size="sm" onClick={refreshAll} disabled={refreshing || loading}>
              <RefreshCw size={16} className={cn('mr-2', refreshing && 'animate-spin')} />
              Refresh
            </Button>
          </div>
        </motion.div>

        {loading && !overview ? (
          <div className="rounded-xl border border-border/80 bg-card p-12 text-center text-muted-foreground">
            Loading…
          </div>
        ) : (
          <Tabs value={tab} onValueChange={setTab} className="space-y-6">
            <TabsList className="grid w-full max-w-xl grid-cols-4">
              <TabsTrigger value="overview" className="gap-1.5">
                <Activity size={14} />
                Overview
              </TabsTrigger>
              <TabsTrigger value="users" className="gap-1.5">
                <Users size={14} />
                Users
              </TabsTrigger>
              <TabsTrigger value="system" className="gap-1.5">
                <BarChart3 size={14} />
                System
              </TabsTrigger>
              <TabsTrigger value="stocks" className="gap-1.5">
                <TrendingUp size={14} />
                Stocks
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-6">
              {overview && (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <StatCard label="Total users" value={overview.users_total} />
                  <StatCard label="Active users" value={overview.users_active} />
                  <StatCard label="New (7d)" value={overview.users_new_7d} sub={`${overview.users_new_24h} in 24h`} />
                  <StatCard label="Active alerts" value={overview.alerts_active} sub={`${overview.alerts_total} total`} />
                  <StatCard label="Tracked rows" value={overview.tracked_assets_rows} sub={`${overview.tracked_unique_symbols} unique symbols`} />
                  <StatCard label="Watchlists" value={overview.watchlists_total} />
                  <StatCard label="Notifications (24h)" value={overview.notification_logs_24h} />
                  <StatCard
                    label="Trending cache"
                    value={`${overview.trending_cache_hits} / ${overview.trending_cache_misses}`}
                    sub="hits / misses"
                  />
                </div>
              )}
            </TabsContent>

            <TabsContent value="users" className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Showing {users.length} of {userTotal} users. Toggle access flags — last superuser cannot be demoted.
              </p>
              <div className="overflow-x-auto rounded-xl border border-border/80 bg-card">
                <table className="w-full min-w-[640px] text-sm">
                  <thead>
                    <tr className="border-b border-border/80 text-left text-muted-foreground">
                      <th className="p-3 font-medium">Email</th>
                      <th className="p-3 font-medium">Name</th>
                      <th className="p-3 font-medium">Created</th>
                      <th className="p-3 font-medium">Active</th>
                      <th className="p-3 font-medium">Admin</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id} className="border-b border-border/40 last:border-0">
                        <td className="p-3 font-mono text-xs">{u.email}</td>
                        <td className="p-3">{u.name || '—'}</td>
                        <td className="p-3 text-xs text-muted-foreground">
                          {u.created_at ? new Date(u.created_at).toLocaleString() : '—'}
                        </td>
                        <td className="p-3">
                          <Switch
                            checked={u.is_active}
                            disabled={!!rowBusy[`${u.id}-is_active`]}
                            onCheckedChange={(v) => patchUser(u, 'is_active', v)}
                          />
                        </td>
                        <td className="p-3">
                          <Switch
                            checked={u.is_superuser}
                            disabled={!!rowBusy[`${u.id}-is_superuser`]}
                            onCheckedChange={(v) => patchUser(u, 'is_superuser', v)}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </TabsContent>

            <TabsContent value="system" className="space-y-6">
              {health && (
                <>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <StatCard
                      label="API uptime"
                      value={formatUptime(health.uptime_seconds)}
                      sub={`Version ${health.api_version}`}
                    />
                    <StatCard
                      label="Database"
                      value={health.database_ok ? 'OK' : 'Error'}
                      sub={
                        health.database_latency_ms != null
                          ? `${health.database_latency_ms.toFixed(1)} ms`
                          : undefined
                      }
                    />
                    <StatCard
                      label="Redis"
                      value={health.redis_ok ? 'OK' : 'Down'}
                      sub={
                        health.redis_latency_ms != null
                          ? `${health.redis_latency_ms.toFixed(1)} ms`
                          : health.redis_error || undefined
                      }
                    />
                  </div>
                  <Card className="border-border/80 bg-card">
                    <CardHeader>
                      <CardTitle className="font-display text-lg">Configured TTLs & intervals</CardTitle>
                      <p className="text-sm text-muted-foreground">
                        Seconds unless noted. Used for cache freshness, alerts, and tokens.
                      </p>
                    </CardHeader>
                    <CardContent>
                      <ul className="grid gap-2 sm:grid-cols-2">
                        {Object.entries(health.ttl_seconds).map(([k, v]) => (
                          <li
                            key={k}
                            className="flex justify-between rounded-lg border border-border/50 bg-muted/30 px-3 py-2 font-mono text-xs"
                          >
                            <span className="text-muted-foreground">{k}</span>
                            <span>{v}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>
                </>
              )}
            </TabsContent>

            <TabsContent value="stocks" className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Unique symbols tracked across all users: <strong>{uniqueSyms}</strong>
              </p>
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {stocks.map((s) => (
                  <Card key={s.symbol} className="border-border/80 bg-card">
                    <CardContent className="flex items-center justify-between p-4">
                      <span className="font-semibold">{s.symbol}</span>
                      <span className="text-sm text-muted-foreground">{s.track_count} tracks</span>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}
