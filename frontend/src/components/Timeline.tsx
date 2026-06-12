import React from 'react';
import { Check, X } from 'lucide-react';
import styles from './Timeline.module.css';
import type { Job } from '../api';

interface TimelineProps {
  job: Job;
}

interface StepInfo {
  key: string;
  title: string;
  description: string;
}

export const Timeline: React.FC<TimelineProps> = ({ job }) => {
  const steps: StepInfo[] = [
    { key: 'upload', title: 'Upload', description: 'CSV Upload Ingested' },
    { key: 'validation', title: 'Validation', description: 'Schema Integrity Check' },
    { key: 'cleaning', title: 'Cleaning', description: 'Data Sanitization' },
    { key: 'anomaly', title: 'Anomaly Audit', description: 'Multi-Strategy Risk Check' },
    { key: 'classification', title: 'Classification', description: 'LLM Categorization' },
    { key: 'reporting', title: 'AI Summary', description: 'Narrative Insight Generation' },
    { key: 'completed', title: 'Completed', description: 'Audit Pipeline Concluded' },
  ];

  // Resolve step states: 'pending' | 'active' | 'completed' | 'failed'
  const getStepState = (stepKey: string): 'pending' | 'active' | 'completed' | 'failed' => {
    const status = job.status;

    if (status === 'FAILED') {
      // Find where it failed based on metadata
      const failedStepKey = job.error_message?.toLowerCase().includes('validation')
        ? 'validation'
        : job.error_message?.toLowerCase().includes('clean')
        ? 'cleaning'
        : job.error_message?.toLowerCase().includes('anomaly') || job.error_message?.toLowerCase().includes('risk')
        ? 'anomaly'
        : job.llm_failed || job.error_message?.toLowerCase().includes('llm') || job.error_message?.toLowerCase().includes('classify')
        ? 'classification'
        : job.error_message?.toLowerCase().includes('report') || job.error_message?.toLowerCase().includes('summary')
        ? 'reporting'
        : 'completed'; // default

      if (stepKey === failedStepKey) return 'failed';
      // Any step before the failed step is completed, after is pending
      const failedIdx = steps.findIndex(s => s.key === failedStepKey);
      const currentIdx = steps.findIndex(s => s.key === stepKey);
      return currentIdx < failedIdx ? 'completed' : 'pending';
    }

    switch (stepKey) {
      case 'upload':
        return 'completed'; // Upload is always done if the job exists

      case 'validation':
        if (status === 'PENDING') return 'active';
        return 'completed';

      case 'cleaning':
        if (status === 'PENDING') return 'pending';
        if (status === 'PROCESSING') return 'active';
        return 'completed';

      case 'anomaly':
        if (status === 'PENDING' || status === 'PROCESSING') {
          // If row_count_clean exists, cleaning is done, so we are auditing anomalies
          return job.row_count_clean ? 'active' : 'pending';
        }
        return 'completed';

      case 'classification':
        if (status === 'PENDING' || status === 'PROCESSING') return 'pending';
        if (status === 'LLM_PROCESSING') return 'active';
        return 'completed';

      case 'reporting':
        if (status === 'PENDING' || status === 'PROCESSING' || status === 'LLM_PROCESSING') return 'pending';
        if (status === 'REPORTING') return 'active';
        return 'completed';

      case 'completed':
        return status === 'COMPLETED' ? 'completed' : 'pending';

      default:
        return 'pending';
    }
  };

  // Calculate progress bar width
  const getProgressWidth = (): string => {
    if (job.status === 'COMPLETED') return '100%';
    const activeIdx = steps.findIndex(s => getStepState(s.key) === 'active' || getStepState(s.key) === 'failed');
    if (activeIdx === -1) return '0%';
    return `${(activeIdx / (steps.length - 1)) * 100}%`;
  };

  return (
    <div className={styles.timeline}>
      <div className={styles.timelineLine} />
      <div 
        className={styles.timelineProgress} 
        style={{ width: getProgressWidth() }} 
      />

      {steps.map((step, idx) => {
        const state = getStepState(step.key);
        return (
          <div key={step.key} className={styles.step}>
            <div 
              className={`${styles.node} ${
                state === 'completed' 
                  ? styles.nodeCompleted 
                  : state === 'active' 
                  ? styles.nodeActive 
                  : state === 'failed' 
                  ? styles.nodeFailed 
                  : ''
              }`}
            >
              {state === 'completed' && <Check size={16} />}
              {state === 'failed' && <X size={16} />}
              {state !== 'completed' && state !== 'failed' && idx + 1}
            </div>
            <span 
              className={`${styles.stepTitle} ${
                state === 'active' 
                  ? styles.stepTitleActive 
                  : state === 'completed' 
                  ? styles.stepTitleCompleted 
                  : state === 'failed' 
                  ? styles.stepTitleFailed 
                  : ''
              }`}
            >
              {step.title}
            </span>
            <span className={styles.stepDesc}>{step.description}</span>
          </div>
        );
      })}
    </div>
  );
};
