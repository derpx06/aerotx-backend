import { useState, useEffect } from 'react';
import { LayoutDashboard, Table2, BarChart2, Activity, UploadCloud, Cpu, LogOut, Terminal, RefreshCw } from 'lucide-react';
import styles from './Layout.module.css';
import { api } from '../api';

interface LayoutProps {
  currentView: string;
  setView: (view: string) => void;
  onUploadClick: () => void;
  user: any;
  onLogout: () => void;
  children: React.ReactNode;
}

export const Layout = ({ currentView, setView, onUploadClick, user, onLogout, children }: LayoutProps) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);

  const checkHealth = async () => {
    setChecking(true);
    try {
      await api.getHealth();
      setIsHealthy(true);
    } catch {
      setIsHealthy(false);
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  const getPageTitle = () => {
    if (currentView === 'dashboard') return 'Dashboard';
    if (currentView === 'upload') return 'Upload';
    if (currentView === 'transactions') return 'Transactions';
    if (currentView === 'analytics') return 'Analytics';
    if (currentView === 'health') return 'System Health';
    if (currentView.startsWith('job-')) return 'Job Details';
    return 'AeroTx';
  };

  return (
    <div className={styles.container}>
      <aside className={styles.sidebar}>
        {/* Logo */}
        <div className={styles.logoContainer}>
          <div className={styles.logo}>
            <Cpu size={16} />
          </div>
          <span className={styles.logoText}>AeroTx</span>
        </div>

        {/* Primary nav: Workspace */}
        <div className={styles.navSection}>
          <span className={styles.sectionHeader}>Workspace</span>
          <nav className={styles.nav}>
            <button
              onClick={() => setView('dashboard')}
              className={`${styles.navLink} ${currentView === 'dashboard' || currentView.startsWith('job-') ? styles.navLinkActive : ''}`}
            >
              <LayoutDashboard size={15} />
              <span>Dashboard</span>
            </button>
            <button
              onClick={() => setView('transactions')}
              className={`${styles.navLink} ${currentView === 'transactions' ? styles.navLinkActive : ''}`}
            >
              <Table2 size={15} />
              <span>Transactions</span>
            </button>
            <button
              onClick={() => setView('analytics')}
              className={`${styles.navLink} ${currentView === 'analytics' ? styles.navLinkActive : ''}`}
            >
              <BarChart2 size={15} />
              <span>Analytics</span>
            </button>
          </nav>
        </div>

        {/* Operational Status */}
        <div className={styles.navSection}>
          <span className={styles.sectionHeader}>Operational</span>
          <nav className={styles.nav}>
            <button
              onClick={() => setView('health')}
              className={`${styles.navLink} ${currentView === 'health' ? styles.navLinkActive : ''}`}
            >
              <Activity size={15} />
              <span>System Health</span>
            </button>
          </nav>
        </div>

        {/* Quick Actions Panel */}
        <div className={styles.navSection}>
          <span className={styles.sectionHeader}>Quick Actions</span>
          <div className={styles.actionPanel}>
            <button
              onClick={onUploadClick}
              className={styles.sidebarActionBtn}
            >
              <UploadCloud size={14} />
              <span>Upload CSV</span>
            </button>
            <button
              onClick={checkHealth}
              disabled={checking}
              className={styles.sidebarActionBtn}
            >
              <RefreshCw size={14} className={checking ? 'animate-spin' : ''} />
              <span>Trigger Sync Check</span>
            </button>
            <button
              onClick={() => setView('transactions')}
              className={styles.sidebarActionBtn}
            >
              <Terminal size={14} />
              <span>Database Query</span>
            </button>
          </div>
        </div>

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* User profile */}
        {user && (
          <div className={styles.userProfile}>
            <img 
              src={user.avatarUrl || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=80&q=80'} 
              alt="avatar" 
              className={styles.avatar} 
            />
            <div className={styles.userInfo}>
              <span className={styles.userName}>{user.name}</span>
              <span className={styles.userEmail}>{user.email}</span>
            </div>
            <button 
              onClick={onLogout} 
              className={styles.logoutBtn}
              title="Sign Out"
            >
              <LogOut size={14} />
            </button>
          </div>
        )}

        {/* Status indicator */}
        <div className={styles.statusRow}>
          <div className={`${styles.statusDot} ${isHealthy === true ? styles.dotOnline : isHealthy === false ? styles.dotOffline : styles.dotChecking}`} />
          <span className={styles.statusLabel}>
            {isHealthy === true ? 'API Connected' : isHealthy === false ? 'API Offline' : 'Checking...'}
          </span>
        </div>
      </aside>

      <div className={styles.contentWrapper}>
        <header className={styles.header}>
          <h1 className={styles.pageTitle}>{getPageTitle()}</h1>
        </header>
        <main className={styles.mainContent}>
          {children}
        </main>
      </div>
    </div>
  );
};
