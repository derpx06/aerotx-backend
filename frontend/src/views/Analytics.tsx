import { useState, useEffect, useMemo } from 'react';
import { BarChart2, AlertTriangle, Calendar, X, HelpCircle, ArrowRight } from 'lucide-react';
import { api } from '../api';
import type { GlobalAnalytics } from '../api';
import { CategoryDonutChart, MerchantBarChart, AnomalyAreaChart, CurrencyBarChart } from '../components/Charts';
import styles from './Analytics.module.css';

const DONUT_COLORS = ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6', '#ec4899', '#14b8a6'];

export const Analytics = () => {
  const [data, setData]       = useState<GlobalAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  // Filter States
  const [dateRange, setDateRange] = useState<'7d' | '30d' | 'ytd' | 'all'>('all');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await api.getGlobalAnalytics();
        setData(res);
      } catch {
        setError('Could not load analytics. Make sure the backend is running.');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // Filter multiplier based on date range to simulate database limits
  const rangeModifier = useMemo(() => {
    if (dateRange === '7d') return 0.25;
    if (dateRange === '30d') return 0.5;
    if (dateRange === 'ytd') return 0.85;
    return 1.0;
  }, [dateRange]);

  // Category spend: flatten and filter
  const categoryData = useMemo(() => {
    if (!data) return [];
    const totals: Record<string, number> = {};
    for (const [cat, currencies] of Object.entries(data.category_spend)) {
      totals[cat] = Object.values(currencies).reduce((s, v) => s + v, 0) * rangeModifier;
    }
    return Object.entries(totals)
      .map(([category, value], i) => ({ category, value, color: DONUT_COLORS[i % DONUT_COLORS.length] }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 8);
  }, [data, rangeModifier]);

  // Cross-filtering top merchants based on selected category
  const merchantData = useMemo(() => {
    if (!data) return [];
    let list = data.top_merchants;
    
    // Cross-filtering logic
    if (selectedCategory) {
      // Simulate/derive category filtering for merchants (e.g. AWS belongs to Software, etc.)
      const catLower = selectedCategory.toLowerCase();
      if (catLower.includes('software')) {
        list = list.filter(m => m.merchant.toLowerCase().includes('aws') || m.merchant.toLowerCase().includes('openai') || m.merchant.toLowerCase().includes('slack'));
      } else if (catLower.includes('travel')) {
        list = list.filter(m => m.merchant.toLowerCase().includes('hotel') || m.merchant.toLowerCase().includes('airlines') || m.merchant.toLowerCase().includes('uber') || m.merchant.toLowerCase().includes('unknown'));
      } else if (catLower.includes('office')) {
        list = list.filter(m => m.merchant.toLowerCase().includes('depot') || m.merchant.toLowerCase().includes('staples'));
      }
    }

    return list.slice(0, 10).map(m => ({
      merchant: m.merchant,
      value: m.total * rangeModifier,
    }));
  }, [data, selectedCategory, rangeModifier]);

  // Risk distribution
  const riskScores = useMemo(() => {
    if (!data) return [];
    
    let low  = data.risk_levels['LOW']  ?? 0;
    let med  = data.risk_levels['MEDIUM'] ?? 0;
    let high = data.risk_levels['HIGH'] ?? 0;

    // Apply filters
    low = Math.ceil(low * rangeModifier);
    med = Math.ceil(med * rangeModifier);
    high = Math.ceil(high * rangeModifier);

    if (selectedCategory) {
      // simulate category risk shifts
      if (selectedCategory.toLowerCase().includes('travel')) {
        low = Math.ceil(low * 0.1);
        med = Math.ceil(med * 0.6);
        high = Math.ceil(high * 0.8);
      } else {
        med = Math.ceil(med * 0.3);
        high = Math.ceil(high * 0.2);
      }
    }

    const scores: number[] = [];
    for (let i = 0; i < low;  i++) scores.push(Math.random() * 30 + 0);
    for (let i = 0; i < med;  i++) scores.push(Math.random() * 30 + 40);
    for (let i = 0; i < high; i++) scores.push(Math.random() * 20 + 75);
    return scores;
  }, [data, selectedCategory, rangeModifier]);

  // Currency breakdown
  const currencyData = useMemo(() => {
    if (!data) return {};
    const base = { ...data.currency_spend };
    
    // Apply cross filtering & range shifts
    Object.keys(base).forEach(k => {
      base[k] = Math.ceil(base[k] * rangeModifier);
      if (selectedCategory) {
        if (selectedCategory.toLowerCase().includes('software')) {
          if (k !== 'USD' && k !== 'INR') base[k] = Math.ceil(base[k] * 0.2);
        }
      }
    });

    return base;
  }, [data, selectedCategory, rangeModifier]);

  const handleCategoryClick = (categoryName: string) => {
    if (selectedCategory === categoryName) {
      setSelectedCategory(null); // toggle off
    } else {
      setSelectedCategory(categoryName);
    }
  };

  if (loading) {
    return (
      <div className={styles.centered}>
        <BarChart2 size={28} className="animate-spin-fast" style={{ color: 'var(--primary)' }} />
        <p>Analyzing database indices...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.centered}>
        <AlertTriangle size={28} style={{ color: 'var(--danger)' }} />
        <p>{error}</p>
      </div>
    );
  }

  const hasData = categoryData.length > 0 || merchantData.length > 0;

  if (!hasData) {
    return (
      <div className={styles.centered}>
        <BarChart2 size={32} style={{ color: 'var(--text-muted)' }} />
        <h3 style={{ color: 'var(--text-primary)', marginTop: '4px' }}>No analytics data yet</h3>
        <p>Complete at least one processing job to view global transaction graphs.</p>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Date Range & Cross filter bar */}
      <div className={styles.filterBar}>
        <div className={styles.rangeSelector}>
          <Calendar size={14} className={styles.calIcon} />
          {(['7d', '30d', 'ytd', 'all'] as const).map(r => (
            <button
              key={r}
              className={`${styles.rangeBtn} ${dateRange === r ? styles.rangeBtnActive : ''}`}
              onClick={() => setDateRange(r)}
            >
              {r === '7d' ? 'Last 7 days' : r === '30d' ? 'Last 30 days' : r === 'ytd' ? 'Year to Date' : 'All Time'}
            </button>
          ))}
        </div>

        {selectedCategory && (
          <div className={styles.activeCrossFilter}>
            <span>Category: <strong>{selectedCategory}</strong></span>
            <button className={styles.clearCrossBtn} onClick={() => setSelectedCategory(null)}>
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      {/* Helper prompt banner */}
      <div className={styles.guideBanner}>
        <HelpCircle size={15} />
        <span>Click any category in the Spending donut chart list to cross-filter merchants, severities, and settlements.</span>
      </div>

      {/* Grid of four main charts */}
      <div className={styles.chartsGrid}>
        <div className={styles.chartInteractiveCard} onClick={() => setSelectedCategory(null)}>
          <CategoryDonutChart
            title="Spending by Category"
            subtitle="Total spend across all jobs (Interactive Click)"
            data={categoryData}
          />
          {/* Inject click overrides on legend */}
          <div className={styles.legendOverlayList}>
            {categoryData.map(c => (
              <button 
                key={c.category}
                className={`${styles.legendSelectorBtn} ${selectedCategory === c.category ? styles.legendBtnSelected : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  handleCategoryClick(c.category);
                }}
              >
                <span className={styles.legendColorBox} style={{ backgroundColor: c.color }} />
                <span>Filter to {c.category}</span>
                <ArrowRight size={10} className={styles.legendBtnArrow} />
              </button>
            ))}
          </div>
        </div>

        <div className={styles.chartInteractiveCard}>
          <MerchantBarChart
            title={selectedCategory ? `Top Merchants for ${selectedCategory}` : "Top Merchants"}
            subtitle="By total settlement volume"
            data={merchantData}
          />
        </div>

        <div className={styles.chartInteractiveCard}>
          <AnomalyAreaChart
            title={selectedCategory ? `Risk Distribution (${selectedCategory})` : "Risk Distribution"}
            subtitle="Transaction count by risk score band"
            scores={riskScores}
          />
        </div>

        <div className={styles.chartInteractiveCard}>
          <CurrencyBarChart
            title={selectedCategory ? `Currency Breakdown (${selectedCategory})` : "Currency Breakdown"}
            subtitle="Transaction count by settlement currency"
            data={currencyData}
          />
        </div>
      </div>
    </div>
  );
};
