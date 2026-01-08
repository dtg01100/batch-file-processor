import { useState, useEffect } from 'react'
import { foldersApi, jobsApi, outputProfilesApi } from '../services/api'


export default function Jobs() {
  const [folders, setFolders] = useState([])
  const [jobs, setJobs] = useState([])
  const [editingJob, setEditingJob] = useState(null)

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
    } catch (error) {
      console.error('Failed to fetch data:', error)
    }
  }

  const handleCreateJob = async (jobData) => {
    try {
      const response = await jobsApi.create(jobData)
      setJobs([...jobs, response.data])
      setEditingJob(null)
    } catch (error) {
      console.error('Failed to create job:', error)
      alert('Failed to create job')
    }
  }

  const handleUpdateJob = async (jobId, jobData) => {
    try {
      const response = await jobsApi.update(jobId, jobData)
      setJobs(jobs.map(j => j.id === jobId ? response.data : j))
      setEditingJob(null)
    } catch (error) {
      console.error('Failed to update job:', error)
      alert('Failed to update job')
    }
  }

  const handleDeleteJob = async (jobId) => {
    if (!confirm('Are you sure you want to delete this job?')) {
      return
    }

    try {
      await jobsApi.delete(jobId)
      setJobs(jobs.filter(j => j.id !== jobId))
    } catch (error) {
      console.error('Failed to delete job:', error)
      alert('Failed to delete job')
    }
  }

  const handleRunJob = async (jobId) => {
    try {
      await jobsApi.run(jobId)
      console.log('Job triggered:', jobId)
    } catch (error) {
      console.error('Failed to run job:', error)
      alert('Failed to run job')
    }
  }

  const handleToggleJob = async (jobId) => {
    try {
      const response = await jobsApi.toggle(jobId)
      setJobs(jobs.map(j => j.id === jobId ? response.data : j))
    } catch (error) {
      console.error('Failed to toggle job:', error)
      alert('Failed to toggle job')
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Jobs</h1>
        <button onClick={() => setEditingJob({})}>
          + New Job
        </button>
      </div>

      <div className="jobs-list">
        {jobs.map(job => {
          const folder = folders.find(f => f.id === job.folder_id)
          return (
            <div key={job.id} className="job-card">
              <div className="job-header">
                <h3>{job.folder_alias}</h3>
                <span className={`job-status ${job.enabled ? 'enabled' : 'disabled'}`}>
                  {job.enabled ? 'Scheduled' : 'Disabled'}
                </span>
              </div>

              <div className="job-details">
                <p><strong>Folder:</strong> {folder ? folder.alias : 'Unknown'}</p>
                <p><strong>Schedule:</strong> {job.cron_expression || 'Not scheduled'}</p>
                <p><strong>Next Run:</strong> {job.next_run || 'Not scheduled'}</p>
              </div>

              <div className="job-actions">
                <button onClick={() => handleRunJob(job.id)} disabled={!job.enabled}>
                  Run Now
                </button>
                <button onClick={() => handleToggleJob(job.id)}>
                  {job.enabled ? 'Disable' : 'Enable'}
                </button>
                <button
                  onClick={() => setEditingJob(job)}
                  className="edit-btn"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDeleteJob(job.id)}
                  className="delete-btn"
                >
                  Delete
                </button>
              </div>
            </div>
          )
        })}
      </div>

      {editingJob && (
        <div className="modal">
          <div className="modal-content">
            <h2>{editingJob.id ? 'Edit Job' : 'New Job'}</h2>

            <div className="form-grid">
              <div className="form-section">
                <h3>Basic Settings</h3>

                <div className="form-group">
                  <label>Folder</label>
                  <select
                    value={editingJob.folder_id || ''}
                    onChange={(e) => setEditingJob({
                      ...editingJob,
                      folder_id: parseInt(e.target.value),
                    })}
                  >
                    <option value="">Select a folder...</option>
                    {folders.map(folder => (
                      <option key={folder.id} value={folder.id}>
                        {folder.alias} ({folder.folder_name})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group checkbox">
                  <label>
                    <input
                      type="checkbox"
                      defaultChecked={editingJob.enabled !== false}
                      onChange={(e) => setEditingJob({
                        ...editingJob,
                        enabled: e.target.checked,
                      })}
                    />
                    <span>Enabled</span>
                  </label>
                </div>

                <div className="form-group">
                  <label>Output Profile</label>
                  <select
                    value={editingJob.output_profile_id || ''}
                    onChange={(e) => setEditingJob({
                      ...editingJob,
                      output_profile_id: parseInt(e.target.value) || null,
                    })}
                  >
                    <option value="">Use Default Profile</option>
                    {folders.map(folder => {
                      // Find all output profiles
                      const profiles = outputProfiles || [];
                      return profiles.map(profile => (
                        <option key={profile.id} value={profile.id}>
                          {profile.alias || profile.name}
                          {profile.is_default && ' (Default)'}
                        </option>
                      ));
                    })}
                  </select>
                  <small>Select a saved output configuration or use default</small>
                </div>
              </div>

                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      defaultChecked={editingJob.enabled !== false}
                      onChange={(e) => setEditingJob({
                        ...editingJob,
                        enabled: e.target.checked,
                      })}
                    />
                    <span>Enabled</span>
                  </label>
                </div>
              </div>

              <div className="form-section">
                <h3>Schedule</h3>
                
                <div className="form-group">
                  <label>Cron Expression</label>
                  <input
                    type="text"
                    defaultValue={editingJob.cron_expression || ''}
                    placeholder="0 9 * * * (Daily at 9am)"
                    onChange={(e) => setEditingJob({
                      ...editingJob,
                      cron_expression: e.target.value,
                    })}
                  />
                  <div className="help-text">
                    <p>Format: minute hour day month day_of_week</p>
                    <p>Examples:</p>
                    <ul>
                      <li><code>0 9 * * *</code> - Daily at 9am</li>
                      <li><code>0 */4 * *</code> - Every 4 hours</li>
                      <li><code>0 9 * * 1</code> - Every Monday at 9am</li>
                    </ul>
                  </div>
                </div>
              </div>

              <div className="modal-actions">
                <button onClick={() => handleUpdateJob(editingJob.id, editingJob)}>
                  Save
                </button>
                <button onClick={() => setEditingJob(null)}>
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
