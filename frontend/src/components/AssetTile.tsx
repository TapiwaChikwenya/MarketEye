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
          'relative overflow-hidden transition-shadow duration-300 border-black/[0.06] hover:shadow-md',
          'bg-white',
          isPositive ? 'hover:border-[#34c759]/30' : 'hover:border-[#ff3b30]/25'
        )}
      >
        <div
          className={cn(
            'absolute inset-0 opacity-0 transition-opacity duration-300 hover:opacity-100 pointer-events-none',
            isPositive ? 'bg-[#34c759]/[0.06]' : 'bg-[#ff3b30]/[0.06]'
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
                'flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border border-black/[0.08]',
                isPositive ? 'bg-[#34c759]/10 text-[#1d1d1f]' : 'bg-[#ff3b30]/10 text-[#ff3b30]'
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
                  isPositive ? 'text-[#34c759]' : 'text-[#ff3b30]'
                )}
              >
                {formatPercent(changePercent)}
              </span>
              <span className="text-xs text-muted-foreground">24h</span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4 border-t border-black/[0.06]">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Activity size={14} className="text-[#0071e3]" />
              <span>Live quote</span>
            </div>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
