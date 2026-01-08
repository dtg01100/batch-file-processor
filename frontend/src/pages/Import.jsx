import { useState } from 'react'
import { importApi } from '../services/api'


export default function Import() {
  const [sourceDbPath, setSourceDbPath] = useState('')
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState(null)
  const [preview, setPreview] = useState(null)

  const handleFileUpload = (event) => {
    const file = event.target.files[0]
    if (file) {
      setSourceDbPath(file.path)
    }
  }

  const handleImport = async () => {
    if (!sourceDbPath) {
      alert('Please select a source database file')
      return
    }

    setImporting(true)
    setResult(null)

    try {
      const response = await importApi.importDatabase(sourceDbPath)
      setResult(response.data)
    } catch (error) {
      setResult({
        success: false,
        message: error.message || 'Import failed',
      })
    } finally {
      setImporting(false)
    }
  }

  const handleShowPreview = () => {
    setPreview(result)
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Import Database</h1>
        <p className="description">
          Import an existing folders.db from the Tkinter interface. Windows paths
          will be automatically converted to remote file system configurations.
        </p>
      </div>

      <div className="import-form">
        <div className="form-section">
          <h2>Step 1: Upload Database</h2>
          <div className="form-group">
            <label>Source Database (folders.db)</label>
            <input
              type="file"
              accept=".db"
              onChange={handleFileUpload}
              disabled={importing}
            />
            <p className="help-text">
              Select the folders.db file from your Tkinter interface installation
            </p>
          </div>
        </div>

        <div className="form-section">
          <button
            onClick={handleImport}
            disabled={!sourceDbPath || importing}
            className="import-btn"
          >
            {importing ? 'Importing...' : 'Import Database'}
          </button>
        </div>

        {result && (
          <div className={`result-box ${result.success ? 'success' : 'error'}`}>
            <h3>{result.success ? '✓ Import Complete' : '✗ Import Failed'}</h3>
            <pre>{JSON.stringify(result, null, 2)}</pre>

            {result.success && (
              <div className="result-actions">
                <button onClick={handleShowPreview}>
                  View Details
                </button>
              </div>
            )}
          </div>
        )}

        {preview && (
          <div className="preview">
            <div className="preview-header">
              <button onClick={() => setPreview(null)}>← Back</button>
              <h2>Import Summary</h2>
            </div>

            <div className="preview-grid">
              <div className="preview-card">
                <h3>Folders</h3>
                <p><strong>Imported:</strong> {preview.folders_imported}</p>
                {preview.folders_errors > 0 && (
                  <p className="error"><strong>Errors:</strong> {preview.folders_errors}</p>
                )}
              </div>

              <div className="preview-card">
                <h3>Processed Files</h3>
                <p><strong>Imported:</strong> {preview.processed_files_imported}</p>
                {preview.processed_files_errors > 0 && (
                  <p className="error"><strong>Errors:</strong> {preview.processed_files_errors}</p>
                )}
              </div>

              <div className="preview-card">
                <h3>Settings</h3>
                <p><strong>Imported:</strong> {preview.settings_imported}</p>
                {preview.settings_errors > 0 && (
                  <p className="error"><strong>Errors:</strong> {preview.settings_errors}</p>
                )}
              </div>

              <div className="preview-card preview-summary">
                <h3>Summary</h3>
                <p><strong>Total Imported:</strong> {preview.total_imported}</p>
                <p><strong>Total Errors:</strong> {preview.total_errors}</p>
                <p><strong>Status:</strong> {preview.success ? 'Success' : 'Failed'}</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
