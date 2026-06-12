import { useState, useEffect } from 'react';
import { 
  ArrowRight, 
  ShieldCheck, 
  Sparkles, 
  Cpu, 
  Settings, 
  AlertTriangle, 
  Layers, 
  Activity, 
  Database, 
  Workflow, 
  CheckCircle2, 
  UploadCloud,
  ChevronRight,
  Server,
  LineChart
} from 'lucide-react';
import { api } from '../api';
import styles from './LandingPage.module.css';

declare global {
  interface Window {
    google?: any;
  }
}

interface LandingPageProps {
  user: any;
  onLogin: (user: any) => void;
  onLaunch: () => void;
}

export const LandingPage = ({ user, onLogin, onLaunch }: LandingPageProps) => {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);
  const [clientId, setClientId] = useState(
    localStorage.getItem('aerotx_google_client_id') || 
    import.meta.env.VITE_GOOGLE_CLIENT_ID || 
    '827464019253-dummyclientid.apps.googleusercontent.com'
  );
  const [showSettings, setShowSettings] = useState(false);
  const [tempClientId, setTempClientId] = useState(clientId);
  const [clientInitError, setClientInitError] = useState<string | null>(null);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        await api.getHealth();
        setIsHealthy(true);
      } catch {
        setIsHealthy(false);
      }
    };
    checkHealth();
  }, []);

  // Dynamically load Google Identity Services Script
  useEffect(() => {
    if (user) return;

    const existingScript = document.getElementById('google-gsi-script');
    if (existingScript) {
      existingScript.remove();
    }

    const script = document.createElement('script');
    script.id = 'google-gsi-script';
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);

    script.onload = () => {
      try {
        window.google?.accounts.id.initialize({
          client_id: clientId,
          callback: (response: any) => {
            try {
              const tokenPayload = response.credential.split('.')[1];
              const decodedPayload = JSON.parse(
                decodeURIComponent(
                  atob(tokenPayload)
                    .split('')
                    .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                    .join('')
                )
              );

              const googleUser = {
                name: decodedPayload.name,
                email: decodedPayload.email,
                avatarUrl: decodedPayload.picture,
              };

              onLogin(googleUser);
              onLaunch();
            } catch (jwtErr) {
              console.error('Failed to parse JWT payload:', jwtErr);
              setClientInitError('Authentication parsing error.');
            }
          },
        });

        const btnElement = document.getElementById('google-signin-btn-container');
        if (btnElement) {
          window.google?.accounts.id.renderButton(btnElement, {
            type: 'standard',
            theme: 'filled_black',
            size: 'large',
            text: 'signin_with',
            shape: 'rectangular',
            logo_alignment: 'left',
          });
        }
      } catch (err) {
        console.error('Failed to initialize Google login widget:', err);
        setClientInitError('Configuration or Client ID error.');
      }
    };

    return () => {
      const scriptToRemove = document.getElementById('google-gsi-script');
      if (scriptToRemove) {
        scriptToRemove.remove();
      }
    };
  }, [clientId, user, onLogin, onLaunch]);

  const saveClientId = () => {
    localStorage.setItem('aerotx_google_client_id', tempClientId);
    setClientId(tempClientId);
    setShowSettings(false);
    setClientInitError(null);
  };

  const scrollToLogin = () => {
    document.getElementById('login-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToTech = () => {
    document.getElementById('tech-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className={styles.container}>
      {/* Decorative background effects */}
      <div className={styles.gridOverlay} />
      <div className={styles.ambientGlow} />
      <div className={styles.ambientGlowSecondary} />

      {/* Top Navbar */}
      <header className={styles.navbar}>
        <div className={styles.navLogo}>
          <Cpu size={18} className={styles.logoPulse} />
          <span>AeroTx</span>
        </div>
        <div className={styles.navActions}>
          <div className={styles.navHealth}>
            <span className={`${styles.navHealthDot} ${isHealthy ? styles.navHealthOnline : styles.navHealthOffline}`} />
            <span>{isHealthy ? 'API Connected' : 'Connecting to Core...'}</span>
          </div>
          <button onClick={scrollToLogin} className={styles.navBtn}>
            Launch Console
          </button>
        </div>
      </header>

      {/* Settings Panel Gear */}
      {!user && (
        <div className={styles.settingsWrapper}>
          <button 
            className={styles.settingsToggle}
            onClick={() => setShowSettings(!showSettings)}
            title="Configure Google OAuth Client ID"
          >
            <Settings size={16} />
          </button>

          {showSettings && (
            <div className={styles.settingsPanel}>
              <h4>OAuth Client Settings</h4>
              <p>Configure a custom Google Client ID for local login testing:</p>
              <input 
                type="text" 
                value={tempClientId} 
                onChange={(e) => setTempClientId(e.target.value)}
                placeholder="Google OAuth Client ID"
              />
              <div className={styles.settingsActions}>
                <button className={styles.settingsSave} onClick={saveClientId}>Save & Reconnect</button>
                <button className={styles.settingsCancel} onClick={() => setShowSettings(false)}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 1. HERO SECTION */}
      <section className={styles.heroSection}>
        <div className={styles.heroBadge}>
          <span className={styles.badgePulse} />
          <span>Enterprise Transaction Intelligence Platform</span>
        </div>
        
        <h1 className={styles.heroTitle}>
          AI-Powered Transaction Processing <br />
          <span className={styles.gradientText}>Built For Scale</span>
        </h1>
        
        <p className={styles.heroSubtitle}>
          Ingest raw transactions, isolate risks via strategy-pattern heuristics, and synthesize narratives using distributed LLM engines with microsecond tracking telemetry.
        </p>

        <div className={styles.heroActions}>
          <button onClick={scrollToLogin} className={styles.primaryHeroBtn}>
            <span>Access Platform</span>
            <ArrowRight size={16} />
          </button>
          <button onClick={scrollToTech} className={styles.secondaryHeroBtn}>
            <span>View Architecture</span>
          </button>
        </div>
      </section>

      {/* 2. PLATFORM PREVIEW (FLOATING DASHBOARD MOCKUP) */}
      <section className={styles.previewSection}>
        <div className={styles.previewContainer}>
          <div className={styles.previewHeader}>
            <div className={styles.windowDots}>
              <span className={styles.dotRed} />
              <span className={styles.dotYellow} />
              <span className={styles.dotGreen} />
            </div>
            <div className={styles.windowTitle}>AeroTx Console // Pipeline Control</div>
            <div className={styles.windowStatus}>
              <Activity size={12} className={styles.pulseColor} />
              <span>Pipeline: ACTIVE</span>
            </div>
          </div>
          
          <div className={styles.previewGrid}>
            {/* Mock Sidebar */}
            <div className={styles.mockSidebar}>
              <div className={styles.mockSidebarItemActive}><Layers size={14} /><span>Dashboard</span></div>
              <div className={styles.mockSidebarItem}><Workflow size={14} /><span>Explorer</span></div>
              <div className={styles.mockSidebarItem}><LineChart size={14} /><span>Analytics</span></div>
              <div className={styles.mockSidebarItem}><Activity size={14} /><span>Health</span></div>
            </div>

            {/* Mock Dashboard Body */}
            <div className={styles.mockBody}>
              {/* Row 1: Metrics */}
              <div className={styles.mockMetricsRow}>
                <div className={styles.mockMetricCard}>
                  <div className={styles.metricLabel}>Transactions Processed</div>
                  <div className={styles.metricValue}>1,248,592</div>
                  <div className={styles.metricSub}>99.99% Cleansed</div>
                </div>
                <div className={styles.mockMetricCard}>
                  <div className={styles.metricLabel}>Risk Anomaly Ratio</div>
                  <div className={styles.metricValue} style={{ color: 'var(--warning)' }}>4.21%</div>
                  <div className={styles.metricSub}>Strategy-Pattern Flagged</div>
                </div>
                <div className={styles.mockMetricCard}>
                  <div className={styles.metricLabel}>Average Latency</div>
                  <div className={styles.metricValue}>42.8ms</div>
                  <div className={styles.metricSub}>Redis Cached</div>
                </div>
              </div>

              {/* Row 2: Charts and Tables */}
              <div className={styles.mockChartsGrid}>
                {/* Mock Chart */}
                <div className={styles.mockChartCard}>
                  <div className={styles.cardHeader}>Risk Categories Distribution</div>
                  <div className={styles.donutMock}>
                    <div className={styles.donutCircle}>
                      <span className={styles.donutCenter}>4.2%</span>
                    </div>
                    <div className={styles.donutLegend}>
                      <div><span className={styles.legSquare} style={{ background: 'var(--primary)' }} /><span>Normal (95.8%)</span></div>
                      <div><span className={styles.legSquare} style={{ background: 'var(--warning)' }} /><span>Deviation (3.1%)</span></div>
                      <div><span className={styles.legSquare} style={{ background: 'var(--danger)' }} /><span>Critical Risk (1.1%)</span></div>
                    </div>
                  </div>
                </div>

                {/* Mock Table */}
                <div className={styles.mockTableCard}>
                  <div className={styles.cardHeader}>Recent Ingested Transactions</div>
                  <div className={styles.tableMock}>
                    <div className={styles.tableRowHeader}>
                      <span>Counterparty</span>
                      <span>Amount</span>
                      <span>Status</span>
                    </div>
                    <div className={styles.tableRow}>
                      <span>Acme Corp Inc.</span>
                      <span>$12,450.00</span>
                      <span className={styles.badgeSuccess}>CLEANSED</span>
                    </div>
                    <div className={styles.tableRow}>
                      <span>AWS Cloud Billing</span>
                      <span>$4,120.45</span>
                      <span className={styles.badgeSuccess}>CLEANSED</span>
                    </div>
                    <div className={styles.tableRow}>
                      <span>Unknown Merchant (HK)</span>
                      <span>$8,900.00</span>
                      <span className={styles.badgeWarning}>RISK_FLAG</span>
                    </div>
                    <div className={styles.tableRow}>
                      <span>OpenAI API</span>
                      <span>$452.10</span>
                      <span className={styles.badgeSuccess}>CLEANSED</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. KEY METRICS */}
      <section className={styles.metricsSection}>
        <div className={styles.metricsGrid}>
          <div className={styles.metricBox}>
            <div className={styles.metricNumber}>100k+</div>
            <div className={styles.metricTitle}>Transactions Processed</div>
            <div className={styles.metricDesc}>Bulk pipeline uploads ingested, parsed, and mapped dynamically.</div>
          </div>
          <div className={styles.metricBox}>
            <div className={styles.metricNumber}>99.9%</div>
            <div className={styles.metricTitle}>Pipeline Reliability</div>
            <div className={styles.metricDesc}>Zero-loss task queue orchestration with automated worker retries.</div>
          </div>
          <div className={styles.metricBox}>
            <div className={styles.metricNumber}>&lt;100ms</div>
            <div className={styles.metricTitle}>Sub-Second Job Visibility</div>
            <div className={styles.metricDesc}>Near-instant task status checks using Redis event locks.</div>
          </div>
          <div className={styles.metricBox}>
            <div className={styles.metricNumber}>LLM</div>
            <div className={styles.metricTitle}>Classification Engine</div>
            <div className={styles.metricDesc}>High-speed transaction narratives powered by Google Gemini API.</div>
          </div>
        </div>
      </section>

      {/* 4. PROCESS VISUALIZATION PIPELINE */}
      <section className={styles.pipelineSection}>
        <div className={styles.sectionHeader}>
          <h2>Autonomous Processing Pipeline</h2>
          <p>How raw transaction records are cleaned, audited, classified, and indexed in real-time.</p>
        </div>

        <div className={styles.pipelineContainer}>
          <div className={styles.pipelineNode}>
            <div className={styles.nodeIcon}><UploadCloud size={18} /></div>
            <div className={styles.nodeTitle}>CSV Upload</div>
            <div className={styles.nodeSubtitle}>Multipart parse</div>
          </div>
          <div className={styles.pipelineArrow}><ChevronRight size={14} /></div>

          <div className={styles.pipelineNode}>
            <div className={styles.nodeIcon}><CheckCircle2 size={18} /></div>
            <div className={styles.nodeTitle}>Validation</div>
            <div className={styles.nodeSubtitle}>Format & schema</div>
          </div>
          <div className={styles.pipelineArrow}><ChevronRight size={14} /></div>

          <div className={styles.pipelineNode}>
            <div className={styles.nodeIcon}><Cpu size={18} /></div>
            <div className={styles.nodeTitle}>Data Cleaning</div>
            <div className={styles.nodeSubtitle}>Whitespace & nulls</div>
          </div>
          <div className={styles.pipelineArrow}><ChevronRight size={14} /></div>

          <div className={styles.pipelineNode}>
            <div className={styles.nodeIcon}><ShieldCheck size={18} /></div>
            <div className={styles.nodeTitle}>Risk Heuristics</div>
            <div className={styles.nodeSubtitle}>Deviation scoring</div>
          </div>
          <div className={styles.pipelineArrow}><ChevronRight size={14} /></div>

          <div className={styles.pipelineNode}>
            <div className={styles.nodeIcon}><Sparkles size={18} /></div>
            <div className={styles.nodeTitle}>AI Inference</div>
            <div className={styles.nodeSubtitle}>Gemini classification</div>
          </div>
          <div className={styles.pipelineArrow}><ChevronRight size={14} /></div>

          <div className={styles.pipelineNode}>
            <div className={styles.nodeIcon}><Layers size={18} /></div>
            <div className={styles.nodeTitle}>Sync Registry</div>
            <div className={styles.nodeSubtitle}>Database commit</div>
          </div>
          <div className={styles.pipelineArrow}><ChevronRight size={14} /></div>

          <div className={styles.pipelineNode}>
            <div className={styles.nodeIcon}><LineChart size={18} /></div>
            <div className={styles.nodeTitle}>Real-time Analytics</div>
            <div className={styles.nodeSubtitle}>Index updates</div>
          </div>
        </div>
      </section>

      {/* 5. PLATFORM CAPABILITIES */}
      <section className={styles.capabilitiesSection}>
        <div className={styles.sectionHeader}>
          <h2>Built For Modern Transaction Intelligence</h2>
          <p>A unified infrastructure layers clean ingestion, analytical insights, and machine learning models together.</p>
        </div>

        <div className={styles.capabilitiesGrid}>
          <div className={styles.capCard}>
            <div className={styles.capIcon}><UploadCloud size={20} /></div>
            <h4>Transaction Ingestion</h4>
            <p>Direct chunked multipart uploads with asynchronous background processing to handle files containing millions of rows without timeouts.</p>
          </div>
          <div className={styles.capCard}>
            <div className={styles.capIcon}><Cpu size={20} /></div>
            <h4>Automatic Data Cleaning</h4>
            <p>Standardizes messy inputs: resolves blank merchants, cleans decimal floats, aligns currencies, and removes corrupt characters.</p>
          </div>
          <div className={styles.capCard}>
            <div className={styles.capIcon}><ShieldCheck size={20} /></div>
            <h4>Deterministic Risk Scoring</h4>
            <p>Computes risk scores using algorithms including duplicate frequency matching, median deviation triggers, and transaction risk models.</p>
          </div>
          <div className={styles.capCard}>
            <div className={styles.capIcon}><Sparkles size={20} /></div>
            <h4>AI Narrative Classification</h4>
            <p>Generates context-rich merchant categorizations and high-level transaction summary reports using prompt-optimized LLM pipelines.</p>
          </div>
          <div className={styles.capCard}>
            <div className={styles.capIcon}><LineChart size={20} /></div>
            <h4>Operational Analytics</h4>
            <p>Embedded dashboard charts including spend category distributions and counterparty volume tables computed dynamically on ingest.</p>
          </div>
          <div className={styles.capCard}>
            <div className={styles.capIcon}><Workflow size={20} /></div>
            <h4>Full Timeline Audits</h4>
            <p>Track job telemetry records at every microservice transition—from file queuing and cleaning to risk engine runs and completion.</p>
          </div>
        </div>
      </section>

      {/* 6. TECHNOLOGY SHOWCASE */}
      <section id="tech-section" className={styles.techSection}>
        <div className={styles.sectionHeader}>
          <h2>Enterprise-Grade Architecture Stack</h2>
          <p>Engineered for low latency, fault tolerance, and secure modular isolation.</p>
        </div>

        <div className={styles.techGrid}>
          <div className={styles.techBox}>
            <div className={styles.techHeader}>
              <Server size={18} className={styles.techIcon} />
              <h4>FastAPI Core</h4>
            </div>
            <p>High-performance asynchronous Python REST server. Handles API routes with Pydantic schemas and auto-generated OpenAPI documentation.</p>
          </div>
          <div className={styles.techBox}>
            <div className={styles.techHeader}>
              <Database size={18} className={styles.techIcon} />
              <h4>PostgreSQL</h4>
            </div>
            <p>Relational storage with connection pooling, transactional integrity, and custom database indices for transaction querying.</p>
          </div>
          <div className={styles.techBox}>
            <div className={styles.techHeader}>
              <Activity size={18} className={styles.techIcon} />
              <h4>Redis</h4>
            </div>
            <p>In-memory cache and Celery broker. Drives sub-millisecond job locking, status tracking, and query response caches.</p>
          </div>
          <div className={styles.techBox}>
            <div className={styles.techHeader}>
              <Workflow size={18} className={styles.techIcon} />
              <h4>Celery Workers</h4>
            </div>
            <p>Distributed background worker task runners. Executes heavy computations, validation runs, and LLM calls in independent processes.</p>
          </div>
          <div className={styles.techBox}>
            <div className={styles.techHeader}>
              <Sparkles size={18} className={styles.techIcon} />
              <h4>Gemini AI</h4>
            </div>
            <p>Large language model orchestration with fallback circuit breakers. Classifies categories and writes human-readable summaries.</p>
          </div>
          <div className={styles.techBox}>
            <div className={styles.techHeader}>
              <Layers size={18} className={styles.techIcon} />
              <h4>Dockerized Orchestration</h4>
            </div>
            <p>Standardized containers for development and testing. Enables isolated, reproducible builds across environment stages.</p>
          </div>
        </div>
      </section>

      {/* 7. LOGIN CTA SECTION (MOVED TO BOTTOM) */}
      <section id="login-section" className={styles.loginSection}>
        <div className={styles.loginContainer}>
          <div className={styles.loginContent}>
            <h2>Launch the Analytics Console</h2>
            <p>Connect your account using enterprise authentication to begin parsing transactions and exploring risk anomalies.</p>
            
            <div className={styles.loginFeatureList}>
              <div className={styles.loginFeature}><CheckCircle2 size={16} /> <span>Deterministic cleaning pipeline</span></div>
              <div className={styles.loginFeature}><CheckCircle2 size={16} /> <span>Strategy risk validation</span></div>
              <div className={styles.loginFeature}><CheckCircle2 size={16} /> <span>Real-time telemetry reports</span></div>
            </div>
          </div>

          <div className={styles.loginCard}>
            {user ? (
              <div className={styles.loggedInView}>
                <div className={styles.userSummary}>
                  <img src={user.avatarUrl} alt="avatar" className={styles.loggedInAvatar} />
                  <div>
                    <div className={styles.loggedInName}>{user.name}</div>
                    <div className={styles.loggedInEmail}>{user.email}</div>
                  </div>
                </div>
                <button onClick={onLaunch} className={styles.launchBtn}>
                  <span>Enter Dashboard Console</span>
                  <ArrowRight size={16} />
                </button>
              </div>
            ) : (
              <div className={styles.loggedOutView}>
                <div className={styles.loginCardHeader}>
                  <h3>Access Platform Workspace</h3>
                  <p>OAuth authentication via Google account required.</p>
                </div>

                {clientInitError && (
                  <div className={styles.oauthError}>
                    <AlertTriangle size={14} />
                    <span>{clientInitError} (Click Settings gear at top right)</span>
                  </div>
                )}

                {/* Real Google Button Container */}
                <div className={styles.googleBtnWrapper}>
                  <div id="google-signin-btn-container"></div>
                </div>

                <div className={styles.developerBypass}>
                  <span>Developer Sandbox: </span>
                  <button 
                    type="button" 
                    onClick={() => {
                      onLogin({
                        name: 'Developer Sandbox User',
                        email: 'dev.user@aerotx.local',
                        avatarUrl: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=80&q=80',
                      });
                      onLaunch();
                    }}
                    className={styles.bypassLink}
                  >
                    Bypass with Local Session
                  </button>
                </div>

                <div className={styles.loginFooter}>
                  Authorized secure workspace. Credentials are routed directly to accounts.google.com.
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className={styles.footer}>
        <div className={styles.footerBrand}>
          <Cpu size={16} />
          <span>AeroTx Platform</span>
        </div>
        <div className={styles.footerInfo}>
          <span>© {new Date().getFullYear()} AeroTx. All rights reserved.</span>
          <span>•</span>
          <span className={styles.footerStatus}>
            <span className={`${styles.statusDot} ${isHealthy ? styles.statusOnline : styles.statusOffline}`} />
            {isHealthy ? 'All Systems Operational' : 'Offline Mode'}
          </span>
        </div>
      </footer>
    </div>
  );
};
