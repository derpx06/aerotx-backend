import React, { useState, useRef } from 'react';
import { UploadCloud, AlertCircle, FileSpreadsheet } from 'lucide-react';
import styles from './JobUpload.module.css';
import { api } from '../api';

interface JobUploadProps {
  onUploadSuccess: (jobId: string) => void;
}

interface CSVPreview {
  headers: string[];
  rows: string[][];
  totalLines: number;
}

export const JobUpload: React.FC<JobUploadProps> = ({ onUploadSuccess }) => {
  const [isDragActive, setIsDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CSVPreview | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const parseCSVPreview = (text: string): CSVPreview => {
    const lines = text.split('\n').map(line => line.trim()).filter(line => line.length > 0);
    const totalLines = lines.length;
    const headers = lines[0].split(',').map(h => h.replace(/^["']|["']$/g, '').trim());
    const previewRows = lines.slice(1, 16).map(line =>
      line.split(',').map(cell => cell.replace(/^["']|["']$/g, '').trim())
    );

    return {
      headers,
      rows: previewRows,
      totalLines: totalLines - 1, // Exclude header
    };
  };

  const handleFile = (selectedFile: File) => {
    if (!selectedFile.name.endsWith('.csv')) {
      setError('Invalid file format. Please upload a standard transaction CSV file.');
      setFile(null);
      setPreview(null);
      return;
    }

    setError(null);
    setFile(selectedFile);

    // Read preview
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      if (text) {
        try {
          const parsed = parseCSVPreview(text);
          setPreview(parsed);
        } catch (err) {
          setError('Failed to parse the CSV file. Please make sure the structure is correct.');
        }
      }
    };
    reader.readAsText(selectedFile.slice(0, 1024 * 10)); // read first 10kb
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const handleUploadSubmit = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(20);
    setError(null);

    // Simulate progress updates for a smoother UX
    const interval = setInterval(() => {
      setProgress((prev) => (prev < 90 ? prev + 10 : prev));
    }, 200);

    try {
      const job = await api.uploadCSV(file);
      clearInterval(interval);
      setProgress(100);
      setTimeout(() => {
        onUploadSuccess(job.id);
      }, 500);
    } catch (err: any) {
      clearInterval(interval);
      setUploading(false);
      setProgress(0);
      setError(err?.message || 'Failed to upload and start job. Please try again.');
    }
  };

  const handleReset = () => {
    setFile(null);
    setPreview(null);
    setError(null);
    setProgress(0);
    setUploading(false);
  };

  return (
    <div className={styles.container}>
      {error && (
        <div className={styles.errorBox}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {!file && (
        <div
          className={`${styles.uploadBox} ${isDragActive ? styles.uploadBoxHover : ''}`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          onClick={triggerFileInput}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && triggerFileInput()}
          aria-label="Upload Transaction CSV File"
        >
          <input
            ref={fileInputRef}
            type="file"
            className={styles.fileInput}
            onChange={handleChange}
            accept=".csv"
          />
          <div className={styles.iconContainer}>
            <UploadCloud size={32} />
          </div>
          <h2 className={styles.uploadTitle}>Drag and drop your transaction log</h2>
          <p className={styles.uploadSub}>
            Supports standard UTF-8 transaction CSV files containing merchant, amount, category, currency, and transaction dates.
          </p>
          <span className={styles.btn} style={{ backgroundColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
            Select CSV File
          </span>
        </div>
      )}

      {file && preview && (
        <div className={styles.previewCard}>
          <div className={styles.previewHeader}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileSpreadsheet size={18} style={{ color: 'var(--primary-hover)' }} />
              <span>{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
            </div>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
              Detected {preview.totalLines.toLocaleString()} rows
            </span>
          </div>

          <div className={styles.previewTableWrapper}>
            <table className={styles.previewTable}>
              <thead>
                <tr>
                  {preview.headers.map((h, i) => (
                    <th key={i}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, rowIdx) => (
                  <tr key={rowIdx}>
                    {row.map((cell, cellIdx) => (
                      <td key={cellIdx}>{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {uploading && (
            <div style={{ margin: '8px 0' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                <span>Ingesting and parsing file structure...</span>
                <span>{progress}%</span>
              </div>
              <div className={styles.progressBarContainer}>
                <div className={styles.progressBar} style={{ width: `${progress}%` }} />
              </div>
            </div>
          )}

          <div className={styles.buttonGroup}>
            <button
              onClick={handleReset}
              disabled={uploading}
              className={`${styles.btn} ${styles.btnSecondary}`}
            >
              Cancel
            </button>
            <button
              onClick={handleUploadSubmit}
              disabled={uploading}
              className={`${styles.btn} ${styles.btnPrimary}`}
            >
              Start Ingestion Pipeline
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
