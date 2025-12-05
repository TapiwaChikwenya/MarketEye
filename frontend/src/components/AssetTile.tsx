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
      whileHover={{ scale: 1.02, y: -5 }}
      transition={{ duration: 0.2 }}
      onClick={onClick}
      className="cursor-pointer"
    >
      <Card
        className={cn(
          "relative overflow-hidden transition-all duration-300 hover:border-neon-cyan/50",
          "glass",
          isPositive ? "hover:shadow-lg hover:shadow-neon-cyan/20" : "hover:shadow-lg hover:shadow-neon-magenta/20"
        )}
      >
        {/* Animated background glow */}
        <div className={cn(
          "absolute inset-0 opacity-0 transition-opacity duration-300 hover:opacity-10",
          isPositive ? "bg-neon-cyan" : "bg-neon-magenta"
        )} />

        <div className="relative p-6">
          {/* Header */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <h3 className="text-xl font-bold text-neon-cyan neon-text">
                {asset.symbol}
              </h3>
              <p className="text-sm text-muted-foreground truncate max-w-[200px]">
                {asset.name}
              </p>
            </div>
            <div className={cn(
              "flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium",
              isPositive
                ? "bg-neon-cyan/20 text-neon-cyan"
                : "bg-neon-magenta/20 text-neon-magenta"
            )}>
              {isPositive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              {asset.asset_type}
            </div>
          </div>

          {/* Price */}
          <div className="mb-4">
            <div className="text-3xl font-bold mb-1">
              {formatCurrency(price)}
            </div>
            <div className="flex items-center gap-2">
              <span className={cn(
                "text-sm font-medium",
                isPositive ? "text-neon-cyan" : "text-neon-magenta"
              )}>
                {formatPercent(changePercent)}
              </span>
              <span className="text-xs text-muted-foreground">24h</span>
            </div>
          </div>

          {/* Mini sparkline visualization */}
          <div className="flex items-center justify-between pt-4 border-t border-neon-cyan/10">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Activity size={14} className="text-neon-cyan" />
              <span>{asset.exchange || 'Market'}</span>
            </div>
            {asset.last_updated && (
              <div className="text-xs text-muted-foreground">
                {new Date(asset.last_updated).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>

        {/* Animated border gradient */}
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-neon-cyan to-transparent opacity-50" />
      </Card>
    </motion.div>
  );
}
