import React from 'react';
import type { LucideIcon } from 'lucide-react';
import styles from './MetricCard.module.css';

interface MetricCardProps {
  label: string;
  value: string | number;
  icon: LucideIcon;
  subtext?: string;
  trend?: {
    type: 'up' | 'down' | 'neutral';
    value: string;
  };
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  icon: Icon,
  subtext,
  trend,
}) => {
  return (
    <div className={styles.card}>
      <div className={styles.info}>
        <span className={styles.label}>{label}</span>
        <span className={styles.value}>{value}</span>
        {trend && (
          <span className={styles.subtext}>
            <span
              className={
                trend.type === 'up'
                  ? styles.trendUp
                  : trend.type === 'down'
                  ? styles.trendDown
                  : ''
              }
            >
              {trend.value}
            </span>
            {subtext}
          </span>
        )}
        {!trend && subtext && <span className={styles.subtext}>{subtext}</span>}
      </div>

      <div className={styles.iconBox}>
        <Icon size={22} />
      </div>
    </div>
  );
};
