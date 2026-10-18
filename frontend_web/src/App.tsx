import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import ProspectingPage from './pages/ProspectingPage'
import ConversationsPage from './pages/ConversationsPage'
import DashboardPage from './pages/DashboardPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/prospecting" replace />} />
        <Route path="/prospecting" element={<ProspectingPage />} />
        <Route path="/conversations" element={<ConversationsPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="*" element={<Navigate to="/prospecting" replace />} />
      </Route>
    </Routes>
  )
}
