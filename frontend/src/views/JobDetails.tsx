import { useState, useEffect, useCallback, Fragment } from 'react';
import {
  ArrowLeft, RefreshCw, AlertOctagon, CheckCircle2, XCircle,
  ChevronDown, ChevronUp, Copy, Check, Download
} from 'lucide-react';
import { api } from '../api';
import type { Job, JobSummary, Transaction, JobEvent } from '../api';
import styles from './JobDetails.module.css';

interface Props {
  jobId: string;
  onBack: () => void;
}

type Tab = 'overview' | 'timeline' | 'transactions' | 'risk' | 'export';

const STATUS_ACTIVE = new Set(['PENDING', 'PROCESSING', 'LLM_PROCESSING', 'REPORTING']);

function RiskBadge({ level }: { level: 'LOW' | 'MEDIUM' | 'HIGH' | string }) {
  const cls = level === 'HIGH' ? styles.riskHigh : level === 'MEDIUM' ? styles.riskMedium : styles.riskLow;
  return <span className={`${styles.riskBadge} ${cls}`}>{level}</span>;
}

function StatusPill({ status }: { status: string }) {
  const cls =
    status === 'COMPLETED' ? styles.pillSuccess :
    status === 'FAILED'    ? styles.pillDanger  :
                             styles.pillActive;
  return <span className={`${styles.pill} ${cls}`}>{status.replace(/_/g, ' ')}</span>;
}

