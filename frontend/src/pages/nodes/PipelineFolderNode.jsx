/** Pipeline Folder Source Node
 * 
 * Input source supporting multiple protocols:
 * - Local filesystem
 * - SMB/CIFS (Windows shares)
 * - FTP/SFTP
 * - S3 (Amazon S3)
 * - Azure Blob Storage
 * - Google Cloud Storage
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const protocols = [
  { 
    value: 'local', 
    label: 'Local', 
    icon: '📁', 
    color: '#4CAF50',
    fields: [
      { key: 'path', label: 'Folder Path', type: 'text', placeholder: '/path/to/folder' }
    ]
  },
  { 
    value: 'smb', 
    label: 'SMB/CIFS', 
    icon: '🖥️', 
    color: '#2196F3',
    fields: [
      { key: 'server', label: 'Server', type: 'text', placeholder: '//server/share' },
      { key: 'username', label: 'Username', type: 'text', placeholder: 'domain\\user' },
      { key: 'password', label: 'Password', type: 'password', placeholder: '********' },
      { key: 'path', label: 'Share Path', type: 'text', placeholder: '/shared/folder' }
    ]
  },
  { 
    value: 'ftp', 
    label: 'FTP/SFTP', 
    icon: '🌐', 
    color: '#FF9800',
    fields: [
      { key: 'host', label: 'Host', type: 'text', placeholder: 'ftp.example.com' },
      { key: 'port', label: 'Port', type: 'number', placeholder: '21 (FTP) or 22 (SFTP)' },
      { key: 'username', label: 'Username', type: 'text', placeholder: 'ftp_user' },
      { key: 'password', label: 'Password', type: 'password', placeholder: '********' },
      { key: 'path', label: 'Remote Path', type: 'text', placeholder: '/incoming' },
      { key: 'secure', label: 'Use SFTP', type: 'checkbox' }
    ]
  },
  { 
    value: 's3', 
    label: 'Amazon S3', 
    icon: '☁️', 
    color: '#FF9900',
    fields: [
      { key: 'bucket', label: 'Bucket Name', type: 'text', placeholder: 'my-bucket' },
      { key: 'prefix', label: 'Prefix', type: 'text', placeholder: 'input/' },
      { key: 'region', label: 'Region', type: 'select', options: ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1'] },
      { key: 'accessKey', label: 'Access Key ID', type: 'text', placeholder: 'AKIA...' },
      { key: 'secretKey', label: 'Secret Access Key', type: 'password', placeholder: '********' }
    ]
  },
  { 
    value: 'azure', 
    label: 'Azure Blob', 
    icon: '🔵', 
    color: '#0078D4',
    fields: [
      { key: 'account', label: 'Storage Account', type: 'text', placeholder: 'mystorage' },
      { key: 'container', label: 'Container', type: 'text', placeholder: 'input-container' },
      { key: 'prefix', label: 'Prefix', type: 'text', placeholder: 'folder/' },
      { key: 'sasToken', label: 'SAS Token', type: 'password', placeholder: 'sv=2020-08-04&...' },
    ]
  },
  { 
    value: 'gcs', 
    label: 'Google Cloud', 
    icon: '🔶', 
    color: '#4285F4',
    fields: [
      { key: 'project', label: 'Project ID', type: 'text', placeholder: 'my-project' },
      { key: 'bucket', label: 'Bucket', type: 'text', placeholder: 'input-bucket' },
      { key: 'prefix', label: 'Prefix', type: 'text', placeholder: 'data/' },
      { key: 'credentials', label: 'JSON Key', type: 'textarea', placeholder: '{"type": "service_account"...}' }
    ]
  },
];

function PipelineFolderNode({ data, selected, onUpdate }) {
  const [showEditor, setShowEditor] = useState(false);
  
  const protocolInfo = protocols.find(p => p.value === data.protocol) || protocols[0];
  const config = data.config || {};
  
  return (
    <div 
      className={`pipeline-node folder-source ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : protocolInfo.color,
        backgroundColor: selected ? '#E8F5E9' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setShowEditor(true)}
      title="Double-click to configure input source"
    >
      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: protocolInfo.color }}
      />
      
      <div className="node-content">
        <div className="node-icon" style={{ color: protocolInfo.color }}>
          {protocolInfo.icon}
        </div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Input'}</div>
          <div className="node-protocol">
            <span className="protocol-badge" style={{ backgroundColor: protocolInfo.color }}>
              {protocolInfo.label}
            </span>
          </div>
          <div className="node-path">
            {getDisplayPath(data)}
          </div>
        </div>
      </div>
      
      {showEditor && (
        <FolderEditor
          protocol={data.protocol || 'local'}
          config={config}
          filePattern={data.filePattern || '*.csv'}
          onUpdate={(p, c, fp) => {
            onUpdate?.(data.id, { protocol: p, config: c, filePattern: fp });
          }}
          onClose={() => setShowEditor(false)}
        />
      )}
      
      <style>{`
        .pipeline-node.folder-source {
          min-width: 180px;
          border: 2px solid #4CAF50;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.folder-source:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.folder-source.selected {
          border-color: #2196F3;
          background-color: #E8F5E9;
        }
        
        .node-content {
          padding: 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .node-icon {
          font-size: 28px;
        }
        
        .node-text {
          flex: 1;
          min-width: 0;
        }
        
        .node-label {
          font-weight: 600;
          font-size: 13px;
          color: #333;
        }
        
        .node-protocol {
          margin-top: 4px;
        }
        
        .protocol-badge {
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 10px;
          color: #fff;
          font-weight: 600;
        }
        
        .node-path {
          font-size: 10px;
          color: #666;
          margin-top: 2px;
          font-family: monospace;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .node-handle {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          border: 2px solid #fff;
        }
      `}</style>
    </div>
  );
}

// Helper to display path based on protocol
function getDisplayPath(data) {
  const c = data.config || {};
  switch (data.protocol) {
    case 'local':
    case 'smb':
      return c.path || 'No path set';
    case 'ftp':
      return `${c.host || 'host'}:${c.path || '/path'}`;
    case 's3':
      return `${c.bucket || 'bucket'}/${c.prefix || ''}`;
    case 'azure':
      return `${c.account}.blob.core.windows.net/${c.container || 'container'}`;
    case 'gcs':
      return `${c.bucket || 'bucket'}/${c.prefix || ''}`;
    default:
      return 'No source configured';
  }
}

// Folder editor component
function FolderEditor({ protocol, config, filePattern, onUpdate, onClose }) {
  const [localProtocol, setLocalProtocol] = useState(protocol);
  const [localConfig, setLocalConfig] = useState(config);
  const [localFilePattern, setLocalFilePattern] = useState(filePattern);
  
  const protocolInfo = protocols.find(p => p.value === localProtocol) || protocols[0];
  
  const updateConfig = (key, value) => {
    setLocalConfig({ ...localConfig, [key]: value });
  };
  
  const saveAndClose = () => {
    onUpdate(localProtocol, localConfig, localFilePattern);
    onClose();
  };
  
  return (
    <div className="folder-overlay">
      <div className="folder-editor">
        <div className="folder-header">
          <h3>📥 Input Source</h3>
          <button className="folder-close" onClick={onClose}>×</button>
        </div>
        
        <div className="folder-content">
          {/* Protocol selector */}
          <div className="folder-section">
            <label>Protocol</label>
            <div className="protocol-grid">
              {protocols.map((p) => (
                <button
                  key={p.value}
                  className={`protocol-btn ${localProtocol === p.value ? 'active' : ''}`}
                  style={{ borderColor: p.color }}
                  onClick={() => setLocalProtocol(p.value)}
                >
                  <span className="protocol-icon">{p.icon}</span>
                  <span className="protocol-label">{p.label}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Protocol-specific fields */}
          <div className="folder-section">
            <label>{protocolInfo.label} Configuration</label>
            {protocolInfo.fields.map((field) => (
              <div key={field.key} className="config-field">
                {field.type === 'text' && (
                  <>
                    <label>{field.label}</label>
                    <input
                      type="text"
                      value={localConfig[field.key] || ''}
                      onChange={(e) => updateConfig(field.key, e.target.value)}
                      placeholder={field.placeholder}
                    />
                  </>
                )}
                {field.type === 'password' && (
                  <>
                    <label>{field.label}</label>
                    <input
                      type="password"
                      value={localConfig[field.key] || ''}
                      onChange={(e) => updateConfig(field.key, e.target.value)}
                      placeholder={field.placeholder}
                    />
                  </>
                )}
                {field.type === 'number' && (
                  <>
                    <label>{field.label}</label>
                    <input
                      type="number"
                      value={localConfig[field.key] || ''}
                      onChange={(e) => updateConfig(field.key, e.target.value)}
                      placeholder={field.placeholder}
                    />
                  </>
                )}
                {field.type === 'select' && (
                  <>
                    <label>{field.label}</label>
                    <select
                      value={localConfig[field.key] || ''}
                      onChange={(e) => updateConfig(field.key, e.target.value)}
                    >
                      <option value="">Select...</option>
                      {field.options?.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  </>
                )}
                {field.type === 'checkbox' && (
                  <label className="checkbox-field">
                    <input
                      type="checkbox"
                      checked={localConfig[field.key] || false}
                      onChange={(e) => updateConfig(field.key, e.target.checked)}
                    />
                    <span>{field.label}</span>
                  </label>
                )}
                {field.type === 'textarea' && (
                  <>
                    <label>{field.label}</label>
                    <textarea
                      value={localConfig[field.key] || ''}
                      onChange={(e) => updateConfig(field.key, e.target.value)}
                      placeholder={field.placeholder}
                      rows={4}
                    />
                  </>
                )}
              </div>
            ))}
          </div>
          
          {/* File pattern */}
          <div className="folder-section">
            <label>File Pattern</label>
            <input
              type="text"
              value={localFilePattern}
              onChange={(e) => setLocalFilePattern(e.target.value)}
              placeholder="*.csv, *.txt, *.*"
            />
            <p className="help-text">
              Comma-separated patterns. Use * for wildcards.
            </p>
          </div>
          
          {/* Connection test */}
          <div className="folder-section">
            <button className="test-btn">
              🔗 Test Connection
            </button>
          </div>
        </div>
        
        <div className="folder-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn" onClick={saveAndClose}>✓ Apply</button>
        </div>
      </div>
      
      <style>{`
        .folder-overlay {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0,0,0,0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 100;
          border-radius: 8px;
        }
        
        .folder-editor {
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          width: 450px;
          max-height: 500px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .folder-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);
          color: #fff;
        }
        
        .folder-header h3 {
          margin: 0;
          font-size: 16px;
        }
        
        .folder-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .folder-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        
        .folder-section {
          margin-bottom: 16px;
        }
        
        .folder-section > label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .protocol-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
        }
        
        .protocol-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 10px 8px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .protocol-btn.active {
          border-width: 2px;
          background: #E8F5E9;
        }
        
        .protocol-icon {
          font-size: 24px;
          margin-bottom: 4px;
        }
        
        .protocol-label {
          font-size: 11px;
          font-weight: 600;
          color: #333;
        }
        
        .config-field {
          margin-bottom: 12px;
        }
        
        .config-field label {
          display: block;
          font-size: 11px;
          font-weight: 500;
          color: #666;
          margin-bottom: 4px;
        }
        
        .config-field input,
        .config-field select,
        .config-field textarea {
          width: 100%;
          padding: 8px 10px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 13px;
        }
        
        .config-field textarea {
          font-family: monospace;
          font-size: 11px;
          resize: vertical;
        }
        
        .checkbox-field {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          cursor: pointer;
        }
        
        .help-text {
          font-size: 10px;
          color: #999;
          margin-top: 4px;
        }
        
        .test-btn {
          width: 100%;
          padding: 10px;
          border: 1px dashed #4CAF50;
          border-radius: 6px;
          background: transparent;
          color: #4CAF50;
          cursor: pointer;
          font-size: 13px;
          font-weight: 500;
        }
        
        .test-btn:hover {
          background: #E8F5E9;
        }
        
        .folder-footer {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          padding: 12px 16px;
          border-top: 1px solid #e0e0e0;
        }
        
        .cancel-btn {
          padding: 10px 20px;
          border: 1px solid #ddd;
          border-radius: 6px;
          background: #fff;
          cursor: pointer;
          font-size: 13px;
        }
        
        .save-btn {
          padding: 10px 20px;
          border: none;
          border-radius: 6px;
          background: #4CAF50;
          color: #fff;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}

export default memo(PipelineFolderNode);
