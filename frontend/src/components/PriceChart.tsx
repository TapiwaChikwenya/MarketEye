import { useState, useEffect, useCallback } from 'react';
import {
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { TrendingUp, TrendingDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { API_URL } from '@/lib/api-config';

interface PriceDataPoint {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface PriceChartProps {
  symbol: string;
  name?: string;
  assetType: 'STOCK' | 'CRYPTO' | 'ETF' | 'MUTUAL_FUND';
  currentPrice?: string;
  changePercent?: string;
  compact?: boolean;
}

const TIME_PERIODS = [
  { label: '1D', value: '1d', interval: '5m' },
  { label: '1W', value: '5d', interval: '30m' },
  { label: '1M', value: '1mo', interval: '1d' },
  { label: '3M', value: '3mo', interval: '1d' },
  { label: '1Y', value: '1y', interval: '1wk' },
  { label: 'ALL', value: 'max', interval: '1mo' },
];

export function PriceChart({
  symbol,
  name,
  assetType,
  currentPrice,
  changePercent,
  compact = false,
}: PriceChartProps) {
  const [data, setData] = useState<PriceDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState(TIME_PERIODS[2]); // Default 1M

  const fetchHistoricalData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_URL}/api/v1/public/history?symbol=${symbol}&asset_type=${assetType}&period=${selectedPeriod.value}&interval=${selectedPeriod.interval}`
      );
      const result = await response.json();

      if (result.data && result.data.length > 0) {
        setData(result.data);
      } else {
        setData([]);
      }
    } catch (err) {
      console.error('Error fetching chart data:', err);
      setError('Failed to load chart data');
      setData([]);
    } finally {
      setLoading(false);
    }
  }, [symbol, assetType, selectedPeriod]);

  useEffect(() => {
    void fetchHistoricalData();
  }, [fetchHistoricalData]);

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    if (selectedPeriod.value === '1d') {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const formatPrice = (price: number) => {
    if (price >= 1000) {
      return `$${price.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
    }
    return `$${price.toFixed(2)}`;
  };

  const priceChange = parseFloat(changePercent || '0');
  const isPositive = priceChange >= 0;
  const chartColor = isPositive ? '#0071e3' : '#ff3b30';

  // Calculate chart stats
  const minPrice = data.length > 0 ? Math.min(...data.map(d => d.close)) : 0;
  const maxPrice = data.length > 0 ? Math.max(...data.map(d => d.close)) : 0;
  const startPrice = data.length > 0 ? data[0].close : 0;
  const endPrice = data.length > 0 ? data[data.length - 1].close : 0;
  const periodChange = startPrice > 0 ? ((endPrice - startPrice) / startPrice) * 100 : 0;

  if (compact) {
    return (
      <div className="h-16 w-full">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-xs text-muted-foreground">
            No chart data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`gradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area
                type="monotone"
                dataKey="close"
                stroke={chartColor}
                strokeWidth={2}
                fill={`url(#gradient-${symbol})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    );
  }

  return (
    <Card className="border-black/[0.06] bg-white p-6 shadow-sm">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h3 className="text-2xl font-semibold text-foreground">{symbol}</h3>
            <span className={cn(
              "px-2 py-0.5 rounded-md text-xs font-medium",
              assetType === 'CRYPTO' ? 'bg-violet-500/15 text-violet-700' : 'bg-[#0071e3]/10 text-[#0071e3]'
            )}>
              {assetType}
            </span>
          </div>
          {name && <p className="text-sm text-muted-foreground mt-1">{name}</p>}
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold">
            {currentPrice ? `$${parseFloat(currentPrice).toLocaleString()}` : '—'}
          </div>
          <div className={cn(
            "flex items-center justify-end gap-1 text-sm",
            isPositive ? 'text-[#34c759]' : 'text-[#ff3b30]'
          )}>
            {isPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
            {isPositive ? '+' : ''}{priceChange.toFixed(2)}% (24h)
          </div>
        </div>
      </div>

      {/* Time period selector */}
      <div className="flex gap-2 mb-4">
        {TIME_PERIODS.map((period) => (
          <Button
            key={period.value}
            variant={selectedPeriod.value === period.value ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setSelectedPeriod(period)}
            className="px-3"
          >
            {period.label}
          </Button>
        ))}
      </div>

      {/* Chart */}
      <div className="h-64 w-full">
        {loading ? (
          <div className="h-full flex items-center justify-center">
            <Loader2 className="w-8 h-8 animate-spin text-[#0071e3]" />
          </div>
        ) : error ? (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            {error}
          </div>
        ) : data.length === 0 ? (
          <div className="h-full flex items-center justify-center text-muted-foreground">
            No chart data available
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data}>
              <defs>
                <linearGradient id={`chartGradient-${symbol}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={chartColor} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={chartColor} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis
                dataKey="timestamp"
                tickFormatter={formatDate}
                stroke="#ccc"
                tick={{ fill: '#86868b', fontSize: 12 }}
                axisLine={{ stroke: '#d2d2d7' }}
                tickLine={{ stroke: '#d2d2d7' }}
              />
              <YAxis
                domain={['auto', 'auto']}
                tickFormatter={(value) => formatPrice(value)}
                stroke="#ccc"
                tick={{ fill: '#86868b', fontSize: 12 }}
                axisLine={{ stroke: '#d2d2d7' }}
                tickLine={{ stroke: '#d2d2d7' }}
                width={80}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#ffffff',
                  border: '1px solid rgba(0, 0, 0, 0.08)',
                  borderRadius: '12px',
                  boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
                }}
                labelFormatter={(label) => new Date(label).toLocaleString()}
                formatter={(value: number) => [formatPrice(value), 'Price']}
              />
              <Area
                type="monotone"
                dataKey="close"
                stroke={chartColor}
                strokeWidth={2}
                fill={`url(#chartGradient-${symbol})`}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mt-4 pt-4 border-t border-black/[0.06]">
        <div>
          <div className="text-xs text-muted-foreground">Period Change</div>
          <div className={cn(
            "font-semibold",
            periodChange >= 0 ? 'text-[#34c759]' : 'text-[#ff3b30]'
          )}>
            {periodChange >= 0 ? '+' : ''}{periodChange.toFixed(2)}%
          </div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">High</div>
          <div className="font-semibold text-[#34c759]">{formatPrice(maxPrice)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">Low</div>
          <div className="font-semibold text-muted-foreground">{formatPrice(minPrice)}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">Volume</div>
          <div className="font-semibold">
            {data.length > 0 
              ? (data[data.length - 1].volume / 1000000).toFixed(2) + 'M'
              : '-'
            }
          </div>
        </div>
      </div>
    </Card>
  );
}