export const JobDetails = ({ jobId, onBack }: Props) => {
  const [job, setJob]         = useState<Job | null>(null);
  const [summary, setSummary] = useState<JobSummary | null>(null);
  const [events, setEvents]   = useState<JobEvent[]>([]);
  const [txns, setTxns]       = useState<Transaction[]>([]);
  const [totalTxns, setTotalTxns] = useState(0);
  const [tab, setTab]         = useState<Tab>('overview');
  const [txOffset, setTxOffset] = useState(0);
  const [expandedRows, setExpandedRows] = useState<Record<string, boolean>>({});
  const [copied, setCopied]   = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const TX_LIMIT = 25;

  const fetchAll = useCallback(async (showSpinner = false) => {
    if (showSpinner) setLoading(true);
    try {
      // Parallel fetch: details + timeline
      const [details, timeline] = await Promise.all([
        api.getJobDetails(jobId),
        api.getJobTimeline(jobId),
      ]);
      setJob(details.job);
      setSummary(details.summary);
      setEvents(timeline.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()));
      setError(null);
    } catch {
      setError('Failed to load job data.');
    } finally {
      if (showSpinner) setLoading(false);
    }
  }, [jobId]);

  const fetchTxns = useCallback(async () => {
    try {
      const res = await api.getJobResults(jobId, { limit: TX_LIMIT, offset: txOffset });
      setTxns(res.items);
      setTotalTxns(res.total);
    } catch { /* silent */ }
  }, [jobId, txOffset]);

  // Initial load
  useEffect(() => { fetchAll(true); }, [fetchAll]);

  // Fetch transactions when on those tabs
  useEffect(() => {
    if (tab === 'transactions' || tab === 'risk') fetchTxns();
  }, [tab, txOffset, fetchTxns]);

  // Smart polling for active jobs
  useEffect(() => {
    if (!job || !STATUS_ACTIVE.has(job.status)) return;
    const interval = setInterval(() => fetchAll(false), 3000);
    return () => clearInterval(interval);
  }, [job?.status, fetchAll]);

  const copyNarrative = () => {
    if (!summary?.narrative) return;
    navigator.clipboard.writeText(summary.narrative);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const exportCSV = () => {
    if (!txns.length) return;
    const headers = ['Date', 'Merchant', 'Amount', 'Currency', 'Category', 'Status', 'Risk Score', 'Risk Level', 'Is Anomaly'];
    const rows = txns.map(t => [
      t.date, t.merchant, t.amount, t.currency, t.category, t.status, t.risk_score, t.risk_level, t.is_anomaly
    ]);
    const csv = [headers, ...rows].map(r => r.map(v => `"${v}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${job?.filename ?? 'export'}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  const anomalies = txns.filter(t => t.is_anomaly);

  if (loading) return (
    <div className={styles.centered}>
      <RefreshCw size={24} className="animate-spin-fast" style={{ color: 'var(--primary)' }} />
      <p>Loading job…</p>
    </div>
  );

  if (error || !job) return (
    <div className={styles.centered}>
      <XCircle size={32} style={{ color: 'var(--danger)' }} />
      <p>{error ?? 'Job not found.'}</p>
      <button className={styles.backBtn} onClick={onBack}><ArrowLeft size={14} /> Back</button>
    </div>
  );

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'timeline', label: `Timeline (${events.length})` },
    { id: 'transactions', label: `Transactions (${totalTxns || job.row_count_clean || 0})` },
    { id: 'risk', label: `Risk Analysis (${summary?.anomaly_count ?? 0})` },
    { id: 'export', label: 'Export' },
  ];

  return (
    <div className={styles.container}>
      {/* Top bar */}
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={onBack}>
          <ArrowLeft size={14} /> Jobs
        </button>
        <button className={styles.refreshBtn} onClick={() => fetchAll(true)} title="Refresh">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Job header card */}
      <div className={styles.headerCard}>
        <div className={styles.headerLeft}>
          <h2 className={styles.jobName}>{job.filename}</h2>
          <code className={styles.jobId}>{job.id}</code>
        </div>
        <div className={styles.headerRight}>
          <StatusPill status={job.status} />
          {summary?.risk_level && <RiskBadge level={summary.risk_level} />}
        </div>
      </div>

      {/* Tabs */}
      <div className={styles.tabBar}>
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`${styles.tab} ${tab === t.id ? styles.tabActive : ''}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ── OVERVIEW ── */}
      {tab === 'overview' && (
        <div className={styles.panel}>
          {/* Quick stats */}
          <div className={styles.statsRow}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Raw Rows</span>
              <span className={styles.statValue}>{job.row_count_raw?.toLocaleString() ?? '—'}</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>Clean Rows</span>
              <span className={styles.statValue}>{job.row_count_clean?.toLocaleString() ?? '—'}</span>
            </div>
            {summary && (
              <>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Total Spend (INR)</span>
                  <span className={styles.statValue}>₹{Number(summary.total_spend_inr).toLocaleString()}</span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Total Spend (USD)</span>
                  <span className={styles.statValue}>${Number(summary.total_spend_usd).toLocaleString()}</span>
                </div>
                <div className={styles.stat}>
                  <span className={styles.statLabel}>Anomalies</span>
                  <span className={`${styles.statValue} ${summary.anomaly_count > 0 ? styles.danger : ''}`}>
                    {summary.anomaly_count}
                  </span>
                </div>
              </>
            )}
          </div>

          {/* Error message */}
          {job.error_message && (
            <div className={styles.errorBox}>
              <AlertOctagon size={16} />
              <span>{job.error_message}</span>
            </div>
          )}

          {/* AI Narrative */}
          {summary?.narrative ? (
            <div className={styles.narrativeCard}>
              <div className={styles.narrativeHeader}>
                <span className={styles.narrativeTitle}>AI Executive Summary</span>
                <button className={styles.copyBtn} onClick={copyNarrative}>
                  {copied ? <Check size={13} /> : <Copy size={13} />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>
              <p className={styles.narrativeText}>{summary.narrative}</p>
            </div>
          ) : (
            <div className={styles.placeholder}>
              {STATUS_ACTIVE.has(job.status)
                ? 'AI summary is being generated…'
                : 'No AI summary available for this job.'}
            </div>
          )}

          {/* Top merchants */}
          {summary?.top_merchants && summary.top_merchants.length > 0 && (
            <div className={styles.merchantsCard}>
              <span className={styles.cardLabel}>Top Merchants</span>
              <div className={styles.merchantList}>
                {summary.top_merchants.slice(0, 5).map((m: any) => {
                  const max = Number(summary.top_merchants[0]?.total || 1);
                  const pct = (Number(m.total) / max) * 100;
                  return (
                    <div key={m.merchant} className={styles.merchantRow}>
                      <span className={styles.merchantName}>{m.merchant}</span>
                      <div className={styles.barTrack}>
                        <div className={styles.barFill} style={{ width: `${pct}%` }} />
                      </div>
                      <span className={styles.merchantAmount}>₹{Number(m.total).toLocaleString()}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TIMELINE ── */}
      {tab === 'timeline' && (
        <div className={styles.panel}>
          {events.length === 0 ? (
            <div className={styles.placeholder}>No pipeline events recorded.</div>
          ) : (
            <div className={styles.timeline}>
              {events.map((evt, idx) => {
                const failed = evt.event_type.includes('FAILED') || evt.event_type.includes('ERROR');
                return (
                  <div key={evt.id} className={styles.timelineItem}>
                    <div className={styles.timelineLeft}>
                      <div className={`${styles.timelineDot} ${failed ? styles.dotFailed : styles.dotDone}`} />
                      {idx < events.length - 1 && <div className={styles.timelineLine} />}
                    </div>
                    <div className={styles.timelineContent}>
                      <span className={`${styles.evtName} ${failed ? styles.evtFailed : ''}`}>
                        {evt.event_type.replace(/_/g, ' ')}
                      </span>
                      <span className={styles.evtTime}>
                        {new Date(evt.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* ── TRANSACTIONS ── */}
      {tab === 'transactions' && (
        <div className={styles.panel}>
          {txns.length === 0 ? (
            <div className={styles.placeholder}>
              {STATUS_ACTIVE.has(job.status) ? 'Transactions will appear when processing completes.' : 'No transactions found.'}
            </div>
          ) : (
            <>
              <div className={styles.tableWrap}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Merchant</th>
                      <th>Amount</th>
                      <th>Category</th>
                      <th>Status</th>
                      <th>Risk</th>
                    </tr>
                  </thead>
                  <tbody>
                    {txns.map(t => (
                      <tr key={t.id} className={t.is_anomaly ? styles.anomalyRow : ''}>
                        <td className={styles.muted}>{t.date}</td>
                        <td className={styles.bold}>{t.merchant}</td>
                        <td className={styles.mono}>{t.currency} {t.amount.toLocaleString()}</td>
                        <td>{t.category}</td>
                        <td>{t.status}</td>
                        <td>
                          <span style={{
                            color: t.risk_level === 'HIGH' ? 'var(--danger)' : t.risk_level === 'MEDIUM' ? 'var(--warning)' : 'var(--success)',
                            fontWeight: 700, fontSize: '0.8rem'
                          }}>
                            {t.risk_score.toFixed(0)} {t.risk_level}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className={styles.pagination}>
                <button disabled={txOffset === 0} onClick={() => setTxOffset(Math.max(0, txOffset - TX_LIMIT))} className={styles.pageBtn}>
                  Previous
                </button>
                <span className={styles.pageInfo}>
                  {txOffset + 1}–{Math.min(txOffset + TX_LIMIT, totalTxns)} of {totalTxns}
                </span>
                <button disabled={txOffset + TX_LIMIT >= totalTxns} onClick={() => setTxOffset(txOffset + TX_LIMIT)} className={styles.pageBtn}>
                  Next
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── RISK ANALYSIS ── */}
      {tab === 'risk' && (
        <div className={styles.panel}>
          {anomalies.length === 0 ? (
            <div className={styles.cleanState}>
              <CheckCircle2 size={36} style={{ color: 'var(--success)' }} />
              <h3>No anomalies detected</h3>
              <p>All transactions on this page passed risk checks.</p>
            </div>
          ) : (
            <div className={styles.tableWrap}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th></th>
                    <th>Merchant</th>
                    <th>Amount</th>
                    <th>Category</th>
                    <th>Risk Score</th>
                    <th>Signals</th>
                  </tr>
                </thead>
                <tbody>
                  {anomalies.map(t => {
                    const open = !!expandedRows[t.id];
                    return (
                      <Fragment key={t.id}>
                        <tr className={styles.expandableRow} onClick={() => setExpandedRows(p => ({ ...p, [t.id]: !p[t.id] }))}>
                          <td className={styles.expandIcon}>
                            {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </td>
                          <td className={styles.bold}>{t.merchant}</td>
                          <td className={`${styles.mono} ${styles.danger}`}>{t.currency} {t.amount.toLocaleString()}</td>
                          <td>{t.category}</td>
                          <td>
                            <span className={styles.danger} style={{ fontWeight: 700 }}>{t.risk_score.toFixed(0)}</span>
                          </td>
                          <td className={styles.muted}>{t.risk_signals?.length ?? 0} signal{t.risk_signals?.length !== 1 ? 's' : ''}</td>
                        </tr>
                        {open && (
                          <tr>
                            <td colSpan={6} className={styles.expandedCell}>
                              {t.anomaly_reason && (
                                <p className={styles.anomalyReason}>{t.anomaly_reason}</p>
                              )}
                              {t.risk_signals?.length > 0 ? (
                                <div className={styles.signalList}>
                                  {t.risk_signals.map((s, i) => (
                                    <div key={i} className={styles.signalCard}>
                                      <div className={styles.signalHeader}>
                                        <span className={styles.signalType}>{s.signal_type.replace(/_/g, ' ').toUpperCase()}</span>
                                        <span className={styles.signalScore}>Score: {s.signal_score.toFixed(0)}</span>
                                      </div>
                                      <p className={styles.signalDesc}>{s.description}</p>
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <p className={styles.muted} style={{ fontSize: '0.75rem' }}>No granular signals stored.</p>
                              )}
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── EXPORT ── */}
      {tab === 'export' && (
        <div className={styles.panel}>
          <div className={styles.exportCard}>
            <Download size={28} style={{ color: 'var(--text-muted)' }} />
            <div>
              <h3 className={styles.exportTitle}>Export Transactions</h3>
              <p className={styles.exportDesc}>
                Download all transactions for <strong>{job.filename}</strong> as CSV.
                Currently showing {txns.length} of {totalTxns} records (current page).
              </p>
            </div>
            <button className={styles.exportBtn} onClick={exportCSV} disabled={txns.length === 0}>
              <Download size={15} />
              Download CSV
            </button>
          </div>
          <p className={styles.exportNote}>
            To export all transactions, navigate to the <strong>Transactions</strong> page and use the export button there for the full dataset.
          </p>
        </div>
      )}
    </div>
  );
};
