import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Plus, Search, TrendingUp, Wallet, Bell, Settings } from 'lucide-react';
import { AssetTile } from '@/components/AssetTile';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Asset } from '@/types';

export function Dashboard() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  // Mock data for demonstration
  useEffect(() => {
    const mockAssets: Asset[] = [
      {
        id: '1',
        symbol: 'BTC',
        name: 'Bitcoin',
        asset_type: 'CRYPTO',
        exchange: 'Binance',
        currency: 'USD',
        current_price: '65432.10',
        change_percent_24h: '2.45',
        created_at: new Date().toISOString(),
      },
      {
        id: '2',
        symbol: 'AAPL',
        name: 'Apple Inc.',
        asset_type: 'STOCK',
        exchange: 'NASDAQ',
        currency: 'USD',
        current_price: '178.23',
        change_percent_24h: '-1.23',
        created_at: new Date().toISOString(),
      },
      {
        id: '3',
        symbol: 'ETH',
        name: 'Ethereum',
        asset_type: 'CRYPTO',
        exchange: 'Binance',
        currency: 'USD',
        current_price: '3421.56',
        change_percent_24h: '3.12',
        created_at: new Date().toISOString(),
      },
      {
        id: '4',
        symbol: 'TSLA',
        name: 'Tesla, Inc.',
        asset_type: 'STOCK',
        exchange: 'NASDAQ',
        currency: 'USD',
        current_price: '242.84',
        change_percent_24h: '-2.15',
        created_at: new Date().toISOString(),
      },
    ];
    setAssets(mockAssets);
  }, []);

  return (
    <div className="min-h-screen bg-cyber-darker cyber-grid-bg">
      {/* Header */}
      <motion.header
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="sticky top-0 z-50 glass border-b border-neon-cyan/20"
      >
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
                MarketEye
              </h1>
              <div className="hidden md:flex items-center gap-2">
                <div className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse" />
                <span className="text-sm text-neon-cyan">Live</span>
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon">
                <Bell size={20} />
              </Button>
              <Button variant="ghost" size="icon">
                <Wallet size={20} />
              </Button>
              <Button variant="ghost" size="icon">
                <Settings size={20} />
              </Button>
            </div>
          </div>
        </div>
      </motion.header>

      <div className="container mx-auto px-6 py-8">
        {/* Stats Row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
        >
          <Card className="glass border-neon-cyan/30">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Wallet className="text-neon-cyan" size={20} />
                Portfolio Value
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-neon-cyan">$125,432.10</div>
              <div className="text-sm text-green-400 flex items-center gap-1 mt-2">
                <TrendingUp size={14} />
                <span>+5.23% Today</span>
              </div>
            </CardContent>
          </Card>

          <Card className="glass border-neon-magenta/30">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Bell className="text-neon-magenta" size={20} />
                Active Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-neon-magenta">12</div>
              <div className="text-sm text-muted-foreground mt-2">
                3 triggered today
              </div>
            </CardContent>
          </Card>

          <Card className="glass border-neon-lime/30">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="text-neon-lime" size={20} />
                Watchlist Assets
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-neon-lime">24</div>
              <div className="text-sm text-muted-foreground mt-2">
                Across 3 watchlists
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Search and Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col md:flex-row gap-4 mb-8"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
            <Input
              placeholder="Search assets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button variant="neon" className="gap-2">
            <Plus size={20} />
            Add Asset
          </Button>
        </motion.div>

        {/* Assets Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <h2 className="text-2xl font-bold mb-6 text-neon-cyan">
            Your Watchlist
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {assets.map((asset, index) => (
              <motion.div
                key={asset.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 * index }}
              >
                <AssetTile
                  asset={asset}
                  onClick={() => console.log('Asset clicked:', asset.symbol)}
                />
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Add some cyberpunk decorative elements */}
        <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden -z-10">
          <div className="absolute top-20 left-10 w-64 h-64 bg-neon-cyan/5 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-neon-magenta/5 rounded-full blur-3xl" />
        </div>
      </div>
    </div>
  );
}
