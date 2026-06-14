import React, { useState } from 'react';
import styles from './Charts.module.css';

interface TooltipState {
  x: number;
  y: number;
  label: string;
  value: string;
  show: boolean;
}

// ----------------------------------------------------
// 1. CATEGORY DONUT CHART
// ----------------------------------------------------
interface DonutData {
  category: string;
  value: number;
  color: string;
}

interface CategoryDonutChartProps {
  title: string;
  subtitle: string;
  data: DonutData[];
}

export const CategoryDonutChart: React.FC<CategoryDonutChartProps> = ({ title, subtitle, data }) => {
  const [tooltip, setTooltip] = useState<TooltipState>({ x: 0, y: 0, label: '', value: '', show: false });
  const total = data.reduce((sum, item) => sum + item.value, 0);

  let accumulatedAngle = 0;

  return (
    <div className={styles.chartContainer}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>{title}</span>
        <span className={styles.chartSubtitle}>{subtitle}</span>
      </div>

      <div className={styles.chartContent}>
        {tooltip.show && (
          <div
            className={styles.tooltip}
            style={{ left: `${tooltip.x + 10}px`, top: `${tooltip.y - 40}px` }}
          >
            <span className={styles.tooltipLabel}>{tooltip.label}</span>
            <span className={styles.tooltipValue}>{tooltip.value}</span>
          </div>
        )}

        <svg width="200" height="200" viewBox="0 0 200 200">
          <circle cx="100" cy="100" r="70" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="24" />
          {data.map((item) => {
            const percentage = total > 0 ? item.value / total : 0;
            const strokeDash = percentage * 439.8; // 2 * PI * r (r=70)
            const strokeOffset = 439.8 - strokeDash + accumulatedAngle;
            accumulatedAngle -= strokeDash;

            return (
              <circle
                key={item.category}
                cx="100"
                cy="100"
                r="70"
                className={styles.donutSegment}
                stroke={item.color}
                strokeWidth="24"
                strokeDasharray={`${strokeDash} 439.8`}
                strokeDashoffset={strokeOffset}
                strokeLinecap="round"
                transform="rotate(-90 100 100)"
                onMouseMove={(e) => {
                  const rect = e.currentTarget.parentElement?.getBoundingClientRect();
                  if (rect) {
                    setTooltip({
                      x: e.clientX - rect.left,
                      y: e.clientY - rect.top,
                      label: item.category,
                      value: `₹${item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })} (${(percentage * 100).toFixed(1)}%)`,
                      show: true,
                    });
                  }
                }}
                onMouseLeave={() => setTooltip(prev => ({ ...prev, show: false }))}
              />
            );
          })}
          <text x="100" y="96" textAnchor="middle" fill="var(--text-secondary)" fontSize="10" fontWeight="600">TOTAL SPEND</text>
          <text x="100" y="116" textAnchor="middle" fill="var(--text-primary)" fontSize="14" fontWeight="800">
            ₹{total.toLocaleString(undefined, { maximumFractionDigits: 0 })}
          </text>
        </svg>
      </div>

      <div className={styles.legend}>
        {data.map((item) => (
          <div key={item.category} className={styles.legendItem}>
            <span className={styles.legendDot} style={{ backgroundColor: item.color }} />
            <span>{item.category}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ----------------------------------------------------
// 2. MERCHANT BAR CHART (HORIZONTAL)
// ----------------------------------------------------
interface MerchantBarChartProps {
  title: string;
  subtitle: string;
  data: { merchant: string; value: number }[];
}

export const MerchantBarChart: React.FC<MerchantBarChartProps> = ({ title, subtitle, data }) => {
  const [tooltip, setTooltip] = useState<TooltipState>({ x: 0, y: 0, label: '', value: '', show: false });
  const maxValue = Math.max(...data.map(d => d.value), 1);

  return (
    <div className={styles.chartContainer}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>{title}</span>
        <span className={styles.chartSubtitle}>{subtitle}</span>
      </div>

      <div className={styles.chartContent} style={{ flexDirection: 'column', justifyContent: 'flex-start', gap: '12px' }}>
        {tooltip.show && (
          <div
            className={styles.tooltip}
            style={{ left: `${tooltip.x + 10}px`, top: `${tooltip.y - 45}px` }}
          >
            <span className={styles.tooltipLabel}>{tooltip.label}</span>
            <span className={styles.tooltipValue}>{tooltip.value}</span>
          </div>
        )}

        {data.map((item) => {
          const ratio = item.value / maxValue;
          return (
            <div
              key={item.merchant}
              style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '4px' }}
              onMouseMove={(e) => {
                const rect = e.currentTarget.parentElement?.getBoundingClientRect();
                if (rect) {
                  setTooltip({
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                    label: item.merchant,
                    value: `₹${item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
                    show: true,
                  });
                }
              }}
              onMouseLeave={() => setTooltip(prev => ({ ...prev, show: false }))}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 500 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{item.merchant}</span>
                <span style={{ color: 'var(--text-primary)' }}>₹{item.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
              </div>
              <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--border-color)', borderRadius: '4px', overflow: 'hidden' }}>
                <div
                  style={{
                    width: `${ratio * 100}%`,
                    height: '100%',
                    background: 'linear-gradient(90deg, var(--primary), var(--primary-hover))',
                    borderRadius: '4px',
                    transition: 'width var(--transition-slow)',
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ----------------------------------------------------
// 3. ANOMALY RISK DISTRIBUTION (AREA CHART)
// ----------------------------------------------------
interface AnomalyAreaChartProps {
  title: string;
  subtitle: string;
  scores: number[]; // Array of scores from 0-100
}

export const AnomalyAreaChart: React.FC<AnomalyAreaChartProps> = ({ title, subtitle, scores }) => {
  const [tooltip, setTooltip] = useState<TooltipState>({ x: 0, y: 0, label: '', value: '', show: false });

  // Group scores into buckets: 0-19, 20-39, 40-59, 60-79, 80-100
  const buckets = ['Low (0-20)', 'Med-Low (21-40)', 'Medium (41-60)', 'High (61-80)', 'Critical (81-100)'];
  const bucketCounts = [0, 0, 0, 0, 0];
  scores.forEach(s => {
    if (s < 20) bucketCounts[0]++;
    else if (s < 40) bucketCounts[1]++;
    else if (s < 60) bucketCounts[2]++;
    else if (s < 80) bucketCounts[3]++;
    else bucketCounts[4]++;
  });

  const maxCount = Math.max(...bucketCounts, 1);
  const width = 300;
  const height = 150;
  const padding = 20;

  // Generate SVG path points
  const points = bucketCounts.map((count, idx) => {
    const x = padding + (idx * (width - 2 * padding)) / (bucketCounts.length - 1);
    const y = height - padding - (count / maxCount) * (height - 2 * padding);
    return { x, y, count, label: buckets[idx] };
  });

  const pathD = points.reduce((acc, p, idx) => {
    return acc + `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`;
  }, '');

  const areaD = pathD + ` L ${points[points.length - 1].x} ${height - padding} L ${points[0].x} ${height - padding} Z`;

  return (
    <div className={styles.chartContainer}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>{title}</span>
        <span className={styles.chartSubtitle}>{subtitle}</span>
      </div>

      <div className={styles.chartContent}>
        {tooltip.show && (
          <div
            className={styles.tooltip}
            style={{ left: `${tooltip.x + 10}px`, top: `${tooltip.y - 40}px` }}
          >
            <span className={styles.tooltipLabel}>{tooltip.label}</span>
            <span className={styles.tooltipValue}>{tooltip.value}</span>
          </div>
        )}

        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
          {/* Grid lines */}
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border-color)" />
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} className={styles.gridLine} />
          <line x1={padding} y1={(height) / 2} x2={width - padding} y2={(height) / 2} className={styles.gridLine} />

          {/* Area fill */}
          <path d={areaD} fill="url(#purpleGlow)" opacity="0.2" />

          {/* Line path */}
          <path d={pathD} fill="none" stroke="var(--primary)" strokeWidth="2.5" />

          {/* Gradient definitions */}
          <defs>
            <linearGradient id="purpleGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--primary)" />
              <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
            </linearGradient>
          </defs>

          {/* Interactive dots */}
          {points.map((p, idx) => (
            <circle
              key={idx}
              cx={p.x}
              cy={p.y}
              r="5"
              fill="var(--bg-card)"
              stroke="var(--primary-hover)"
              strokeWidth="2"
              style={{ cursor: 'pointer', transition: 'r 0.15s ease' }}
              onMouseMove={(e) => {
                const rect = e.currentTarget.parentElement?.getBoundingClientRect();
                if (rect) {
                  setTooltip({
                    x: e.clientX - rect.left,
                    y: e.clientY - rect.top,
                    label: p.label,
                    value: `${p.count} Transactions`,
                    show: true,
                  });
                }
              }}
              onMouseLeave={() => setTooltip(prev => ({ ...prev, show: false }))}
            />
          ))}

          {/* Axis Labels */}
          <text x={padding} y={height - 4} className={styles.axisText} textAnchor="start">Low Risk</text>
          <text x={width - padding} y={height - 4} className={styles.axisText} textAnchor="end">Critical Risk</text>
        </svg>
      </div>
    </div>
  );
};

// ----------------------------------------------------
// 4. CURRENCY DISTRIBUTION (VERTICAL BARS)
// ----------------------------------------------------
interface CurrencyBarChartProps {
  title: string;
  subtitle: string;
  data: Record<string, number>;
}

export const CurrencyBarChart: React.FC<CurrencyBarChartProps> = ({ title, subtitle, data }) => {
  const [tooltip, setTooltip] = useState<TooltipState>({ x: 0, y: 0, label: '', value: '', show: false });
  const entries = Object.entries(data);
  const maxValue = Math.max(...entries.map(e => e[1]), 1);

  const width = 300;
  const height = 150;
  const padding = 20;
  const barWidth = 36;
  const gap = 20;

  return (
    <div className={styles.chartContainer}>
      <div className={styles.chartHeader}>
        <span className={styles.chartTitle}>{title}</span>
        <span className={styles.chartSubtitle}>{subtitle}</span>
      </div>

      <div className={styles.chartContent}>
        {tooltip.show && (
          <div
            className={styles.tooltip}
            style={{ left: `${tooltip.x + 10}px`, top: `${tooltip.y - 40}px` }}
          >
            <span className={styles.tooltipLabel}>{tooltip.label}</span>
            <span className={styles.tooltipValue}>{tooltip.value}</span>
          </div>
        )}

        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border-color)" />

          {entries.map(([currency, count], idx) => {
            const barHeight = (count / maxValue) * (height - 2 * padding);
            const x = padding + idx * (barWidth + gap) + 20;
            const y = height - padding - barHeight;

            return (
              <g key={currency}>
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  rx="4"
                  className={styles.bar}
                  onMouseMove={(e) => {
                    const rect = e.currentTarget.parentElement?.parentElement?.getBoundingClientRect();
                    if (rect) {
                      setTooltip({
                        x: e.clientX - rect.left,
                        y: e.clientY - rect.top,
                        label: currency,
                        value: `${count} Transactions`,
                        show: true,
                      });
                    }
                  }}
                  onMouseLeave={() => setTooltip(prev => ({ ...prev, show: false }))}
                />
                <text
                  x={x + barWidth / 2}
                  y={height - 4}
                  textAnchor="middle"
                  className={styles.axisText}
                >
                  {currency}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
