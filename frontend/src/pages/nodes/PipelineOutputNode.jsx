/** Pipeline Output Node
 * 
 * Output destination supporting multiple protocols:
 * - Local filesystem
 * - SMB/CIFS (Windows shares)
 * - FTP/SFTP
 * - Email (send as attachment)
 * - API endpoint (POST)
 * - Database table
 * - HTTP webhook
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const outputProtocols = [
  { 
    value: 'local', 
    label: 'Local', 
    icon: '📁', 
    color: '#4CAF50',
    fields: [
      { key: 'path', label: 'Output Path', type: 'text', placeholder: '/path/to/output' },
      { key: 'naming', label: 'File Naming Pattern', type: 'text', placeholder: '{{timestamp}}_{{original}}' }
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
      { key: 'path', label: 'Share Path', type: 'text', placeholder: '/shared/folder' },
      { key: 'naming', label: 'File Naming Pattern', type: 'text', placeholder: '{{timestamp}}_{{original}}' }
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
      { key: 'path', label: 'Remote Path', type: 'text', placeholder: '/outgoing' },
      { key: 'secure', label: 'Use SFTP', type: 'checkbox' }
    ]
  },
  { 
    value: 'email', 
    label: 'Email', 
    icon: '📧', 
    color: '#E91E63',
    fields: [
      { key: 'to', label: 'To Email', type: 'text', placeholder: 'recipient@example.com' },
      { key: 'subject', label: 'Subject', type: 'text', placeholder: 'Data export' },
      { key: 'body', label: 'Body', type: 'textarea', placeholder: 'Please find your data attached.' },
      { key: 'attachmentName', label: 'Attachment Name', type: 'text', placeholder: 'export_{{date}}.csv' }
    ]
  },
  { 
    value: 'api', 
    label: 'API Endpoint', 
    icon: '🌍', 
    color: '#9C27B0',
    fields: [
      { key: 'url', label: 'API URL', type: 'text', placeholder: 'https://api.example.com/data' },
      { key: 'method', label: 'Method', type: 'select', options: ['POST', 'PUT', 'PATCH'] },
      { key: 'contentType', label: 'Content-Type', type: 'select', options: ['application/json', 'application/xml', 'multipart/form-data'] },
      { key: 'authType', label: 'Auth', type: 'select', options: ['none', 'bearer', 'basic', 'apikey'] },
      { key: 'authValue', label: 'Auth Value', type: 'password', placeholder: 'token or key' }
    ]
  },
  { 
    value: 'database', 
    label: 'Database', 
    icon: '🗄️', 
    color: '#00BCD4',
    fields: [
      { key: 'connection', label: 'Connection', type: 'select', options: ['Use active connection', 'New connection'] },
      { key: 'table', label: 'Table Name', type: 'text', placeholder: 'output_table' },
      { key: 'mode', label: 'Write Mode', type: 'select', options: ['insert', 'upsert', 'replace', 'append'] }
    ]
  },
  { 
    value: 'webhook', 
    label: 'Webhook', 
    icon: '🔔', 
    color: '#795548',
    fields: [
      { key: 'url', label: 'Webhook URL', type: 'text', placeholder: 'https://hooks.example.com/trigger' },
      { key: 'method', label: 'Method', type: 'select', options: ['POST', 'PUT'] }
    ]
  },
];

function PipelineOutputNode({ data, selected, onUpdate }) {
  const [showEditor, setShowEditor] = useState(false);
  
  const protocolInfo = outputProtocols.find(p => p.value === data.protocol) || outputProtocols[0];
  const config = data.config || {};
  
  return (
    <div 
      className={`pipeline-node output-node ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : protocolInfo.color,
        backgroundColor: selected ? '#EFEBE9' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setShowEditor(true)}
      title="Double-click to configure output destination"
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: protocolInfo.color }}
      />
      
      <div className="node-content">
        <div className="node-icon" style={{ color: protocolInfo.color }}>
          {protocolInfo.icon}
        </div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Output'}</div>
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
        <OutputEditor
          protocol={data.protocol || 'local'}
          config={config}
          onUpdate={(p, c) => {
            onUpdate?.(data.id, { protocol: p, config: c });
          }}
          onClose={() => setShowEditor(false)}
        />
      )}
      
      <style>{`
        .pipeline-node.output-node {
          min-width: 160px;
          border: 2px solid #795548;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.output-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.output-node.selected {
          border-color: #2196F3;
          background-color: #EFEBE9;
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
      return `${c.host || 'host'}:${c.path || '/out'}`;
    case 'email':
      return `📧 ${c.to || 'no recipient'}`;
    case 'api':
      return c.url || 'No URL set';
    case 'database':
      return `🗄️ ${c.table || 'no table'}`;
    case 'webhook':
      return c.url || 'No webhook URL';
    default:
      return 'No destination configured';
  }
}

// Output editor component
function OutputEditor({ protocol, config, onUpdate, onClose }) {
  const [localProtocol, setLocalProtocol] = useState(protocol);
  const [localConfig, setLocalConfig] = useState(config);
  
  const protocolInfo = outputProtocols.find(p => p.value === localProtocol) || outputProtocols[0];
  
  const updateConfig = (key, value) => {
    setLocalConfig({ ...localConfig, [key]: value });
  };
  
  const saveAndClose = () => {
    onUpdate(localProtocol, localConfig);
    onClose();
  };
  
  return (
    <div className="output-overlay">
      <div className="output-editor">
        <div className="output-header">
          <h3>📤 Output Destination</h3>
          <button className="output-close" onClick={onClose}>×</button>
        </div>
        
        <div className="output-content">
          {/* Protocol selector */}
          <div className="output-section">
            <label>Destination Type</label>
            <div className="protocol-grid">
              {outputProtocols.map((p) => (
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
          <div className="output-section">
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
                      rows={3}
                    />
                  </>
                )}
              </div>
            ))}
          </div>
          
          {/* Naming patterns (for file-based outputs) */}
          {['local', 'smb'].includes(localProtocol) && (
            <div className="output-section">
              <label>File Naming Variables</label>
              <div className="var-chips">
                <span className="var-chip">{{original}}</span>
                <span className="var-chip">{{timestamp}}</span>
                <span className="var-chip">{{date}}</span>
                <span className="var-chip">{{uuid}}</span>
                <span className="var-chip">{{counter}}</span>
              </div>
            </div>
          )}
        </div>
        
        <div className="output-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn" onClick={saveAndClose}>✓ Apply</button>
        </div>
      </div>
      
      <style>{`
        .output-overlay {
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
        
        .output-editor {
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          width: 450px;
          max-height: 500px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .output-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, #795548 0%, #5D4037 100%);
          color: #fff;
        }
        
        .output-header h3 {
          margin: 0;
          font-size: 16px;
        }
        
        .output-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .output-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        
        .output-section {
          margin-bottom: 16px;
        }
        
        .output-section > label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .protocol-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 6px;
        }
        
        .protocol-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 8px 6px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .protocol-btn.active {
          border-width: 2px;
          background: #EFEBE9;
        }
        
        .protocol-icon {
          font-size: 20px;
          margin-bottom: 4px;
        }
        
        .protocol-label {
          font-size: 10px;
          font-weight: 600;
          color: #333;
          text-align: center;
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
        
        .var-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        
        .var-chip {
          padding: 4px 10px;
          background: #f5f5f5;
          border-radius: 12px;
          font-size: 11px;
          font-family: monospace;
          color: #795548;
        }
        
        .output-footer {
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
          background: #795548;
          color: #fff;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}

export default memo(PipelineOutputNode);
