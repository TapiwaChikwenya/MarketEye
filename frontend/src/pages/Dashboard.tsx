import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, Search, TrendingUp, TrendingDown, Wallet, Bell, Settings, RefreshCw, LogOut, 
  X, Star, Trash2, AlertTriangle, User as UserIcon, Clock, Home,
  ChevronDown, ChevronUp, LineChart, Eye, EyeOff, Building2, Coins, PiggyBank, BellRing, CheckCheck
} from 'lucide-react';
import { toast } from 'sonner';
import { AssetTile } from '@/components/AssetTile';
import { PriceChart } from '@/components/PriceChart';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Asset, User, Watchlist, AlertRule } from '@/types';
import { api } from '@/lib/axios';
import { authService } from '@/services/auth';
import { userService, CONTACT_METHODS, TIME_ZONES, UpdateUserData } from '@/services/user';
import { watchlistsService, WatchlistWithAssetsDetail } from '@/services/watchlists';
import { alertsService, CONDITION_TYPE_LABELS, ConditionType, CreateAlertData } from '@/services/alerts';
import { trackedService, TrackedAsset, TrackAssetData } from '@/services/tracked';
import { notificationsService, Notification as AppNotification } from '@/services/notifications';
import { useNotifications, useNotificationState } from '@/hooks/useNotifications';
import { useAlertStream, playAlertSound, type AlertEvent } from '@/hooks/useAlertStream';
import { Link, useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';

interface TrendingData {
  stocks: Asset[];
  crypto: Asset[];
  funds: Asset[];
  market_summary: {
    total_assets: number;
    avg_change_24h: number;
    gainers: number;
    losers: number;
  };
}

interface CatalogData {
  stocks: Asset[];
  crypto: Asset[];
  funds: Asset[];
  etfs: Asset[];
}

interface SearchResult {
  symbol: string;
  name: string;
  asset_type: string;
  exchange?: string;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function Dashboard() {
  const navigate = useNavigate();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [marketSummary, setMarketSummary] = useState({
    total_assets: 0,
    avg_change_24h: 0,
    gainers: 0,
    losers: 0,
  });

  // User and account state
  const [user, setUser] = useState<User | null>(null);
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [alerts, setAlerts] = useState<AlertRule[]>([]);
  
  // Tracked assets (from database)
  const [trackedAssets, setTrackedAssets] = useState<TrackedAsset[]>([]);
  const [showTrackedSection, setShowTrackedSection] = useState(true);
  const [selectedChartAsset, setSelectedChartAsset] = useState<TrackedAsset | null>(null);

  // Search state
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [liveSearchResults, setLiveSearchResults] = useState<SearchResult[]>([]);

  // Modal states
  const [showSettings, setShowSettings] = useState(false);
  const [showAlerts, setShowAlerts] = useState(false);
  const [showAddAsset, setShowAddAsset] = useState(false);
  const [showCreateAlert, setShowCreateAlert] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [activeTab, setActiveTab] = useState<'trending' | 'tracked'>('trending');
  const [assetFilter, setAssetFilter] = useState<'all' | 'stocks' | 'crypto' | 'funds'>('all');

  // Watchlist management
  const [selectedWatchlist, setSelectedWatchlist] = useState<WatchlistWithAssetsDetail | null>(null);
  const [showAddToWatchlist, setShowAddToWatchlist] = useState(false);

  // Notifications
  const { requestPermission, showPriceAlert, isEnabled: pushEnabled, isSupported: pushSupported } = useNotifications();
  const { notifications: appNotifications, unreadCount, addNotification, markAsRead, markAllAsRead, clearNotifications } = useNotificationState();

  // SSE alert stream -- plays sound + shows browser notification for every triggered alert
  useAlertStream({
    onAlert: (event: AlertEvent) => {
      playAlertSound();
      showPriceAlert(event.symbol, event.condition, event.price);
      addNotification({
        type: event.type === 'test' ? 'system' : 'price_alert',
        title: event.title,
        message: event.body,
        symbol: event.symbol,
      });
    },
  });

  // Form states
  const [settingsForm, setSettingsForm] = useState<UpdateUserData>({});
  const [newWatchlistName, setNewWatchlistName] = useState('');
  const [alertForm, setAlertForm] = useState<Partial<CreateAlertData>>({
    condition_type: 'PRICE_ABOVE',
    notification_channel: 'PUSH',
    repeat_behavior: 'ONE_TIME',
  });

  const fetchTrendingData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    
    try {
      const trendingRes = await api.get<TrendingData>('/public/trending');
      const data = trendingRes.data;
      
      const normalize = (arr: any[], fallbackType: Asset['asset_type']) =>
        (arr || []).map((item, index) => ({
          ...item,
          id: item.id || `${item.symbol}-${index}`,
          asset_type: (item.asset_type || fallbackType) as Asset['asset_type'],
          created_at: item.created_at || new Date().toISOString(),
        }));

      const combinedAssets: Asset[] = [
        ...normalize(data.stocks, 'STOCK'),
        ...normalize(data.crypto, 'CRYPTO'),
        ...normalize(data.funds, 'MUTUAL_FUND'),
      ];

      // Deduplicate by symbol (keep first occurrence)
      const uniqueBySymbol = Object.values(
        combinedAssets.reduce((acc: Record<string, Asset>, cur) => {
          if (!acc[cur.symbol]) acc[cur.symbol] = cur;
          return acc;
        }, {})
      );
      
      setAssets(uniqueBySymbol);
      setMarketSummary(data.market_summary);
      setLastUpdate(new Date());
      
      // Update tracked assets with latest prices
      updateTrackedAssetPrices(combinedAssets);
    } catch (error) {
      console.error('Error fetching trending data:', error);
      toast.error('Failed to fetch market data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const updateTrackedAssetPrices = (latestAssets: Asset[]) => {
    setTrackedAssets(prev => prev.map(tracked => {
      const updated = latestAssets.find(a => a.symbol === tracked.symbol);
      if (updated) {
        return {
          ...tracked,
          current_price: updated.current_price,
          change_percent_24h: updated.change_percent_24h,
        };
      }
      return tracked;
    }));
  };

  const fetchUserData = useCallback(async () => {
    try {
      const [userData, watchlistsData, alertsData, trackedData] = await Promise.all([
        userService.getCurrentUser(),
        watchlistsService.getWatchlists().catch(() => []),
        alertsService.getAlerts().catch(() => []),
        trackedService.getTrackedAssets().catch(() => []),
      ]);
      
      setUser(userData);
      setWatchlists(watchlistsData);
      setAlerts(alertsData);
      setTrackedAssets(trackedData);
      
      // Auto-select first tracked asset for chart
      if (trackedData.length > 0 && !selectedChartAsset) {
        setSelectedChartAsset(trackedData[0]);
      }
      
      setSettingsForm({
        name: userData.name || '',
        phone_number: userData.phone_number || '',
        preferred_contact_method: userData.preferred_contact_method,
        time_zone: userData.time_zone,
        quiet_hours_enabled: userData.quiet_hours_enabled,
      });
    } catch (error) {
      console.error('Error fetching user data:', error);
    }
  }, []);

  useEffect(() => {
    fetchTrendingData();
    fetchUserData();
  }, [fetchTrendingData, fetchUserData]);

  useEffect(() => {
    const interval = setInterval(() => {
      fetchTrendingData(true);
    }, 60000);
    return () => clearInterval(interval);
  }, [fetchTrendingData]);

  // Search functionality
  const handleSearch = async (query: string) => {
    setSearchQuery(query);
    
    if (query.length < 2) {
      setSearchResults([]);
      setLiveSearchResults([]);
      return;
    }
    
    setIsSearching(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/public/search?q=${encodeURIComponent(query)}`);
      const data = await response.json();
      const results = data.results || [];
      setSearchResults(results);
      setLiveSearchResults(results);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  const handleRefresh = () => {
    fetchTrendingData(true);
  };

  const handleSaveSettings = async () => {
    try {
      const updatedUser = await userService.updateUser(settingsForm);
      setUser(updatedUser);
      toast.success('Settings saved successfully');
      setShowSettings(false);
    } catch (error) {
      toast.error('Failed to save settings');
    }
  };

  const handleCreateWatchlist = async () => {
    if (!newWatchlistName.trim()) return;
    
    try {
      const newWatchlist = await watchlistsService.createWatchlist({ name: newWatchlistName });
      setWatchlists([...watchlists, newWatchlist]);
      setNewWatchlistName('');
      toast.success(`Watchlist "${newWatchlistName}" created`);
    } catch (error) {
      toast.error('Failed to create watchlist');
    }
  };

  const handleDeleteWatchlist = async (watchlistId: string) => {
    try {
      await watchlistsService.deleteWatchlist(watchlistId);
      setWatchlists(watchlists.filter(w => w.id !== watchlistId));
      toast.success('Watchlist deleted');
    } catch (error) {
      toast.error('Failed to delete watchlist');
    }
  };

  const handleTrackAsset = async (asset: Asset | SearchResult) => {
    // Check if already tracked
    if (trackedAssets.some(t => t.symbol === asset.symbol)) {
      toast.info(`${asset.symbol} is already being tracked`);
      return;
    }

    try {
      const trackData: TrackAssetData = {
        symbol: asset.symbol,
        name: asset.name || asset.symbol,
        asset_type: asset.asset_type || 'STOCK',
        exchange: asset.exchange,
      };

      const newTracked = await trackedService.trackAsset(trackData);
      setTrackedAssets(prev => [...prev, newTracked]);
      
      // Auto-select for chart if first tracked asset
      if (trackedAssets.length === 0) {
        setSelectedChartAsset(newTracked);
      }
      
      toast.success(`${asset.symbol} is now being tracked`);
      setShowAddAsset(false);
      setShowSearch(false);
      setSelectedAsset(null);
    } catch (error: any) {
      if (error.response?.status === 400) {
        toast.info(`${asset.symbol} is already being tracked`);
      } else {
        toast.error('Failed to track asset');
      }
    }
  };

  const handleUntrackAsset = async (symbol: string) => {
    try {
      await trackedService.untrackAsset(symbol);
      setTrackedAssets(prev => prev.filter(t => t.symbol !== symbol));
      
      // If untracking the currently selected chart asset, select another
      if (selectedChartAsset?.symbol === symbol) {
        const remaining = trackedAssets.filter(t => t.symbol !== symbol);
        setSelectedChartAsset(remaining.length > 0 ? remaining[0] : null);
      }
      
      toast.success(`${symbol} removed from tracking`);
    } catch (error) {
      toast.error('Failed to untrack asset');
    }
  };

  const handleCreateAlert = async () => {
    if (!selectedAsset || !alertForm.threshold_value) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      const newAlert = await alertsService.createAlert({
        ...alertForm,
        name: `${selectedAsset.symbol} Alert`,
      } as CreateAlertData);
      
      setAlerts([newAlert, ...alerts]);
      toast.success('Alert created successfully');
      setShowCreateAlert(false);
      setAlertForm({
        condition_type: 'PRICE_ABOVE',
        notification_channel: 'EMAIL',
        repeat_behavior: 'ONE_TIME',
      });
    } catch (error) {
      toast.error('Failed to create alert');
    }
  };

  const handleToggleAlert = async (alertId: string, isActive: boolean) => {
    try {
      await alertsService.toggleAlert(alertId, isActive);
      setAlerts(alerts.map(a => a.id === alertId ? { ...a, is_active: isActive } : a));
      toast.success(`Alert ${isActive ? 'enabled' : 'disabled'}`);
    } catch (error) {
      toast.error('Failed to update alert');
    }
  };

  const handleDeleteAlert = async (alertId: string) => {
    try {
      await alertsService.deleteAlert(alertId);
      setAlerts(alerts.filter(a => a.id !== alertId));
      toast.success('Alert deleted');
    } catch (error) {
      toast.error('Failed to delete alert');
    }
  };

  // Push notification handlers
  const handleEnablePushNotifications = async () => {
    const granted = await requestPermission();
    if (granted) {
      addNotification({
        type: 'system',
        title: 'Push Notifications Enabled',
        message: 'You will now receive browser notifications for price alerts.',
      });
    }
  };

  const handleTestNotification = async () => {
    try {
      const result = await notificationsService.sendTestNotification({ channel: 'PUSH' });
      if (result.data) {
        showPriceAlert('TEST', 'Test notification sent successfully', '0.00');
        addNotification({
          type: 'system',
          title: result.data.title,
          message: result.data.body,
        });
      }
      toast.success('Test notification sent!');
    } catch (error) {
      toast.error('Failed to send test notification');
    }
  };

  // Watchlist handlers
  const handleAddToWatchlist = async (watchlistId: string, asset: Asset) => {
    try {
      await watchlistsService.addAssetBySymbol(watchlistId, {
        symbol: asset.symbol,
        name: asset.name,
        asset_type: asset.asset_type,
        exchange: asset.exchange,
      });
      toast.success(`${asset.symbol} added to watchlist`);
      setShowAddToWatchlist(false);
      // Refresh watchlists
      const updatedWatchlists = await watchlistsService.getWatchlists();
      setWatchlists(updatedWatchlists);
    } catch (error: any) {
      if (error.response?.data?.message?.includes('already')) {
        toast.info(`${asset.symbol} is already in this watchlist`);
      } else {
        toast.error('Failed to add asset to watchlist');
      }
    }
  };

  const handleViewWatchlist = async (watchlistId: string) => {
    try {
      const detail = await watchlistsService.getWatchlist(watchlistId);
      setSelectedWatchlist(detail);
    } catch (error) {
      toast.error('Failed to load watchlist');
    }
  };

  const handleRemoveFromWatchlist = async (watchlistId: string, symbol: string) => {
    try {
      await watchlistsService.removeAssetBySymbol(watchlistId, symbol);
      toast.success(`${symbol} removed from watchlist`);
      // Refresh the current watchlist
      if (selectedWatchlist) {
        const detail = await watchlistsService.getWatchlist(watchlistId);
        setSelectedWatchlist(detail);
      }
    } catch (error) {
      toast.error('Failed to remove asset from watchlist');
    }
  };

  const getFilteredAssets = () => {
    let filtered = assets;
    
    // Apply type filter
    if (assetFilter !== 'all') {
      filtered = assets.filter(asset => {
        if (assetFilter === 'stocks') return asset.asset_type === 'STOCK';
        if (assetFilter === 'crypto') return asset.asset_type === 'CRYPTO';
        if (assetFilter === 'funds') return asset.asset_type === 'ETF' || asset.asset_type === 'MUTUAL_FUND';
        return true;
      });
    }
    
    // Apply search filter (local)
    if (searchQuery) {
      filtered = filtered.filter(asset =>
        asset.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
        asset.name?.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }
    
    // If user has an active search and live results, prefer merged live results
    if (searchQuery.length >= 2 && liveSearchResults.length > 0) {
      const mapped = liveSearchResults.map((res, index) => ({
        id: `live-${res.symbol}-${index}`,
        symbol: res.symbol,
        name: res.name,
        asset_type: (res.asset_type || 'STOCK') as Asset['asset_type'],
        exchange: res.exchange,
        currency: 'USD',
        created_at: new Date().toISOString(),
      }));

      const merged = [...mapped, ...filtered];
      const unique = Object.values(
        merged.reduce((acc: Record<string, Asset>, cur) => {
          if (!acc[cur.symbol]) acc[cur.symbol] = cur;
          return acc;
        }, {})
      );
      return unique;
    }
    
    return filtered;
  };

  const filteredAssets = getFilteredAssets();
  const isAssetTracked = (symbol: string) => trackedAssets.some(t => t.symbol === symbol);

  const getAssetTypeIcon = (type: string) => {
    switch (type) {
      case 'STOCK': return <Building2 size={12} />;
      case 'CRYPTO': return <Coins size={12} />;
      case 'ETF':
      case 'MUTUAL_FUND': return <PiggyBank size={12} />;
      default: return null;
    }
  };

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
            {/* Logo and Navigation */}
            <div className="flex items-center gap-6">
              <Link to="/" className="flex items-center gap-3 group">
                <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-neon-cyan to-neon-magenta flex items-center justify-center group-hover:scale-105 transition-transform">
                  <Eye className="text-white" size={20} />
                </div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
                  MarketEye
                </h1>
              </Link>
              <div className="hidden md:flex items-center gap-2">
                <div className="w-2 h-2 bg-neon-cyan rounded-full animate-pulse" />
                <span className="text-sm text-neon-cyan">Live</span>
              </div>
              {/* Navigation Links */}
              <nav className="hidden md:flex items-center gap-4 ml-4 pl-4 border-l border-neon-cyan/20">
                <Link 
                  to="/" 
                  className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-neon-cyan transition-colors"
                >
                  <Home size={16} />
                  Home
                </Link>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSettings(true)}
                  className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-yellow-500"
                >
                  <Wallet size={16} />
                  Watchlists
                </Button>
              </nav>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => setShowSearch(true)}
                title="Search assets"
              >
                <Search size={20} />
              </Button>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={handleRefresh}
                disabled={refreshing}
                title="Refresh data"
              >
                <RefreshCw size={20} className={refreshing ? 'animate-spin' : ''} />
              </Button>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => setShowNotifications(true)}
                title="Notifications"
                className="relative"
              >
                <BellRing size={20} />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-neon-magenta rounded-full text-xs flex items-center justify-center">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Button>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => setShowAlerts(true)}
                title="Price Alerts"
                className="relative"
              >
                <Bell size={20} />
                {alerts.filter(a => a.is_active).length > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-neon-cyan rounded-full text-xs flex items-center justify-center">
                    {alerts.filter(a => a.is_active).length}
                  </span>
                )}
              </Button>
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => setShowSettings(true)}
                title="Settings"
              >
                <Settings size={20} />
              </Button>
              <Button variant="ghost" size="icon" onClick={handleLogout} title="Logout">
                <LogOut size={20} />
              </Button>
            </div>
          </div>
        </div>
      </motion.header>

      <div className="container mx-auto px-6 py-8">
        {/* Welcome message */}
        {user && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6"
          >
            <h2 className="text-xl text-muted-foreground">
              Welcome back, <span className="text-neon-cyan font-semibold">{user.name || user.email}</span>
            </h2>
          </motion.div>
        )}

        {/* Stats Row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
        >
          <Card className="glass border-neon-cyan/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-muted-foreground">
                <TrendingUp className="text-neon-cyan" size={16} />
                Gainers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-neon-cyan">{marketSummary.gainers}</div>
            </CardContent>
          </Card>

          <Card className="glass border-neon-magenta/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-muted-foreground">
                <TrendingDown className="text-neon-magenta" size={16} />
                Losers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-neon-magenta">{marketSummary.losers}</div>
            </CardContent>
          </Card>

          <Card className="glass border-neon-lime/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-muted-foreground">
                <Bell className="text-neon-lime" size={16} />
                Active Alerts
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-neon-lime">{alerts.filter(a => a.is_active).length}</div>
            </CardContent>
          </Card>

          <Card className="glass border-yellow-500/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-muted-foreground">
                <Star className="text-yellow-500" size={16} />
                Tracked Assets
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-500">{trackedAssets.length}</div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Tracked Assets Section with Chart */}
        {trackedAssets.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15 }}
            className="mb-8"
          >
            <div 
              className="flex items-center justify-between mb-4 cursor-pointer"
              onClick={() => setShowTrackedSection(!showTrackedSection)}
            >
              <h2 className="text-2xl font-bold text-yellow-500 flex items-center gap-2">
                <Star size={24} />
                Your Tracked Assets ({trackedAssets.length})
              </h2>
              <Button variant="ghost" size="sm">
                {showTrackedSection ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
              </Button>
            </div>

            <AnimatePresence>
              {showTrackedSection && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-6"
                >
                  {/* Asset selector buttons */}
                  <div className="flex flex-wrap gap-2">
                    {trackedAssets.map((asset) => (
                      <div key={asset.symbol} className="relative group">
                        <Button
                          variant={selectedChartAsset?.symbol === asset.symbol ? 'neon' : 'ghost'}
                          size="sm"
                          onClick={() => setSelectedChartAsset(asset)}
                          className="pr-8"
                        >
                          <span className={cn(
                            "w-2 h-2 rounded-full mr-2",
                            asset.asset_type === 'CRYPTO' ? 'bg-neon-magenta' : 
                            asset.asset_type === 'MUTUAL_FUND' || asset.asset_type === 'ETF' ? 'bg-neon-lime' : 
                            'bg-neon-cyan'
                          )} />
                          {asset.symbol}
                          {asset.change_percent_24h && (
                            <span className={cn(
                              "ml-2 text-xs",
                              parseFloat(asset.change_percent_24h) >= 0 ? 'text-neon-lime' : 'text-neon-magenta'
                            )}>
                              {parseFloat(asset.change_percent_24h) >= 0 ? '+' : ''}
                              {parseFloat(asset.change_percent_24h).toFixed(1)}%
                            </span>
                          )}
                        </Button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleUntrackAsset(asset.symbol);
                          }}
                          className="absolute right-1 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-destructive/20 rounded"
                          title="Remove from tracking"
                        >
                          <X size={12} className="text-destructive" />
                        </button>
                      </div>
                    ))}
                  </div>

                  {/* Chart for selected asset */}
                  {selectedChartAsset && (
                    <PriceChart
                      symbol={selectedChartAsset.symbol}
                      name={selectedChartAsset.name}
                      assetType={selectedChartAsset.asset_type as 'STOCK' | 'CRYPTO'}
                      currentPrice={selectedChartAsset.current_price}
                      changePercent={selectedChartAsset.change_percent_24h}
                    />
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )}

        {/* Tab selector and filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="flex gap-2">
            <Button
              variant={activeTab === 'trending' ? 'neon' : 'ghost'}
              onClick={() => setActiveTab('trending')}
            >
              <TrendingUp size={16} className="mr-2" />
              Trending
            </Button>
            <Button
              variant={activeTab === 'tracked' ? 'neon' : 'ghost'}
              onClick={() => setActiveTab('tracked')}
              disabled={trackedAssets.length === 0}
            >
              <Star size={16} className="mr-2" />
              My Portfolio ({trackedAssets.length})
            </Button>
          </div>
          
          {activeTab === 'trending' && (
            <div className="flex gap-2">
              <Button
                variant={assetFilter === 'all' ? 'outline' : 'ghost'}
                size="sm"
                onClick={() => setAssetFilter('all')}
              >
                All
              </Button>
              <Button
                variant={assetFilter === 'stocks' ? 'outline' : 'ghost'}
                size="sm"
                onClick={() => setAssetFilter('stocks')}
              >
                <Building2 size={14} className="mr-1" />
                Stocks
              </Button>
              <Button
                variant={assetFilter === 'crypto' ? 'outline' : 'ghost'}
                size="sm"
                onClick={() => setAssetFilter('crypto')}
              >
                <Coins size={14} className="mr-1" />
                Crypto
              </Button>
              <Button
                variant={assetFilter === 'funds' ? 'outline' : 'ghost'}
                size="sm"
                onClick={() => setAssetFilter('funds')}
              >
                <PiggyBank size={14} className="mr-1" />
                Funds
              </Button>
            </div>
          )}
        </div>

        {/* Quick Search */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-col md:flex-row gap-4 mb-8"
        >
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={20} />
            <Input
              placeholder="Filter displayed assets..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button variant="neon" onClick={() => setShowSearch(true)}>
            <Plus size={16} className="mr-2" />
            Find & Track Assets
          </Button>
        </motion.div>

        {/* Assets Grid */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-neon-cyan">
              {activeTab === 'trending' ? 'Market Overview' : 'Your Portfolio'}
            </h2>
            {lastUpdate && (
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                {refreshing ? (
                  <>
                    <RefreshCw size={14} className="animate-spin" />
                    Updating...
                  </>
                ) : (
                  <>
                    <Clock size={14} />
                    Updated {lastUpdate.toLocaleTimeString()}
                  </>
                )}
              </div>
            )}
          </div>
          
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {[...Array(8)].map((_, index) => (
                <div key={index} className="glass rounded-lg p-6 animate-pulse">
                  <div className="h-6 bg-neon-cyan/20 rounded w-1/2 mb-4"></div>
                  <div className="h-8 bg-neon-cyan/10 rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-neon-cyan/10 rounded w-1/4"></div>
                </div>
              ))}
            </div>
          ) : activeTab === 'tracked' ? (
            // Show tracked assets
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {trackedAssets
                .filter(asset => 
                  !searchQuery || 
                  asset.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
                  asset.name.toLowerCase().includes(searchQuery.toLowerCase())
                )
                .map((tracked, index) => {
                  const fullAsset = assets.find(a => a.symbol === tracked.symbol) || {
                    id: tracked.symbol,
                    symbol: tracked.symbol,
                    name: tracked.name,
                    asset_type: tracked.asset_type as Asset['asset_type'],
                    current_price: tracked.current_price,
                    change_percent_24h: tracked.change_percent_24h,
                    exchange: tracked.exchange,
                    currency: 'USD',
                    created_at: tracked.tracked_at,
                  };
                  
                  return (
                    <motion.div
                      key={tracked.symbol}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.05 * index }}
                      className="relative group"
                    >
                      <div onClick={() => setSelectedChartAsset(tracked)}>
                        <AssetTile
                          asset={fullAsset as Asset}
                          onClick={() => setSelectedChartAsset(tracked)}
                        />
                      </div>
                      <div className="absolute top-2 right-2 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center">
                        <Star size={14} className="text-cyber-darker" fill="currentColor" />
                      </div>
                      <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 bg-cyber-darker/80"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedChartAsset(tracked);
                          }}
                          title="View chart"
                        >
                          <LineChart size={14} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 bg-cyber-darker/80"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedAsset(fullAsset as Asset);
                            setShowCreateAlert(true);
                          }}
                          title="Create alert"
                        >
                          <Bell size={14} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-8 w-8 p-0 bg-cyber-darker/80 hover:bg-destructive/20"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleUntrackAsset(tracked.symbol);
                          }}
                          title="Stop tracking"
                        >
                          <Trash2 size={14} />
                        </Button>
                      </div>
                    </motion.div>
                  );
                })}
            </div>
          ) : (
            // Show trending assets
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {filteredAssets.map((asset, index) => (
                <motion.div
                  key={asset.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.05 * Math.min(index, 10) }}
                  className="relative group"
                >
                  <AssetTile
                    asset={asset}
                    onClick={() => {
                      setSelectedAsset(asset);
                      setShowAddAsset(true);
                    }}
                  />
                  {isAssetTracked(asset.symbol) && (
                    <div className="absolute top-2 right-2 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center">
                      <Star size={14} className="text-cyber-darker" fill="currentColor" />
                    </div>
                  )}
                  <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-8 w-8 p-0 bg-cyber-darker/80"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedAsset(asset);
                        setShowCreateAlert(true);
                      }}
                      title="Create alert"
                    >
                      <Bell size={14} />
                    </Button>
                    {isAssetTracked(asset.symbol) ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 p-0 bg-cyber-darker/80 hover:bg-destructive/20"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleUntrackAsset(asset.symbol);
                        }}
                        title="Stop tracking"
                      >
                        <EyeOff size={14} />
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 w-8 p-0 bg-cyber-darker/80"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTrackAsset(asset);
                        }}
                        title="Track this asset"
                      >
                        <Eye size={14} />
                      </Button>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
          
          {!loading && filteredAssets.length === 0 && activeTab === 'trending' && (
            <div className="text-center py-12 text-muted-foreground">
              No assets found. Try changing your filter or search.
            </div>
          )}
          
          {!loading && trackedAssets.length === 0 && activeTab === 'tracked' && (
            <div className="text-center py-12">
              <Star size={48} className="mx-auto mb-4 text-muted-foreground" />
              <p className="text-muted-foreground">You haven't tracked any assets yet.</p>
              <p className="text-sm text-muted-foreground mt-2">
                Use the search button to find and track assets.
              </p>
              <Button 
                variant="neon" 
                className="mt-4"
                onClick={() => setShowSearch(true)}
              >
                <Search size={16} className="mr-2" />
                Find Assets to Track
              </Button>
            </div>
          )}
        </motion.div>

        {/* Background decorations */}
        <div className="fixed top-0 left-0 w-full h-full pointer-events-none overflow-hidden -z-10">
          <div className="absolute top-20 left-10 w-64 h-64 bg-neon-cyan/5 rounded-full blur-3xl" />
          <div className="absolute bottom-20 right-10 w-96 h-96 bg-neon-magenta/5 rounded-full blur-3xl" />
        </div>
      </div>

      {/* Search Modal */}
      <Dialog open={showSearch} onOpenChange={setShowSearch}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Search size={20} />
              Find Assets to Track
            </DialogTitle>
            <DialogDescription>
              Search for stocks, crypto, ETFs, or mutual funds (including Fidelity, Vanguard)
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            <Input
              placeholder="Search by symbol or name (e.g., FXAIX, VOO, BTC)..."
              onChange={(e) => handleSearch(e.target.value)}
              autoFocus
            />
            
            {isSearching && (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="animate-spin mr-2" size={20} />
                Searching...
              </div>
            )}
            
            {searchResults.length > 0 && (
              <div className="max-h-96 overflow-y-auto space-y-2">
                {searchResults.map((result) => (
                  <div
                    key={result.symbol}
                    className="flex items-center justify-between p-3 rounded-lg bg-cyber-dark hover:bg-cyber-dark/80 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-10 h-10 rounded-lg flex items-center justify-center",
                        result.asset_type === 'CRYPTO' ? 'bg-neon-magenta/20' :
                        result.asset_type === 'MUTUAL_FUND' || result.asset_type === 'ETF' ? 'bg-neon-lime/20' :
                        'bg-neon-cyan/20'
                      )}>
                        {getAssetTypeIcon(result.asset_type)}
                      </div>
                      <div>
                        <div className="font-semibold">{result.symbol}</div>
                        <div className="text-sm text-muted-foreground truncate max-w-xs">{result.name}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={cn(
                        "text-xs px-2 py-1 rounded",
                        result.asset_type === 'CRYPTO' ? 'bg-neon-magenta/20 text-neon-magenta' :
                        result.asset_type === 'MUTUAL_FUND' ? 'bg-neon-lime/20 text-neon-lime' :
                        result.asset_type === 'ETF' ? 'bg-green-500/20 text-green-400' :
                        'bg-neon-cyan/20 text-neon-cyan'
                      )}>
                        {result.asset_type}
                      </span>
                      {isAssetTracked(result.symbol) ? (
                        <Button size="sm" variant="ghost" disabled>
                          <Star size={14} className="mr-1" fill="currentColor" />
                          Tracked
                        </Button>
                      ) : (
                        <Button
                          size="sm"
                          variant="neon"
                          onClick={() => handleTrackAsset(result)}
                        >
                          <Plus size={14} className="mr-1" />
                          Track
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {!isSearching && searchResults.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <p>Search for assets by entering a symbol or name above.</p>
                <p className="text-sm mt-2">
                  Examples: AAPL, BTC, FXAIX (Fidelity 500), VOO (Vanguard S&P 500 ETF)
                </p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Settings Modal */}
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserIcon size={20} />
              Account Settings
            </DialogTitle>
            <DialogDescription>
              Manage your profile and notification preferences
            </DialogDescription>
          </DialogHeader>
          
          <Tabs defaultValue="profile" className="mt-4">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="profile">Profile</TabsTrigger>
              <TabsTrigger value="notifications">Notifications</TabsTrigger>
              <TabsTrigger value="watchlists">Watchlists</TabsTrigger>
            </TabsList>
            
            <TabsContent value="profile" className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input
                  value={settingsForm.name || ''}
                  onChange={(e) => setSettingsForm({ ...settingsForm, name: e.target.value })}
                  placeholder="Your name"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Email</Label>
                <Input value={user?.email || ''} disabled className="opacity-50" />
                <p className="text-xs text-muted-foreground">Email cannot be changed</p>
              </div>
              
              <div className="space-y-2">
                <Label>Phone Number</Label>
                <Input
                  value={settingsForm.phone_number || ''}
                  onChange={(e) => setSettingsForm({ ...settingsForm, phone_number: e.target.value })}
                  placeholder="+1 234 567 8900"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Time Zone</Label>
                <Select
                  value={settingsForm.time_zone || 'UTC'}
                  onValueChange={(value) => setSettingsForm({ ...settingsForm, time_zone: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIME_ZONES.map((tz) => (
                      <SelectItem key={tz.value} value={tz.value}>{tz.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </TabsContent>
            
            <TabsContent value="notifications" className="space-y-4 mt-4">
              {/* Browser Push Notifications */}
              <div className="p-4 rounded-lg bg-cyber-dark space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <Label className="text-base">Browser Push Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Receive real-time alerts even when the app is in background
                    </p>
                  </div>
                  <div className={cn(
                    "px-2 py-1 rounded text-xs",
                    pushEnabled ? "bg-neon-lime/20 text-neon-lime" : "bg-yellow-500/20 text-yellow-500"
                  )}>
                    {pushEnabled ? 'Enabled' : 'Disabled'}
                  </div>
                </div>
                {!pushEnabled && pushSupported && (
                  <Button variant="neon" size="sm" onClick={handleEnablePushNotifications}>
                    <BellRing size={14} className="mr-2" />
                    Enable Push Notifications
                  </Button>
                )}
                {pushEnabled && (
                  <Button variant="ghost" size="sm" onClick={handleTestNotification}>
                    Send Test Notification
                  </Button>
                )}
                {!pushSupported && (
                  <p className="text-sm text-destructive">
                    Your browser doesn't support push notifications.
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label>Preferred Contact Method</Label>
                <Select
                  value={settingsForm.preferred_contact_method || 'EMAIL'}
                  onValueChange={(value: any) => setSettingsForm({ ...settingsForm, preferred_contact_method: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CONTACT_METHODS.map((method) => (
                      <SelectItem key={method.value} value={method.value}>{method.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="flex items-center justify-between p-4 rounded-lg bg-cyber-dark">
                <div>
                  <Label>Quiet Hours</Label>
                  <p className="text-sm text-muted-foreground">Pause notifications during set hours</p>
                </div>
                <Switch
                  checked={settingsForm.quiet_hours_enabled || false}
                  onCheckedChange={(checked) => setSettingsForm({ ...settingsForm, quiet_hours_enabled: checked })}
                />
              </div>
              
              {settingsForm.quiet_hours_enabled && (
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Start Time</Label>
                    <Input
                      type="time"
                      value={settingsForm.quiet_hours_start || '22:00'}
                      onChange={(e) => setSettingsForm({ ...settingsForm, quiet_hours_start: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>End Time</Label>
                    <Input
                      type="time"
                      value={settingsForm.quiet_hours_end || '08:00'}
                      onChange={(e) => setSettingsForm({ ...settingsForm, quiet_hours_end: e.target.value })}
                    />
                  </div>
                </div>
              )}
            </TabsContent>
            
            <TabsContent value="watchlists" className="space-y-4 mt-4">
              <div className="flex gap-2">
                <Input
                  value={newWatchlistName}
                  onChange={(e) => setNewWatchlistName(e.target.value)}
                  placeholder="New watchlist name"
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateWatchlist()}
                />
                <Button onClick={handleCreateWatchlist} variant="neon">
                  <Plus size={16} />
                </Button>
              </div>
              
              <div className="space-y-2">
                {watchlists.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    No watchlists yet. Create one to organize your assets.
                  </p>
                ) : (
                  watchlists.map((watchlist) => (
                    <div key={watchlist.id} className="flex items-center justify-between p-3 rounded-lg bg-cyber-dark">
                      <div 
                        className="flex-1 cursor-pointer"
                        onClick={() => handleViewWatchlist(watchlist.id)}
                      >
                        <div className="font-medium flex items-center gap-2">
                          <Star size={14} className="text-yellow-500" />
                          {watchlist.name}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          Created {new Date(watchlist.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleViewWatchlist(watchlist.id)}
                          title="View watchlist"
                        >
                          <Eye size={16} />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteWatchlist(watchlist.id)}
                          className="text-destructive hover:text-destructive"
                          title="Delete watchlist"
                        >
                          <Trash2 size={16} />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </TabsContent>
          </Tabs>
          
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowSettings(false)}>Cancel</Button>
            <Button variant="neon" onClick={handleSaveSettings}>Save Changes</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Alerts Modal */}
      <Dialog open={showAlerts} onOpenChange={setShowAlerts}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Bell size={20} />
              Price Alerts
            </DialogTitle>
            <DialogDescription>
              Manage your price alerts and notifications
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {alerts.length === 0 ? (
              <div className="text-center py-12">
                <AlertTriangle size={48} className="mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">No alerts set up yet.</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Click on any asset and select the bell icon to create an alert.
                </p>
              </div>
            ) : (
              alerts.map((alert) => (
                <div key={alert.id} className="flex items-center justify-between p-4 rounded-lg bg-cyber-dark">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{alert.name || 'Price Alert'}</span>
                      <span className={`text-xs px-2 py-0.5 rounded ${alert.is_active ? 'bg-neon-cyan/20 text-neon-cyan' : 'bg-gray-500/20 text-gray-400'}`}>
                        {alert.is_active ? 'Active' : 'Paused'}
                      </span>
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">
                      {CONDITION_TYPE_LABELS[alert.condition_type as ConditionType]} ${alert.threshold_value}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      Notify via {alert.notification_channel} • Triggered {alert.trigger_count} times
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={alert.is_active}
                      onCheckedChange={(checked) => handleToggleAlert(alert.id, checked)}
                    />
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleDeleteAlert(alert.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Add to Tracked Modal */}
      <Dialog open={showAddAsset} onOpenChange={setShowAddAsset}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Track {selectedAsset?.symbol}</DialogTitle>
            <DialogDescription>
              Add this asset to your tracked list
            </DialogDescription>
          </DialogHeader>
          
          {selectedAsset && (
            <div className="space-y-4 mt-4">
              <div className="p-4 rounded-lg bg-cyber-dark">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={cn(
                      "w-12 h-12 rounded-lg flex items-center justify-center text-lg",
                      selectedAsset.asset_type === 'CRYPTO' ? 'bg-neon-magenta/20 text-neon-magenta' :
                      selectedAsset.asset_type === 'MUTUAL_FUND' || selectedAsset.asset_type === 'ETF' ? 'bg-neon-lime/20 text-neon-lime' :
                      'bg-neon-cyan/20 text-neon-cyan'
                    )}>
                      {getAssetTypeIcon(selectedAsset.asset_type)}
                    </div>
                    <div>
                      <div className="text-lg font-bold">{selectedAsset.symbol}</div>
                      <div className="text-sm text-muted-foreground">{selectedAsset.name}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-semibold">
                      ${parseFloat(selectedAsset.current_price || '0').toLocaleString()}
                    </div>
                    <div className={`text-sm ${parseFloat(selectedAsset.change_percent_24h || '0') >= 0 ? 'text-neon-lime' : 'text-neon-magenta'}`}>
                      {parseFloat(selectedAsset.change_percent_24h || '0') >= 0 ? '+' : ''}
                      {parseFloat(selectedAsset.change_percent_24h || '0').toFixed(2)}%
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 gap-2">
                <Button
                  variant="neon"
                  className="w-full"
                  onClick={() => handleTrackAsset(selectedAsset)}
                  disabled={isAssetTracked(selectedAsset.symbol)}
                >
                  <Star size={16} className="mr-2" />
                  {isAssetTracked(selectedAsset.symbol) ? 'Already Tracked' : 'Track Asset'}
                </Button>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    setShowAddAsset(false);
                    setShowAddToWatchlist(true);
                  }}
                >
                  <Wallet size={16} className="mr-2" />
                  Add to Watchlist
                </Button>
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() => {
                    setShowAddAsset(false);
                    setShowCreateAlert(true);
                  }}
                >
                  <Bell size={16} className="mr-2" />
                  Create Alert
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Create Alert Modal */}
      <Dialog open={showCreateAlert} onOpenChange={setShowCreateAlert}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Price Alert</DialogTitle>
            <DialogDescription>
              Get notified when {selectedAsset?.symbol} reaches your target
            </DialogDescription>
          </DialogHeader>
          
          {selectedAsset && (
            <div className="space-y-4 mt-4">
              <div className="p-4 rounded-lg bg-cyber-dark">
                <div className="text-sm text-muted-foreground">Current Price</div>
                <div className="text-2xl font-bold text-neon-cyan">
                  ${parseFloat(selectedAsset.current_price || '0').toLocaleString()}
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Alert Condition</Label>
                <Select
                  value={alertForm.condition_type}
                  onValueChange={(value: ConditionType) => setAlertForm({ ...alertForm, condition_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(CONDITION_TYPE_LABELS).map(([key, label]) => (
                      <SelectItem key={key} value={key}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Target Value</Label>
                <Input
                  type="number"
                  value={alertForm.threshold_value || ''}
                  onChange={(e) => setAlertForm({ ...alertForm, threshold_value: e.target.value })}
                  placeholder={alertForm.condition_type?.includes('PERCENT') ? 'e.g., 5' : 'e.g., 100.00'}
                />
              </div>
              
              <div className="space-y-2">
                <Label>Notification Method</Label>
                <Select
                  value={alertForm.notification_channel}
                  onValueChange={(value: any) => setAlertForm({ ...alertForm, notification_channel: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="PUSH">Push Notification (Browser)</SelectItem>
                    <SelectItem value="EMAIL">Email</SelectItem>
                    <SelectItem value="SMS">SMS</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Repeat Behavior</Label>
                <Select
                  value={alertForm.repeat_behavior}
                  onValueChange={(value: any) => setAlertForm({ ...alertForm, repeat_behavior: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ONE_TIME">One Time Only</SelectItem>
                    <SelectItem value="ONCE_PER_HOUR">Once Per Hour</SelectItem>
                    <SelectItem value="ONCE_PER_DAY">Once Per Day</SelectItem>
                    <SelectItem value="UNLIMITED">Unlimited</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="ghost" onClick={() => setShowCreateAlert(false)}>Cancel</Button>
            <Button variant="neon" onClick={handleCreateAlert}>Create Alert</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Notifications Modal */}
      <Dialog open={showNotifications} onOpenChange={setShowNotifications}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BellRing size={20} />
              Notifications
            </DialogTitle>
            <DialogDescription>
              Your recent notifications and alerts
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {/* Push notification status */}
            <div className="p-4 rounded-lg bg-cyber-dark flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-3 h-3 rounded-full",
                  pushEnabled ? "bg-neon-lime" : "bg-yellow-500"
                )} />
                <div>
                  <div className="font-medium">Browser Push Notifications</div>
                  <div className="text-sm text-muted-foreground">
                    {!pushSupported 
                      ? 'Not supported in this browser'
                      : pushEnabled 
                        ? 'Enabled - you will receive browser alerts' 
                        : 'Enable to get real-time alerts'}
                  </div>
                </div>
              </div>
              {pushSupported && !pushEnabled && (
                <Button variant="neon" size="sm" onClick={handleEnablePushNotifications}>
                  Enable
                </Button>
              )}
              {pushEnabled && (
                <Button variant="ghost" size="sm" onClick={handleTestNotification}>
                  Test
                </Button>
              )}
            </div>

            {/* Notifications actions */}
            {appNotifications.length > 0 && (
              <div className="flex gap-2 justify-end">
                <Button variant="ghost" size="sm" onClick={markAllAsRead}>
                  <CheckCheck size={14} className="mr-1" />
                  Mark all read
                </Button>
                <Button variant="ghost" size="sm" onClick={clearNotifications} className="text-destructive">
                  <Trash2 size={14} className="mr-1" />
                  Clear all
                </Button>
              </div>
            )}

            {/* Notification list */}
            {appNotifications.length === 0 ? (
              <div className="text-center py-12">
                <BellRing size={48} className="mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">No notifications yet.</p>
                <p className="text-sm text-muted-foreground mt-2">
                  You'll see price alerts and system messages here.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {appNotifications.map((notif) => (
                  <div 
                    key={notif.id} 
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-lg transition-colors cursor-pointer",
                      notif.read ? "bg-cyber-dark/50" : "bg-cyber-dark border-l-2 border-neon-cyan"
                    )}
                    onClick={() => markAsRead(notif.id)}
                  >
                    <div className={cn(
                      "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0",
                      notif.type === 'price_alert' ? "bg-neon-magenta/20 text-neon-magenta" :
                      notif.type === 'system' ? "bg-neon-cyan/20 text-neon-cyan" :
                      "bg-neon-lime/20 text-neon-lime"
                    )}>
                      {notif.type === 'price_alert' ? <AlertTriangle size={14} /> :
                       notif.type === 'system' ? <Settings size={14} /> :
                       <Bell size={14} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium text-sm truncate">{notif.title}</div>
                        <div className="text-xs text-muted-foreground flex-shrink-0">
                          {new Date(notif.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">{notif.message}</div>
                      {notif.symbol && (
                        <div className="text-xs text-neon-cyan mt-1">{notif.symbol}</div>
                      )}
                    </div>
                    {!notif.read && (
                      <div className="w-2 h-2 bg-neon-cyan rounded-full flex-shrink-0" />
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Add to Watchlist Modal */}
      <Dialog open={showAddToWatchlist} onOpenChange={setShowAddToWatchlist}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add to Watchlist</DialogTitle>
            <DialogDescription>
              Choose a watchlist to add {selectedAsset?.symbol}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {watchlists.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground">No watchlists yet.</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Create a watchlist in Settings first.
                </p>
                <Button 
                  variant="neon" 
                  className="mt-4"
                  onClick={() => {
                    setShowAddToWatchlist(false);
                    setShowSettings(true);
                  }}
                >
                  Go to Settings
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {watchlists.map((watchlist) => (
                  <Button
                    key={watchlist.id}
                    variant="ghost"
                    className="w-full justify-start"
                    onClick={() => selectedAsset && handleAddToWatchlist(watchlist.id, selectedAsset)}
                  >
                    <Star size={16} className="mr-2 text-yellow-500" />
                    {watchlist.name}
                  </Button>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* View Watchlist Modal */}
      <Dialog open={!!selectedWatchlist} onOpenChange={() => setSelectedWatchlist(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Star size={20} className="text-yellow-500" />
              {selectedWatchlist?.name}
            </DialogTitle>
            <DialogDescription>
              {selectedWatchlist?.description || 'Your custom watchlist'}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 mt-4">
            {selectedWatchlist?.assets?.length === 0 ? (
              <div className="text-center py-8">
                <Star size={48} className="mx-auto mb-4 text-muted-foreground" />
                <p className="text-muted-foreground">This watchlist is empty.</p>
                <p className="text-sm text-muted-foreground mt-2">
                  Add assets from the trending or search view.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {selectedWatchlist?.assets?.map((asset) => (
                  <div key={asset.id} className="flex items-center justify-between p-3 rounded-lg bg-cyber-dark">
                    <div className="flex items-center gap-3">
                      <div className={cn(
                        "w-10 h-10 rounded-lg flex items-center justify-center",
                        asset.asset_type === 'CRYPTO' ? 'bg-neon-magenta/20' :
                        asset.asset_type === 'MUTUAL_FUND' || asset.asset_type === 'ETF' ? 'bg-neon-lime/20' :
                        'bg-neon-cyan/20'
                      )}>
                        {getAssetTypeIcon(asset.asset_type)}
                      </div>
                      <div>
                        <div className="font-semibold">{asset.symbol}</div>
                        <div className="text-sm text-muted-foreground">{asset.name}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      {asset.current_price && (
                        <div className="text-right">
                          <div className="font-medium">${parseFloat(asset.current_price).toLocaleString()}</div>
                          {asset.change_percent_24h && (
                            <div className={cn(
                              "text-sm",
                              parseFloat(asset.change_percent_24h) >= 0 ? 'text-neon-lime' : 'text-neon-magenta'
                            )}>
                              {parseFloat(asset.change_percent_24h) >= 0 ? '+' : ''}
                              {parseFloat(asset.change_percent_24h).toFixed(2)}%
                            </div>
                          )}
                        </div>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => selectedWatchlist && handleRemoveFromWatchlist(selectedWatchlist.id, asset.symbol)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
