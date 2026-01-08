/** Pipeline Trigger Node
 * 
 * Trigger node - executes the pipeline or a sub-pipeline.
 * Can be triggered manually, on schedule, or by external events.
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const triggerTypes = [
  { value: 'manual', label: 'Manual', icon: '👆', desc: 'Click to trigger' },
  { value: 'schedule', label: 'Schedule', icon: '⏰', desc: 'Cron-based schedule' },
  { value: 'webhook', label: 'Webhook', icon: '🔔', desc: 'HTTP endpoint' },
  { value: 'event', label: 'Event', icon: '⚡', desc: 'File/directory watch' },
  { value: 'upstream', label: 'Upstream', icon: '🔗', desc: 'Triggered by another pipeline' },
];

function PipelineTriggerNode({ data, selected, onUpdate }) {
  const [showEditor, setShowEditor] = useState(false);
  
  const triggerType = data.triggerType || 'manual';
  const config = data.config || '{}';
  
  const typeInfo = triggerTypes.find(t => t.value === triggerType) || triggerTypes[0];
  
  return (
    <div 
      className={`pipeline-node trigger ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#E91E63',
        backgroundColor: selected ? '#FCE4EC' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setShowEditor(true)}
      title="Double-click to configure trigger"
    >
      {/* Output handle - triggers downstream */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#E91E63' }}
      />
      
      <div className="node-content">
        <div className="node-icon" style={{ color: '#E91E63' }}>⚡</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Trigger'}</div>
          <div className="node-type">
            <span className="type-badge">{typeInfo.icon} {typeInfo.label}</span>
          </div>
          {data.schedule && (
            <div className="node-schedule">
              {data.schedule}
            </div>
          )}
          {data.webhookUrl && (
            <div className="node-webhook">
              🔗 Webhook configured
            </div>
          )}
        </div>
      </div>
      
      {showEditor && (
        <TriggerEditor
          triggerType={triggerType}
          config={config}
          onUpdate={(tt, cfg) => {
            onUpdate?.(data.id, { triggerType: tt, config: JSON.stringify(cfg, null, 2) });
          }}
          onClose={() => setShowEditor(false)}
        />
      )}
      
      <style>{`
        .pipeline-node.trigger {
          min-width: 140px;
          border: 2px solid #E91E63;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.trigger:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.trigger.selected {
          border-color: #2196F3;
          background-color: #FCE4EC;
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
        
        .node-type {
          margin-top: 4px;
        }
        
        .type-badge {
          padding: 2px 8px;
          background: #FCE4EC;
          border-radius: 10px;
          font-size: 10px;
          color: #E91E63;
          font-weight: 600;
        }
        
        .node-schedule,
        .node-webhook {
          font-size: 10px;
          color: #666;
          margin-top: 2px;
          font-family: monospace;
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

// Trigger editor component
function TriggerEditor({ triggerType, config, onUpdate, onClose }) {
  const [localTriggerType, setLocalTriggerType] = useState(triggerType);
  const [localConfig, setLocalConfig] = useState(JSON.parse(config || '{}'));
  
  const configParse = (str, def) => {
    try { return JSON.parse(str); } catch { return def; }
  };
  
  const saveAndClose = () => {
    onUpdate(localTriggerType, localConfig);
    onClose();
  };
  
  return (
    <div className="trigger-overlay">
      <div className="trigger-editor">
        <div className="trigger-header">
          <h3>⚡ Trigger Configuration</h3>
          <button className="trigger-close" onClick={onClose}>×</button>
        </div>
        
        <div className="trigger-content">
          {/* Trigger type */}
          <div className="trigger-section">
            <label>Trigger Type</label>
            <div className="type-grid">
              {triggerTypes.map((type) => (
                <button
                  key={type.value}
                  className={`type-btn ${localTriggerType === type.value ? 'active' : ''}`}
                  onClick={() => setLocalTriggerType(type.value)}
                >
                  <span className="type-icon">{type.icon}</span>
                  <span className="type-label">{type.label}</span>
                  <span className="type-desc">{type.desc}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Schedule config */}
          {localTriggerType === 'schedule' && (
            <div className="trigger-section">
              <label>Cron Schedule</label>
              <input
                type="text"
                value={localConfig.cron || '* * * * *'}
                onChange={(e) => setLocalConfig({ ...localConfig, cron: e.target.value })}
                className="cron-input"
                placeholder="* * * * *"
              />
              <div className="cron-presets">
                <span>Presets:</span>
                <button onClick={() => setLocalConfig({ ...localConfig, cron: '0 * * * *' })}>Hourly</button>
                <button onClick={() => setLocalConfig({ ...localConfig, cron: '0 0 * * *' })}>Daily</button>
                <button onClick={() => setLocalConfig({ ...localConfig, cron: '0 0 * * 0' })}>Weekly</button>
                <button onClick={() => setLocalConfig({ ...localConfig, cron: '0 0 1 * *' })}>Monthly</button>
              </div>
              <p className="cron-help">
                Format: minute hour day month weekday<br/>
                <code>*</code> any, <code>,</code> list, <code>-</code> range
              </p>
            </div>
          )}
          
          {/* Webhook config */}
          {localTriggerType === 'webhook' && (
            <div className="trigger-section">
              <label>Webhook URL</label>
              <div className="webhook-url">
                <code>/api/triggers/{localConfig.triggerId || 'unique-id'}</code>
                <button className="copy-btn" onClick={() => navigator.clipboard.writeText(`/api/triggers/${localConfig.triggerId || 'unique-id'}`)}>
                  📋 Copy
                </button>
              </div>
              <p className="webhook-help">
                POST to this URL to trigger the pipeline
              </p>
            </div>
          )}
          
          {/* Event config */}
          {localTriggerType === 'event' && (
            <div className="trigger-section">
              <label>Watch Path</label>
              <input
                type="text"
                value={localConfig.watchPath || ''}
                onChange={(e) => setLocalConfig({ ...localConfig, watchPath: e.target.value })}
                className="path-input"
                placeholder="/path/to/watch"
              />
              <label style={{ marginTop: '12px', display: 'block' }}>Event Types</label>
              <div className="checkbox-group">
                <label><input type="checkbox" checked={localConfig.onCreate !== false} onChange={(e) => setLocalConfig({ ...localConfig, onCreate: e.target.checked })} /> File created</label>
                <label><input type="checkbox" checked={localConfig.onModify !== false} onChange={(e) => setLocalConfig({ ...localConfig, onModify: e.target.checked })} /> File modified</label>
                <label><input type="checkbox" checked={localConfig.onDelete} onChange={(e) => setLocalConfig({ ...localConfig, onDelete: e.target.checked })} /> File deleted</label>
              </div>
            </div>
          )}
          
          {/* Upstream config */}
          {localTriggerType === 'upstream' && (
            <div className="trigger-section">
              <label>Upstream Pipeline ID</label>
              <input
                type="text"
                value={localConfig.upstreamPipeline || ''}
                onChange={(e) => setLocalConfig({ ...localConfig, upstreamPipeline: e.target.value })}
                className="pipeline-input"
                placeholder="pipeline-id-to-watch"
              />
            </div>
          )}
          
          {/* Visual preview */}
          <div className="trigger-preview">
            <div className="preview-title">Trigger Flow</div>
            <div className="preview-diagram">
              <div className="preview-trigger">
                <span className="preview-icon">⚡</span>
                <span>{triggerTypes.find(t => t.value === localTriggerType)?.label}</span>
              </div>
              <span className="preview-arrow">→</span>
              <div className="preview-pipeline">
                <span className="preview-icon">📋</span>
                <span>Pipeline</span>
              </div>
            </div>
          </div>
        </div>
        
        <div className="trigger-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn" onClick={saveAndClose}>✓ Apply</button>
        </div>
      </div>
      
      <style>{`
        .trigger-overlay {
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
        
        .trigger-editor {
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          width: 420px;
          max-height: 500px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .trigger-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, #E91E63 0%, #C2185B 100%);
          color: #fff;
        }
        
        .trigger-header h3 {
          margin: 0;
          font-size: 16px;
        }
        
        .trigger-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .trigger-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        
        .trigger-section {
          margin-bottom: 16px;
        }
        
        .trigger-section label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .type-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
        }
        
        .type-btn {
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
        
        .type-btn.active {
          border-color: #E91E63;
          background: #FCE4EC;
        }
        
        .type-icon {
          font-size: 20px;
          margin-bottom: 4px;
        }
        
        .type-label {
          font-size: 11px;
          font-weight: 600;
          color: #333;
        }
        
        .type-desc {
          font-size: 9px;
          color: #999;
          text-align: center;
          margin-top: 2px;
        }
        
        .cron-input {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-family: monospace;
          font-size: 14px;
        }
        
        .cron-presets {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 8px;
          flex-wrap: wrap;
        }
        
        .cron-presets span {
          font-size: 11px;
          color: #666;
        }
        
        .cron-presets button {
          padding: 4px 10px;
          border: 1px solid #ddd;
          border-radius: 12px;
          background: #fff;
          cursor: pointer;
          font-size: 10px;
        }
        
        .cron-presets button:hover {
          border-color: #E91E63;
          background: #FCE4EC;
        }
        
        .cron-help {
          font-size: 10px;
          color: #999;
          margin-top: 8px;
          line-height: 1.6;
        }
        
        .webhook-url {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          background: #f5f5f5;
          border-radius: 6px;
        }
        
        .webhook-url code {
          flex: 1;
          font-size: 12px;
          font-family: monospace;
        }
        
        .copy-btn {
          padding: 4px 10px;
          border: none;
          border-radius: 4px;
          background: #E91E63;
          color: #fff;
          cursor: pointer;
          font-size: 11px;
        }
        
        .webhook-help {
          font-size: 11px;
          color: #666;
          margin-top: 8px;
        }
        
        .path-input,
        .pipeline-input {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 13px;
        }
        
        .checkbox-group {
          display: flex;
          flex-direction: column;
          gap: 8px;
          margin-top: 8px;
        }
        
        .checkbox-group label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          cursor: pointer;
        }
        
        .trigger-preview {
          margin-top: 16px;
          padding: 12px;
          background: #f5f5f5;
          border-radius: 8px;
        }
        
        .preview-title {
          font-size: 11px;
          font-weight: 600;
          color: #666;
          margin-bottom: 10px;
        }
        
        .preview-diagram {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
        }
        
        .preview-trigger,
        .preview-pipeline {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 500;
        }
        
        .preview-trigger {
          background: #FCE4EC;
          color: #E91E63;
        }
        
        .preview-pipeline {
          background: #E8F5E9;
          color: #4CAF50;
        }
        
        .preview-icon {
          font-size: 14px;
        }
        
        .preview-arrow {
          color: #999;
          font-size: 16px;
        }
        
        .trigger-footer {
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
          background: #E91E63;
          color: #fff;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}

export default memo(PipelineTriggerNode);
