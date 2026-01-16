import { useState, useEffect } from 'react'
import { foldersApi, jobsApi, testConnectionApi } from '../services/api'
import { CONNECTION_TYPES } from '../services/constants'
import ErrorBoundary from '../components/ErrorBoundary'
import LoadingSpinner from '../components/LoadingSpinner'
import { useNotification } from '../contexts/NotificationContext'


export default function Dashboard() {
  const [folders, setFolders] = useState([])
  const [jobs, setJobs] = useState([])
  const [stats, setStats] = useState({
    total_folders: 0,
    active_folders: 0,
    scheduled_jobs: 0,
    recent_runs: 0,
  })
  const [loading, setLoading] = useState(true)
  const [jobActionsLoading, setJobActionsLoading] = useState({})
  const notify = useNotification()

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
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

      notify.showSuccess('Dashboard data loaded successfully')
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
      notify.showError(`Failed to load dashboard data: ${error.message}`)
    } finally {
      setLoading(false)
    }
  }

  const handleToggleJob = async (jobId, currentEnabled) => {
    setJobActionsLoading(prev => ({
      ...prev,
      [jobId]: { ...prev[jobId], toggle: true }
    }));

    try {
      await jobsApi.toggle(jobId);
      setJobs(jobs => jobs.map(j =>
        j.id === jobId ? { ...j, enabled: !currentEnabled } : j
      ));

      notify.showSuccess(`Job ${currentEnabled ? 'disabled' : 'enabled'} successfully`);
    } catch (error) {
      console.error('Failed to toggle job:', error);
      notify.showError(`Failed to ${currentEnabled ? 'disable' : 'enable'} job: ${error.message}`);
    } finally {
      setJobActionsLoading(prev => ({
        ...prev,
        [jobId]: { ...prev[jobId], toggle: false }
      }));
    }
  };

  const handleRunJob = async (jobId) => {
    setJobActionsLoading(prev => ({
      ...prev,
      [jobId]: { ...prev[jobId], run: true }
    }));

    try {
      await jobsApi.run(jobId);
      notify.showSuccess('Job triggered successfully');
    } catch (error) {
      console.error('Failed to run job:', error);
      notify.showError(`Failed to run job: ${error.message}`);
    } finally {
      setJobActionsLoading(prev => ({
        ...prev,
        [jobId]: { ...prev[jobId], run: false }
      }));
    }
  };

  return (
    <ErrorBoundary>
      <div className="dashboard">
        <h1>Dashboard</h1>

        {loading ? (
          <LoadingSpinner message="Loading dashboard data..." />
        ) : (
          <>
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
                      disabled={job.folder_is_active || jobActionsLoading[job.id]?.toggle}
                    >
                      {jobActionsLoading[job.id]?.toggle ? 'Processing...' : job.enabled ? 'Disable' : 'Enable'}
                    </button>
                    <button
                      onClick={() => handleRunJob(job.id)}
                      disabled={!job.enabled || !job.folder_is_active || jobActionsLoading[job.id]?.run}
                    >
                      {jobActionsLoading[job.id]?.run ? 'Running...' : 'Run Now'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </ErrorBoundary>
  )
}
