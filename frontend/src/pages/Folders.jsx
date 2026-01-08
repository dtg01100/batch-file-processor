import { useState } from 'react'
import { foldersApi, testConnectionApi } from '../services/api'
import {
  CONNECTION_TYPES,
  CONNECTION_TYPE_LABELS,
  CONNECTION_FIELDS,
} from '../services/constants'


export default function Folders() {
  const [folders, setFolders] = useState([])
  const [editingFolder, setEditingFolder] = useState(null)
  const [testingConnection, setTestingConnection] = useState(false)
  const [testResult, setTestResult] = useState(null)

  useEffect(() => {
    fetchFolders()
  }, [])

  const fetchFolders = async () => {
    try {
      const response = await foldersApi.list()
      setFolders(response.data)
    } catch (error) {
      console.error('Failed to fetch folders:', error)
    }
  }

  const handleCreateFolder = async (folderData) => {
    try {
      const response = await foldersApi.create(folderData)
      setFolders([...folders, response.data])
    } catch (error) {
      console.error('Failed to create folder:', error)
      alert('Failed to create folder')
    }
  }

  const handleUpdateFolder = async (id, folderData) => {
    try {
      const response = await foldersApi.update(id, folderData)
      setFolders(folders.map(f => f.id === id ? response.data : f))
      setEditingFolder(null)
    } catch (error) {
      console.error('Failed to update folder:', error)
      alert('Failed to update folder')
    }
  }

  const handleDeleteFolder = async (id) => {
    if (!confirm('Are you sure you want to delete this folder?')) {
      return
    }

    try {
      await foldersApi.delete(id)
      setFolders(folders.filter(f => f.id !== id))
    } catch (error) {
      console.error('Failed to delete folder:', error)
      alert('Failed to delete folder')
    }
  }

  const handleTestConnection = async () => {
    if (!editingFolder) return

    setTestingConnection(true)
    setTestResult(null)

    try {
      const connectionConfig = {
        connection_type: editingFolder.connection_type,
        connection_params: editingFolder.connection_params,
      }

      const response = await testConnectionApi.test(connectionConfig)
      setTestResult(response.data)
    } catch (error) {
      setTestResult({
        success: false,
        message: error.message || 'Connection test failed',
      })
    } finally {
      setTestingConnection(false)
    }
  }

  const renderConnectionForm = () => {
    const connectionType = editingFolder?.connection_type || CONNECTION_TYPES.LOCAL
    const connectionParams = editingFolder?.connection_params || {}
    const fields = CONNECTION_FIELDS[connectionType] || []

    return (
      <div className="connection-form">
        <h3>Connection Settings</h3>
        <div className="form-group">
          <label>Connection Type</label>
          <select
            value={connectionType}
            onChange={(e) => setEditingFolder({
              ...editingFolder,
              connection_type: e.target.value,
            })}
            disabled={!editingFolder}
          >
            {Object.entries(CONNECTION_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </div>

        {fields.map(field => (
          <div key={field.name} className="form-group">
            <label>{field.label}</label>
            {field.type === 'password' ? (
              <input
                type={field.type}
                name={field.name}
                placeholder={field.placeholder}
                defaultValue={connectionParams[field.name] || ''}
                onChange={(e) => setEditingFolder({
                  ...editingFolder,
                  connection_params: {
                    ...connectionParams,
                    [field.name]: e.target.value,
                  },
                })}
              />
            ) : field.type === 'select' ? (
              <select
                name={field.name}
                defaultValue={field.default}
                onChange={(e) => setEditingFolder({
                  ...editingFolder,
                  connection_params: {
                    ...connectionParams,
                    [field.name]: e.target.value,
                  },
                })}
              >
                <option value="true">Yes</option>
                <option value="false">No</option>
              </select>
            ) : (
              <input
                type={field.type}
                name={field.name}
                placeholder={field.placeholder}
                defaultValue={connectionParams[field.name] || field.default}
                onChange={(e) => setEditingFolder({
                  ...editingFolder,
                  connection_params: {
                    ...connectionParams,
                    [field.name]: field.type === 'number' ? parseInt(e.target.value) : e.target.value,
                  },
                })}
              />
            )}
          </div>
        ))}

        <button
          type="button"
          onClick={handleTestConnection}
          disabled={!editingFolder || testingConnection}
        >
          {testingConnection ? 'Testing...' : 'Test Connection'}
        </button>

        {testResult && (
          <div className={`test-result ${testResult.success ? 'success' : 'error'}`}>
            {testResult.success ? '✓' : '✗'} {testResult.message}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Folders</h1>
        <button onClick={() => setEditingFolder({})}>
          + New Folder
        </button>
      </div>

      <div className="folders-list">
        {folders.map(folder => (
          <div key={folder.id} className="folder-card">
            <div className="folder-header">
              <h3>{folder.alias || 'Unnamed'}</h3>
              <span className={`status-badge ${folder.folder_is_active ? 'active' : 'inactive'}`}>
                {folder.folder_is_active ? 'Active' : 'Inactive'}
              </span>
            </div>

            <div className="folder-details">
              <p><strong>Type:</strong> {CONNECTION_TYPE_LABELS[folder.connection_type] || 'Local'}</p>
              <p><strong>Path:</strong> {folder.folder_name}</p>
              <p><strong>Schedule:</strong> {folder.schedule || 'Not scheduled'}</p>
              <p><strong>Output Format:</strong> {folder.convert_to_format || 'csv'}</p>
            </div>

            <div className="folder-actions">
              <button onClick={() => setEditingFolder(folder)}>Edit</button>
              <button
                onClick={() => handleDeleteFolder(folder.id)}
                className="delete-btn"
              >
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>

      {editingFolder && (
        <div className="modal">
          <div className="modal-content">
            <h2>{editingFolder.id ? 'Edit Folder' : 'New Folder'}</h2>

            <div className="form-grid">
              <div className="form-section">
                <h3>Basic Settings</h3>
                <div className="form-group">
                  <label>Alias</label>
                  <input
                    type="text"
                    defaultValue={editingFolder.alias || ''}
                    onChange={(e) => setEditingFolder({
                      ...editingFolder,
                      alias: e.target.value,
                    })}
                  />
                </div>

                <div className="form-group">
                  <label>Folder Path</label>
                  {editingFolder.connection_type === CONNECTION_TYPES.LOCAL ? (
                    <input
                      type="text"
                      defaultValue={editingFolder.folder_name || ''}
                      onChange={(e) => setEditingFolder({
                        ...editingFolder,
                        folder_name: e.target.value,
                      })}
                    />
                  ) : (
                    <p className="info-text">
                      Configure in Connection Settings below
                    </p>
                  )}
                </div>

                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      defaultChecked={editingFolder.folder_is_active !== false}
                      onChange={(e) => setEditingFolder({
                        ...editingFolder,
                        folder_is_active: e.target.checked,
                      })}
                    />
                    <span>Active</span>
                  </label>
                </div>
              </div>

              {renderConnectionForm()}

              <div className="form-section">
                <h3>Output Format</h3>
                <div className="form-group">
                  <label>Convert To</label>
                  <select
                    defaultValue={editingFolder.convert_to_format || 'csv'}
                    onChange={(e) => setEditingFolder({
                      ...editingFolder,
                      convert_to_format: e.target.value,
                    })}
                  >
                    <option value="csv">CSV</option>
                    <option value="estore_einvoice">eStore eInvoice</option>
                    <option value="estore_einvoice_generic">eStore eInvoice Generic</option>
                    <option value="fintech">Fintech</option>
                    <option value="scannerware">Scannerware</option>
                    <option value="scansheet_type_a">Scansheet Type A</option>
                    <option value="simplified_csv">Simplified CSV</option>
                    <option value="stewarts_custom">Stewart's Custom</option>
                    <option value="yellowdog_csv">Yellowdog CSV</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>
                    <input
                      type="checkbox"
                      defaultChecked={editingFolder.process_edi}
                      onChange={(e) => setEditingFolder({
                        ...editingFolder,
                        process_edi: e.target.checked,
                      })}
                    />
                    <span>Process EDI</span>
                  </label>
                </div>

                <div className="form-section">
                  <h3>Backends</h3>
                  <div className="checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        defaultChecked={editingFolder.process_backend_copy}
                        onChange={(e) => setEditingFolder({
                          ...editingFolder,
                          process_backend_copy: e.target.checked,
                        })}
                      />
                      <span>Copy to Directory</span>
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        defaultChecked={editingFolder.process_backend_ftp}
                        onChange={(e) => setEditingFolder({
                          ...editingFolder,
                          process_backend_ftp: e.target.checked,
                        })}
                      />
                      <span>FTP Upload</span>
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        defaultChecked={editingFolder.process_backend_email}
                        onChange={(e) => setEditingFolder({
                          ...editingFolder,
                          process_backend_email: e.target.checked,
                        })}
                      />
                      <span>Email</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="modal-actions">
                <button onClick={() => handleUpdateFolder(editingFolder.id, editingFolder)}>
                  Save
                </button>
                <button onClick={() => setEditingFolder(null)}>
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
