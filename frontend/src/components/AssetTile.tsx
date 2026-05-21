import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { Asset } from '@/types';
import { Card } from '@/components/ui/card';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';

interface AssetTileProps {
  asset: Asset;
  onClick?: () => void;
}

export function AssetTile({ asset, onClick }: AssetTileProps) {
  const changePercent = asset.change_percent_24h ? parseFloat(asset.change_percent_24h) : 0;
  const isPositive = changePercent >= 0;
  const price = asset.current_price ? parseFloat(asset.current_price) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.01, y: -2 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className="cursor-pointer"
    >
      <Card
        className={cn(
          'relative overflow-hidden border-border/80 bg-card transition-shadow duration-300 hover:shadow-md',
          isPositive ? 'hover:border-success/30' : 'hover:border-destructive/25'
        )}
      >
        <div
          className={cn(
            'pointer-events-none absolute inset-0 opacity-0 transition-opacity duration-300 hover:opacity-100',
            isPositive ? 'bg-success/[0.06]' : 'bg-destructive/[0.06]'
          )}
        />

        <div className="relative p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-xl font-semibold text-foreground tracking-tight">{asset.symbol}</h3>
              <p className="text-sm text-muted-foreground truncate max-w-[200px]">{asset.name}</p>
            </div>
            <div
              className={cn(
                'flex items-center gap-1 rounded-full border border-border/80 px-2 py-1 text-xs font-medium',
                isPositive ? 'bg-success/10 text-foreground' : 'bg-destructive/10 text-destructive'
              )}
            >
              {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {asset.asset_type}
            </div>
          </div>

          <div className="mb-4">
            <div className="text-3xl font-semibold tracking-tight mb-1">{formatCurrency(price)}</div>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  'text-sm font-medium',
                  isPositive ? 'text-success' : 'text-destructive'
                )}
              >
                {formatPercent(changePercent)}
              </span>
              <span className="text-xs text-muted-foreground">24h</span>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-border/80 pt-4">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Activity size={14} className="text-primary" />
              <span>Live quote</span>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
