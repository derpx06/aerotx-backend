import { useEffect } from 'react';
import { X } from 'lucide-react';
import { JobUpload } from '../views/JobUpload';
import styles from './UploadModal.module.css';

interface UploadModalProps {
  onClose: () => void;
  onSuccess: (jobId: string) => void;
}

export function UploadModal({ onClose, onSuccess }: UploadModalProps) {
  // Close on Escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  // Prevent body scroll while open
  useEffect(() => {
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
  }, []);

  return (
    <div className={styles.backdrop} onClick={onClose} role="dialog" aria-modal="true" aria-label="Upload CSV">
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <h2 className={styles.title}>Upload Transaction CSV</h2>
            <p className={styles.subtitle}>Drag & drop or browse to select your CSV file</p>
          </div>
          <button className={styles.closeBtn} onClick={onClose} aria-label="Close upload dialog">
            <X size={18} />
          </button>
        </div>

        {/* Body — reuses the existing JobUpload component */}
        <div className={styles.body}>
          <JobUpload onUploadSuccess={(id) => { onClose(); onSuccess(id); }} />
        </div>
      </div>
    </div>
  );
}
