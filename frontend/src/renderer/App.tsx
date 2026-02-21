/**
 * Main Application Component
 *
 * JAIA - Journal entry AI Analyzer
 */

import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import ErrorBoundary from './components/ErrorBoundary';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import ImportPage from './pages/ImportPage';
import SearchPage from './pages/SearchPage';
import TimeSeriesPage from './pages/TimeSeriesPage';
import AccountsPage from './pages/AccountsPage';
import SettingsPage from './pages/SettingsPage';
import RiskPage from './pages/RiskPage';
import AIAnalysisPage from './pages/AIAnalysisPage';
import ReportsPage from './pages/ReportsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import Onboarding, { useOnboarding } from './components/onboarding/Onboarding';
import { api } from './lib/api';

// Create React Query client with professional settings
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function useTheme() {
  useEffect(() => {
    const applyTheme = () => {
      try {
        const stored = localStorage.getItem('jaia-settings');
        const settings = stored ? JSON.parse(stored) : {};
        const theme = settings.theme || 'system';

        if (
          theme === 'dark' ||
          (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
        ) {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      } catch {
        document.documentElement.classList.remove('dark');
      }
    };

    applyTheme();

    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'jaia-settings') applyTheme();
    };
    window.addEventListener('storage', handleStorage);

    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    mq.addEventListener('change', applyTheme);

    // Poll for same-window localStorage changes
    const interval = setInterval(applyTheme, 1000);

    return () => {
      window.removeEventListener('storage', handleStorage);
      mq.removeEventListener('change', applyTheme);
      clearInterval(interval);
    };
  }, []);
}

function AppContent() {
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const { showOnboarding, completeOnboarding } = useOnboarding();

  useTheme();

  // Check backend connection on mount
  useEffect(() => {
    const checkConnection = async () => {
      try {
        await api.healthCheck();
        setIsBackendConnected(true);
      } catch {
        setIsBackendConnected(false);
      }
    };

    checkConnection();
    // Check every 30 seconds
    const interval = setInterval(checkConnection, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      {/* Onboarding for first-time users */}
      {showOnboarding && <Onboarding onComplete={completeOnboarding} />}

      <Layout isConnected={isBackendConnected}>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/import" element={<ImportPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/timeseries" element={<TimeSeriesPage />} />
          <Route path="/accounts" element={<AccountsPage />} />
          <Route path="/risk" element={<RiskPage />} />
          <Route path="/ai-analysis" element={<AIAnalysisPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </Layout>
    </>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppContent />
        </BrowserRouter>
        <Toaster position="top-right" richColors closeButton />
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
