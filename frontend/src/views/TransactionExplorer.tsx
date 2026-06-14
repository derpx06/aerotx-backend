import { useState, useEffect, useCallback } from 'react';
import { 
  Search, 
  SlidersHorizontal, 
  Download, 
  X, 
  Eye, 
  ShieldAlert, 
  TrendingUp, 
  FileSpreadsheet
} from 'lucide-react';
import { api } from '../api';
import type { Transaction } from '../api';
import styles from './TransactionExplorer.module.css';

const LIMIT = 50;

const CATEGORIES = ['Food', 'Shopping', 'Travel', 'Transport', 'Utilities', 'Cash Withdrawal', 'Entertainment', 'Other', 'Uncategorised'];
const CURRENCIES = ['INR', 'USD', 'EUR', 'GBP', 'AED', 'SGD'];
const RISK_LEVELS = ['LOW', 'MEDIUM', 'HIGH'];

export default function TransactionExplorer() {
  const [items, setItems]     = useState<Transaction[]>([]);
  const [total, setTotal]     = useState(0);
  const [offset, setOffset]   = useState(0);
  const [loading, setLoading] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [showColMenu, setShowColMenu] = useState(false);

  // Search & Filters state
  const [search, setSearch]         = useState('');
  const [category, setCategory]     = useState('');
  const [currency, setCurrency]     = useState('');
  const [riskLevel, setRiskLevel]   = useState('');
  const [minAmount, setMinAmount]   = useState('');
  const [maxAmount, setMaxAmount]   = useState('');

  // Row selection & drawer state
  const [selectedRowIds, setSelectedRowIds] = useState<Set<string>>(new Set());
  const [activeTxn, setActiveTxn]           = useState<Transaction | null>(null);

  // Column visibility state
  const [cols, setCols] = useState({
    date: true,
    merchant: true,
    amount: true,
    currency: true,
    category: true,
    status: true,
    riskScore: true,
    riskLevel: true,
  });

  const activeFilterCount = [category, currency, riskLevel, minAmount, maxAmount].filter(Boolean).length;

  const fetch = useCallback(async (off = offset) => {
    setLoading(true);
    try {
      const res = await api.getGlobalTransactions({
        limit: LIMIT,
        offset: off,
        search: search || undefined,
        category: category || undefined,
        currency: currency || undefined,
        risk_level: riskLevel || undefined,
        min_amount: minAmount ? Number(minAmount) : undefined,
        max_amount: maxAmount ? Number(maxAmount) : undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [offset, search, category, currency, riskLevel, minAmount, maxAmount]);

  useEffect(() => { fetch(offset); }, [offset, category, currency, riskLevel, minAmount, maxAmount]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    fetch(0);
  };

  const clearFilters = () => {
    setCategory(''); 
    setCurrency(''); 
    setRiskLevel('');
    setMinAmount(''); 
    setMaxAmount('');
    setSearch('');
    setOffset(0);
  };

  // Predefined Saved Filter Pills
  const applySavedFilter = (type: 'high_risk' | 'failed' | 'usd' | 'large') => {
    clearFilters();
    if (type === 'high_risk') {
      setRiskLevel('HIGH');
    } else if (type === 'failed') {
      // API doesn't support direct status filter, so we set search/filters accordingly
      setSearch('FAILED');
    } else if (type === 'usd') {
      setCurrency('USD');
    } else if (type === 'large') {
      setMinAmount('1000');
    }
    setOffset(0);
  };

  // Selection logic
  const handleToggleRow = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const next = new Set(selectedRowIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedRowIds(next);
  };

  const handleToggleAll = () => {
    if (selectedRowIds.size === items.length) {
      setSelectedRowIds(new Set());
    } else {
      setSelectedRowIds(new Set(items.map(t => t.id)));
    }
  };

  // Export options
  const exportToCSV = (transactionsToExport: Transaction[]) => {
    if (!transactionsToExport.length) return;
    const headers = ['Date', 'Merchant', 'Amount', 'Currency', 'Category', 'Status', 'Risk Score', 'Risk Level', 'Anomaly Reason'];
    const rows = transactionsToExport.map(t => [
      t.date, 
      t.merchant, 
      t.amount, 
      t.currency, 
      t.category, 
      t.status, 
      t.risk_score, 
      t.risk_level, 
      t.anomaly_reason || ''
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `aerotx_export_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  const handleExportSelected = () => {
    const selected = items.filter(t => selectedRowIds.has(t.id));
    exportToCSV(selected);
  };

  const handleExportFiltered = () => {
    exportToCSV(items);
  };

  const toggleCol = (key: keyof typeof cols) => {
    setCols(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className={styles.container}>
      {/* 1. Saved Filters Quickbar */}
      <div className={styles.savedFiltersRow}>
        <span className={styles.savedTitle}>Saved Queries:</span>
        <button className={styles.savedPill} onClick={() => applySavedFilter('high_risk')}>
          <ShieldAlert size={12} style={{ color: 'var(--danger)' }} />
          <span>High Risk Anomaly Triggers</span>
        </button>
        <button className={styles.savedPill} onClick={() => applySavedFilter('failed')}>
          <X size={12} style={{ color: 'var(--danger)' }} />
          <span>Failed Runs</span>
        </button>
        <button className={styles.savedPill} onClick={() => applySavedFilter('usd')}>
          <TrendingUp size={12} style={{ color: 'var(--success)' }} />
          <span>USD Transactions</span>
        </button>
        <button className={styles.savedPill} onClick={() => applySavedFilter('large')}>
          <FileSpreadsheet size={12} style={{ color: 'var(--primary-hover)' }} />
          <span>Large Orders (&gt;$1k)</span>
        </button>
        {(activeFilterCount > 0 || search) && (
          <button className={styles.resetFiltersBtn} onClick={clearFilters}>
            Reset Query
          </button>
        )}
      </div>

      {/* 2. Grid Control Toolbar */}
      <div className={styles.toolbar}>
        <form onSubmit={handleSearch} className={styles.searchForm}>
          <Search size={14} className={styles.searchIcon} />
          <input
            className={styles.searchInput}
            type="text"
            placeholder="Search account, category, merchant name..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          {search && (
            <button type="button" className={styles.clearSearch} onClick={() => { setSearch(''); setOffset(0); fetch(0); }}>
              <X size={12} />
            </button>
          )}
        </form>

        <div className={styles.actionButtonGroup}>
          {/* Column toggles */}
          <div className={styles.colToggleWrapper}>
            <button className={styles.btn} onClick={() => setShowColMenu(!showColMenu)}>
              <Eye size={14} />
              <span>Columns</span>
            </button>
            {showColMenu && (
              <div className={styles.colDropdown}>
                {Object.keys(cols).map(k => {
                  const key = k as keyof typeof cols;
                  const active = cols[key];
                  return (
                    <label key={key} className={styles.colLabel}>
                      <input type="checkbox" checked={active} onChange={() => toggleCol(key)} />
                      <span>{key.charAt(0).toUpperCase() + key.slice(1)}</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>

          <button
            className={`${styles.btn} ${showFilters ? styles.btnActive : ''}`}
            onClick={() => setShowFilters(v => !v)}
          >
            <SlidersHorizontal size={14} />
            <span>Filters</span>
            {activeFilterCount > 0 && <span className={styles.filterCount}>{activeFilterCount}</span>}
          </button>

          <button className={styles.btn} onClick={handleExportFiltered} disabled={!items.length}>
            <Download size={14} />
            <span>Export Query</span>
          </button>
        </div>
      </div>

      {/* 3. Advanced Search Expandable Panel */}
      {showFilters && (
        <div className={styles.filterPanel}>
          <div className={styles.filterGrid}>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Category</label>
              <select className={styles.select} value={category} onChange={e => { setCategory(e.target.value); setOffset(0); }}>
                <option value="">All Categories</option>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Currency</label>
              <select className={styles.select} value={currency} onChange={e => { setCurrency(e.target.value); setOffset(0); }}>
                <option value="">All Currencies</option>
                {CURRENCIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Risk Severity</label>
              <select className={styles.select} value={riskLevel} onChange={e => { setRiskLevel(e.target.value); setOffset(0); }}>
                <option value="">All Severities</option>
                {RISK_LEVELS.map(r => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Minimum Amount</label>
              <input className={styles.input} type="number" placeholder="Min val" value={minAmount} onChange={e => { setMinAmount(e.target.value); setOffset(0); }} />
            </div>
            <div className={styles.filterGroup}>
              <label className={styles.filterLabel}>Maximum Amount</label>
              <input className={styles.input} type="number" placeholder="Max val" value={maxAmount} onChange={e => { setMaxAmount(e.target.value); setOffset(0); }} />
            </div>
          </div>
        </div>
      )}

      {/* Bulk actions floating status */}
      {selectedRowIds.size > 0 && (
        <div className={styles.bulkBanner}>
          <div className={styles.bulkLeft}>
            <span>Selected {selectedRowIds.size} records for batch operation</span>
          </div>
          <div className={styles.bulkRight}>
            <button className={styles.bulkExportBtn} onClick={handleExportSelected}>
              <Download size={13} />
              <span>Export Batch</span>
            </button>
            <button className={styles.bulkClearBtn} onClick={() => setSelectedRowIds(new Set())}>
              Deselect All
            </button>
          </div>
        </div>
      )}

      {/* 4. Data Grid */}
      <div className={styles.tableCard}>
        {loading ? (
          <div className={styles.tableLoader}>
            <div className={`${styles.spinner} animate-spin-fast`} />
            <span>Polling transaction records...</span>
          </div>
        ) : items.length === 0 ? (
          <div className={styles.empty}>
            <Search size={32} />
            <h4>No transaction records found</h4>
            <p>Modify your filter query parameters or launch a new CSV task run.</p>
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th className={styles.checkboxCell}>
                  <input 
                    type="checkbox" 
                    checked={selectedRowIds.size === items.length} 
                    onChange={handleToggleAll} 
                  />
                </th>
                {cols.date && <th>Date</th>}
                {cols.merchant && <th>Merchant</th>}
                {cols.amount && <th className={styles.numAlign}>Amount</th>}
                {cols.currency && <th>Currency</th>}
                {cols.category && <th>Category</th>}
                {cols.status && <th>Status</th>}
                {cols.riskScore && <th className={styles.numAlign}>Risk Score</th>}
                {cols.riskLevel && <th>Severity</th>}
              </tr>
            </thead>
            <tbody>
              {items.map(t => {
                const isSelected = selectedRowIds.has(t.id);
                return (
                  <tr
                    key={t.id}
                    className={`${styles.row} ${t.is_anomaly ? styles.anomalyRow : ''} ${isSelected ? styles.rowSelected : ''} ${activeTxn?.id === t.id ? styles.rowActive : ''}`}
                    onClick={() => setActiveTxn(t)}
                  >
                    <td className={styles.checkboxCell} onClick={e => e.stopPropagation()}>
                      <input 
                        type="checkbox" 
                        checked={isSelected} 
                        onChange={ev => handleToggleRow(t.id, ev as any)} 
                      />
                    </td>
                    {cols.date && <td className={styles.dateCell}>{t.date}</td>}
                    {cols.merchant && <td className={styles.boldCell}>{t.merchant}</td>}
                    {cols.amount && (
                      <td className={`${styles.mono} ${styles.numAlign}`}>
                        {t.amount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                    )}
                    {cols.currency && <td><span className={styles.currencyPill}>{t.currency}</span></td>}
                    {cols.category && <td><span className={styles.categoryPill}>{t.category}</span></td>}
                    {cols.status && (
                      <td>
                        <span className={`${styles.statusPill} ${
                          t.status === 'COMPLETED' ? styles.pillOk :
                          t.status === 'FAILED' ? styles.pillFail :
                          styles.pillNeutral
                        }`}>{t.status}</span>
                      </td>
                    )}
                    {cols.riskScore && (
                      <td className={`${styles.mono} ${styles.numAlign}`} style={{
                        color: t.risk_level === 'HIGH' ? 'var(--danger)' : t.risk_level === 'MEDIUM' ? 'var(--warning)' : 'var(--success)',
                        fontWeight: 700
                      }}>
                        {t.risk_score.toFixed(0)}
                      </td>
                    )}
                    {cols.riskLevel && (
                      <td>
                        <span className={`${styles.riskPill} ${
                          t.risk_level === 'HIGH' ? styles.riskHigh : t.risk_level === 'MEDIUM' ? styles.riskMed : styles.riskLow
                        }`}>{t.risk_level}</span>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination control */}
      {total > LIMIT && (
        <div className={styles.pager}>
          <button className={styles.pageBtn} disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - LIMIT))}>← Prev</button>
          <span className={styles.pageInfo}>Records {offset + 1}–{Math.min(offset + LIMIT, total)} of {total.toLocaleString()}</span>
          <button className={styles.pageBtn} disabled={offset + LIMIT >= total} onClick={() => setOffset(offset + LIMIT)}>Next →</button>
        </div>
      )}

      {/* 5. Detail Slide-out Drawer */}
      {activeTxn && (
        <div className={styles.drawerOverlay} onClick={() => setActiveTxn(null)}>
          <div className={styles.drawer} onClick={e => e.stopPropagation()}>
            <div className={styles.drawerHeader}>
              <div className={styles.drawerTitleGroup}>
                <h4>Transaction Insights</h4>
                <code className={styles.drawerUuid}>{activeTxn.id}</code>
              </div>
              <button className={styles.drawerCloseBtn} onClick={() => setActiveTxn(null)}>
                <X size={16} />
              </button>
            </div>

            <div className={styles.drawerBody}>
              {/* Highlight summary card */}
              <div className={styles.drawerSummaryCard}>
                <div className={styles.drawerAmountRow}>
                  <span className={styles.drawerValAmount}>{activeTxn.currency} {activeTxn.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
                  <span className={`${styles.riskPill} ${
                    activeTxn.risk_level === 'HIGH' ? styles.riskHigh : activeTxn.risk_level === 'MEDIUM' ? styles.riskMed : styles.riskLow
                  }`}>{activeTxn.risk_level} Severity</span>
                </div>
                <div className={styles.drawerValMerchant}>{activeTxn.merchant}</div>
                <div className={styles.drawerValDate}>Recorded on {activeTxn.date}</div>
              </div>

              {/* Status and pipeline details */}
              <div className={styles.drawerGroup}>
                <h5>Ingestion & Process State</h5>
                <div className={styles.propertiesGrid}>
                  <div className={styles.propertyItem}>
                    <span className={styles.propLabel}>Cleansing Status</span>
                    <span className={styles.propVal}>
                      <span className={`${styles.statusPill} ${activeTxn.status === 'COMPLETED' ? styles.pillOk : styles.pillFail}`}>
                        {activeTxn.status}
                      </span>
                    </span>
                  </div>
                  <div className={styles.propertyItem}>
                    <span className={styles.propLabel}>Is Anomaly flagged</span>
                    <span className={`${styles.propVal} ${activeTxn.is_anomaly ? styles.textAnomaly : styles.textClean}`}>
                      {activeTxn.is_anomaly ? 'FLAGGED ANOMALY' : 'CLEANSED'}
                    </span>
                  </div>
                  <div className={styles.propertyItem}>
                    <span className={styles.propLabel}>Account Reference ID</span>
                    <code className={styles.propCode}>{activeTxn.account_id}</code>
                  </div>
                  <div className={styles.propertyItem}>
                    <span className={styles.propLabel}>External Transaction ID</span>
                    <code className={styles.propCode}>{activeTxn.txn_id || 'Not specified'}</code>
                  </div>
                </div>
              </div>

              {/* Anomaly Reason */}
              {activeTxn.is_anomaly && activeTxn.anomaly_reason && (
                <div className={styles.drawerGroup} style={{ backgroundColor: 'rgba(239, 68, 68, 0.03)', border: '1px dashed rgba(239, 68, 68, 0.2)', padding: '12px', borderRadius: '4px' }}>
                  <h5 style={{ color: 'var(--danger)', marginTop: 0 }}>Anomaly trigger reason</h5>
                  <p className={styles.anomalyReasonText}>{activeTxn.anomaly_reason}</p>
                </div>
              )}

              {/* Risk Scoring & Heuristics */}
              <div className={styles.drawerGroup}>
                <h5>Risk Signal Heuristics</h5>
                <div className={styles.riskMeterSection}>
                  <div className={styles.riskGauge}>
                    <span className={styles.gaugeVal}>{activeTxn.risk_score.toFixed(0)}</span>
                    <span className={styles.gaugeLabel}>Risk Index</span>
                  </div>
                  <p className={styles.riskMeterDesc}>
                    Computed using strategy deviation checks. High values trigger audits.
                  </p>
                </div>

                {activeTxn.risk_signals && activeTxn.risk_signals.length > 0 ? (
                  <div className={styles.signalLogList}>
                    {activeTxn.risk_signals.map((s, i) => (
                      <div key={i} className={styles.signalLogCard}>
                        <div className={styles.signalLogTop}>
                          <span className={styles.signalTypeName}>{s.signal_type.replace(/_/g, ' ')}</span>
                          <span className={styles.signalScoreVal} style={{
                            color: s.signal_score > 60 ? 'var(--danger)' : 'var(--warning)'
                          }}>
                            Score: {s.signal_score}
                          </span>
                        </div>
                        <p className={styles.signalLogDesc}>{s.description}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className={styles.noSignalsMsg}>
                    No anomalies or heuristic strategy matches found for this transaction.
                  </div>
                )}
              </div>

              {/* Notes */}
              {activeTxn.notes && (
                <div className={styles.drawerGroup}>
                  <h5>Metadata Notes</h5>
                  <p className={styles.notesText}>{activeTxn.notes}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
