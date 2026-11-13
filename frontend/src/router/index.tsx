import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { LoginPage } from '../pages/Login';
import { SourcesPage } from '../pages/Sources';
import { RawQueuePage } from '../pages/RawQueue';
import { PostingsPage } from '../pages/Postings';
import { RulesPage } from '../pages/Rules';
import { BenchmarksPage } from '../pages/Benchmarks';
import { QualityPage } from '../pages/Quality';
import { RequireAuth } from './guards';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppShell />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <Navigate to="/raw" replace /> },
      { path: 'sources', element: <SourcesPage /> },
      { path: 'raw', element: <RawQueuePage /> },
      { path: 'postings', element: <PostingsPage /> },
      { path: 'rules', element: <RulesPage /> },
      { path: 'benchmarks', element: <BenchmarksPage /> },
      { path: 'quality', element: <QualityPage /> },
    ],
  },
  { path: '*', element: <Navigate to="/" replace /> },
]);
