import { useState } from 'react';
import { Layout } from './components/Layout';
import { LandingPage } from './views/LandingPage';
import { Dashboard } from './views/Dashboard';
import { JobDetails } from './views/JobDetails';
import { Analytics } from './views/Analytics';
import TransactionExplorer from './views/TransactionExplorer';
import SystemHealth from './views/SystemHealth';
import { UploadModal } from './components/UploadModal';

export const App = () => {
  const [user, setUser] = useState<any>(() => {
    const saved = localStorage.getItem('aerotx_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [view, setView] = useState<string>(() => {
    const saved = localStorage.getItem('aerotx_user');
    return saved ? 'dashboard' : 'landing';
  });
  const [uploadOpen, setUploadOpen] = useState(false);

  const handleLogin = (userInfo: any) => {
    localStorage.setItem('aerotx_user', JSON.stringify(userInfo));
    setUser(userInfo);
  };

  const handleLogout = () => {
    localStorage.removeItem('aerotx_user');
    setUser(null);
    setView('landing');
  };

  const handleUploadSuccess = (jobId: string) => {
    setUploadOpen(false);
    setView(`job-${jobId}`);
  };

  const renderContent = () => {
    if (view === 'dashboard') {
      return (
        <Dashboard
          onSelectJob={(id) => setView(`job-${id}`)}
          onNavigateToUpload={() => setUploadOpen(true)}
        />
      );
    }

    if (view === 'transactions') return <TransactionExplorer />;
    if (view === 'analytics')    return <Analytics />;
    if (view === 'health')       return <SystemHealth />;

    if (view.startsWith('job-')) {
      return (
        <JobDetails
          jobId={view.substring(4)}
          onBack={() => setView('dashboard')}
        />
      );
    }

    return null;
  };

  if (view === 'landing') {
    return (
      <LandingPage 
        user={user} 
        onLogin={handleLogin} 
        onLaunch={() => setView('dashboard')} 
      />
    );
  }

  return (
    <>
      <Layout
        currentView={view}
        setView={setView}
        onUploadClick={() => setUploadOpen(true)}
        user={user}
        onLogout={handleLogout}
      >
        <div className="animate-fade-in" key={view}>
          {renderContent()}
        </div>
      </Layout>

      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onSuccess={handleUploadSuccess}
        />
      )}
    </>
  );
};

export default App;
