import { useState } from 'react'
import { foldersApi, jobsApi, testConnectionApi } from '../services/api'
import { CONNECTION_TYPES } from '../services/constants'


export default function Dashboard() {
  const [folders, setFolders] = useState([])
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState({
    total_folders: 0,
    active_folders: 0,
    scheduled_jobs: 0,
    recent_runs: 0,
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [foldersRes, jobsRes] = await Promise.all([
        foldersApi.list(),
        jobsApi.list(),
      ])

      setFolders(foldersRes.data)
      setJobs(jobsRes.data)

      setStats({
        total_folders: foldersRes.data.length,
        active_folders: foldersRes.data.filter(f => f.folder_is_active).length,
        scheduled_jobs: jobsRes.data.filter(j => j.enabled).length,
        recent_runs: 5, // Would come from runs API
      })
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    }
  }

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Folders</h3>
          <p className="stat-value">{stats.total_folders}</p>
        </div>

        <div className="stat-card">
          <h3>Active Folders</h3>
          <p className="stat-value">{stats.active_folders}</p>
        </div>

        <div className="stat-card">
          <h3>Scheduled Jobs</h3>
          <p className="stat-value">{stats.scheduled_jobs}</p>
        </div>

        <div className="stat-card">
          <h3>Recent Runs</h3>
          <p className="stat-value">{stats.recent_runs}</p>
        </div>
      </div>

      <div className="recent-jobs">
        <h2>Recent Scheduled Jobs</h2>
        {jobs.slice(0, 5).map(job => (
          <div key={job.id} className="job-card">
            <div className="job-header">
              <span className="job-folder">{job.folder_alias}</span>
              <span className={`job-status ${job.enabled ? 'enabled' : 'disabled'}`}>
                {job.enabled ? 'Scheduled' : 'Disabled'}
              </span>
            </div>
            <div className="job-details">
              <span>Next Run: {job.next_run || 'Not scheduled'}</span>
            </div>
            <div className="job-actions">
              <button
                onClick={() => handleToggleJob(job.id, job.enabled)}
                disabled={job.folder_is_active}
              >
                {job.enabled ? 'Disable' : 'Enable'}
              </button>
              <button
                onClick={() => handleRunJob(job.id)}
                disabled={!job.enabled || !job.folder_is_active}
              >
                Run Now
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

async function handleToggleJob(jobId, currentEnabled) {
  try {
    await jobsApi.toggle(jobId)
    setJobs(jobs => jobs.map(j => 
      j.id === jobId ? { ...j, enabled: !currentEnabled } : j
    ))
  } catch (error) {
    console.error('Failed to toggle job:', error)
  }
}

async function handleRunJob(jobId) {
  try {
    await jobsApi.run(jobId)
    console.log('Job triggered:', jobId)
  } catch (error) {
    console.error('Failed to run job:', error)
  }
}
