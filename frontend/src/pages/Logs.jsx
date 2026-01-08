import { useState, useEffect } from 'react'
import { runsApi } from '../services/api'
import { RUN_STATUS } from '../services/constants'


export default function Logs() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [logs, setLogs] = useState([])
  const [filterStatus, setFilterStatus] = useState('')
  const [filterFolder, setFilterFolder] = useState('')

  useEffect(() => {
    fetchRuns()
  }, [filterStatus, filterFolder])

  const fetchRuns = async () => {
    try {
      const params = {}
      if (filterStatus) params.status = filterStatus
      if (filterFolder) params.folder_id = parseInt(filterFolder)

      const response = await runsApi.list(params)
      setRuns(response.data)
    } catch (error) {
      console.error('Failed to fetch runs:', error)
    }
  }

  const handleViewLogs = async (runId) => {
    try {
      const response = await runsApi.getLogs(runId)
      setLogs(response.data.logs || [])
      setSelectedRun(response.data)
    } catch (error) {
      console.error('Failed to fetch logs:', error)
      alert('Failed to fetch logs')
    }
  }

  const statusColors = {
    [RUN_STATUS.COMPLETED]: 'completed',
    [RUN_STATUS.FAILED]: 'failed',
    [RUN_STATUS.RUNNING]: 'running',
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Logs</h1>
        
        <div className="filters">
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
          >
            <option value="">All Status</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="running">Running</option>
          </select>

          <input
            type="text"
            placeholder="Filter by folder ID..."
            value={filterFolder}
            onChange={(e) => setFilterFolder(e.target.value)}
          />
        </div>
      </div>

      {!selectedRun ? (
        <div className="runs-list">
          <table>
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Folder</th>
                <th>Started</th>
                <th>Completed</th>
                <th>Status</th>
                <th>Files</th>
                <th>Errors</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => (
                <tr key={run.id}>
                  <td>{run.id}</td>
                  <td>{run.folder_alias}</td>
                  <td>{new Date(run.started_at).toLocaleString()}</td>
                  <td>{run.completed_at ? new Date(run.completed_at).toLocaleString() : '-'}</td>
                  <td>
                    <span className={`status-badge ${statusColors[run.status]}`}>
                      {run.status}
                    </span>
                  </td>
                  <td>{run.files_processed}</td>
                  <td>{run.files_failed}</td>
                  <td>
                    <button onClick={() => handleViewLogs(run.id)}>View Logs</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="logs-detail">
          <div className="logs-header">
            <button onClick={() => setSelectedRun(null)}>← Back to List</button>
            <h2>Run Details - {selectedRun.folder_alias}</h2>
          </div>

          <div className="run-info">
            <p><strong>Run ID:</strong> {selectedRun.id}</p>
            <p><strong>Status:</strong> {selectedRun.status}</p>
            <p><strong>Started:</strong> {new Date(selectedRun.started_at).toLocaleString()}</p>
            <p><strong>Completed:</strong> {selectedRun.completed_at ? new Date(selectedRun.completed_at).toLocaleString() : 'N/A'}</p>
            <p><strong>Files Processed:</strong> {selectedRun.files_processed}</p>
            <p><strong>Errors:</strong> {selectedRun.files_failed}</p>
            {selectedRun.error_message && (
              <p className="error-message"><strong>Error:</strong> {selectedRun.error_message}</p>
            )}
          </div>

          <div className="logs-container">
            <h3>Logs</h3>
            {logs.length > 0 ? (
              logs.map((log, index) => (
                <div key={index} className="log-entry">
                  <div className="log-filename">{log.filename}</div>
                  <pre className="log-content">{log.content}</pre>
                </div>
              ))
            ) : (
              <p className="no-logs">No logs available for this run</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
