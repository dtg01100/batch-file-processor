import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Folders from './pages/Folders'
import Jobs from './pages/Jobs'
import Logs from './pages/Logs'
import Import from './pages/Import'
import Settings from './pages/Settings'
import DynamicSettings from './pages/DynamicSettings'
import OutputProfiles from './pages/OutputProfiles'
import PipelineGraph from './pages/PipelineGraph'
import Layout from './components/Layout'
import './App.css'
import './Layout.css'
import './pages.css'

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/folders" element={<Folders />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/logs" element={<Logs />} />
          <Route path="/import" element={<Import />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/settings/dynamic" element={<DynamicSettings />} />
          <Route path="/output-profiles" element={<OutputProfiles />} />
          <Route path="/pipeline" element={<PipelineGraph />} />
        </Routes>
      </Layout>
    </Router>
  )
}

export default App
