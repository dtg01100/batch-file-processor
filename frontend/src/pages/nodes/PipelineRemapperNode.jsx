/** Pipeline Remapper Node
 * 
 * Renames, reorders, and drops fields.
 * Maps input fields to output fields with optional transforms.
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const transforms = [
  { value: 'none', label: 'None (keep as-is)', icon: '•' },
  { value: 'upper', label: 'UPPERCASE', icon: '⬆' },
  { value: 'lower', label: 'lowercase', icon: '⬇' },
  { value: 'title', label: 'Title Case', icon: 'Tt' },
  { value: 'trim', label: 'Trim whitespace', icon: '↔' },
  { value: 'number', label: 'Parse as number', icon: '#' },
  { value: 'date', label: 'Format date', icon: '📅' },
  { value: 'boolean', label: 'Parse as boolean', icon: '☑' },
];

function PipelineRemapperNode({ data, selected, onUpdate }) {
  const [showEditor, setShowEditor] = useState(false);
  
  const mappings = JSON.parse(data.mappings || '[]');
  const dropOthers = data.dropOthers !== false; // Default true
  
  const displayMappings = () => {
    if (mappings.length === 0) return 'No field mappings';
    return `${mappings.length} field${mappings.length > 1 ? 's' : ''} mapped`;
  };
  
  return (
    <div 
      className={`pipeline-node remapper ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#00BCD4',
        backgroundColor: selected ? '#E0F7FA' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setShowEditor(true)}
      title="Double-click to edit field mappings"
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#00BCD4' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🔄</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Remapper'}</div>
          <div className="node-summary">
            {displayMappings()}
          </div>
          {mappings.length > 0 && (
            <div className="node-preview">
              {mappings.slice(0, 4).map((m, i) => (
                <span key={i} className="mapping-tag">
                  {m.source} → {m.target}
                </span>
              ))}
              {mappings.length > 4 && <span className="more">+{mappings.length - 4}</span>}
            </div>
          )}
          <div className="node-options">
            {dropOthers && (
              <span className="option-badge">Drop unmapped</span>
            )}
          </div>
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#00BCD4' }}
      />
      
      {/* Inline editor */}
      {showEditor && (
        <RemapperEditor
          mappings={mappings}
          dropOthers={dropOthers}
          onUpdate={(maps, drop) => {
            onUpdate?.(data.id, { 
              mappings: JSON.stringify(maps, null, 2),
              dropOthers: drop 
            });
          }}
          onClose={() => setShowEditor(false)}
        />
      )}
      
      <style>{`
        .pipeline-node.remapper {
          min-width: 180px;
          border: 2px solid #00BCD4;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.remapper:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.remapper.selected {
          border-color: #0097A7;
          background-color: #E0F7FA;
        }
        
        .node-content {
          padding: 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .node-icon {
          font-size: 24px;
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
        
        .node-summary {
          font-size: 11px;
          color: #666;
          margin-top: 2px;
        }
        
        .node-preview {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 6px;
        }
        
        .mapping-tag {
          padding: 2px 6px;
          background: #E0F7FA;
          border-radius: 4px;
          font-size: 9px;
          color: #0097A7;
        }
        
        .more {
          padding: 2px 6px;
          background: #f5f5f5;
          border-radius: 4px;
          font-size: 9px;
          color: #666;
        }
        
        .node-options {
          margin-top: 4px;
        }
        
        .option-badge {
          padding: 2px 6px;
          background: #FFF3E0;
          border-radius: 10px;
          font-size: 9px;
          color: #FF9800;
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

// Remapper editor component
function RemapperEditor({ mappings, dropOthers, onUpdate, onClose }) {
  const [localMappings, setLocalMappings] = useState(mappings);
  const [localDropOthers, setLocalDropOthers] = useState(dropOthers);
  
  const [newSource, setNewSource] = useState('');
  const [newTarget, setNewTarget] = useState('');
  const [newTransform, setNewTransform] = useState('none');
  
  const addMapping = () => {
    if (!newSource.trim() || !newTarget.trim()) return;
    setLocalMappings([
      ...localMappings,
      { source: newSource, target: newTarget, transform: newTransform }
    ]);
    setNewSource('');
    setNewTarget('');
    setNewTransform('none');
  };
  
  const removeMapping = (index) => {
    setLocalMappings(localMappings.filter((_, i) => i !== index));
  };
  
  const updateMapping = (index, field, value) => {
    const newMappings = [...localMappings];
    newMappings[index] = { ...newMappings[index], [field]: value };
    setLocalMappings(newMappings);
  };
  
  const saveAndClose = () => {
    onUpdate(localMappings, localDropOthers);
    onClose();
  };
  
  const moveUp = (index) => {
    if (index === 0) return;
    const newMappings = [...localMappings];
    [newMappings[index - 1], newMappings[index]] = [newMappings[index], newMappings[index - 1]];
    setLocalMappings(newMappings);
  };
  
  const moveDown = (index) => {
    if (index === localMappings.length - 1) return;
    const newMappings = [...localMappings];
    [newMappings[index], newMappings[index + 1]] = [newMappings[index + 1], newMappings[index]];
    setLocalMappings(newMappings);
  };
  
  return (
    <div className="remapper-overlay">
      <div className="remapper-editor">
        <div className="remapper-header">
          <h3>🔄 Field Remapper</h3>
          <button className="remapper-close" onClick={onClose}>×</button>
        </div>
        
        <div className="remapper-content">
          {/* Options */}
          <div className="remapper-options">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={localDropOthers}
                onChange={(e) => setLocalDropOthers(e.target.checked)}
              />
              <span>Drop unmapped fields</span>
            </label>
            <p className="help-text">
              {localDropOthers 
                ? 'Only the mapped fields will be in output' 
                : 'All fields will be in output (mapped + unmapped)'}
            </p>
          </div>
          
          {/* Current mappings */}
          <div className="remapper-mappings">
            <label>Field Mappings ({localMappings.length})</label>
            {localMappings.length === 0 ? (
              <div className="no-mappings">No mappings added yet</div>
            ) : (
              <div className="mapping-list">
                {localMappings.map((m, i) => (
                  <div key={i} className="mapping-row">
                    <div className="move-buttons">
                      <button onClick={() => moveUp(i)} disabled={i === 0}>↑</button>
                      <button onClick={() => moveDown(i)} disabled={i === localMappings.length - 1}>↓</button>
                    </div>
                    <input
                      type="text"
                      placeholder="Source field"
                      value={m.source}
                      onChange={(e) => updateMapping(i, 'source', e.target.value)}
                      className="field-input"
                    />
                    <span className="arrow">→</span>
                    <input
                      type="text"
                      placeholder="Target field"
                      value={m.target}
                      onChange={(e) => updateMapping(i, 'target', e.target.value)}
                      className="field-input"
                    />
                    <select
                      value={m.transform}
                      onChange={(e) => updateMapping(i, 'transform', e.target.value)}
                      className="transform-select"
                    >
                      {transforms.map((t) => (
                        <option key={t.value} value={t.value}>{t.icon} {t.label}</option>
                      ))}
                    </select>
                    <button className="remove-btn" onClick={() => removeMapping(i)}>×</button>
                  </div>
                ))}
              </div>
            )}
          </div>
          
          {/* Add new mapping */}
          <div className="remapper-add">
            <label>Add Mapping:</label>
            <div className="add-form">
              <input
                type="text"
                placeholder="Source field"
                value={newSource}
                onChange={(e) => setNewSource(e.target.value)}
                className="field-input"
              />
              <span className="arrow">→</span>
              <input
                type="text"
                placeholder="Target field"
                value={newTarget}
                onChange={(e) => setNewTarget(e.target.value)}
                className="field-input"
              />
              <select
                value={newTransform}
                onChange={(e) => setNewTransform(e.target.value)}
                className="transform-select"
              >
                {transforms.map((t) => (
                  <option key={t.value} value={t.value}>{t.icon} {t.label}</option>
                ))}
              </select>
              <button className="add-btn" onClick={addMapping}>+</button>
            </div>
          </div>
          
          {/* Templates */}
          <div className="remapper-templates">
            <span className="templates-label">Quick templates:</span>
            <button onClick={() => {
              setLocalMappings([
                { source: 'CUST_NAME', target: 'customer_name', transform: 'title' },
                { source: 'CUST_EMAIL', target: 'email', transform: 'lower' },
                { source: 'PHONE_NUM', target: 'phone', transform: 'none' },
              ]);
            }}>Customer Data</button>
            <button onClick={() => {
              setLocalMappings([
                { source: 'order_id', target: 'id', transform: 'none' },
                { source: 'order_total', target: 'amount', transform: 'number' },
                { source: 'order_date', target: 'date', transform: 'date' },
              ]);
            }}>Orders</button>
            <button onClick={() => {
              setLocalMappings([
                { source: 'SKU', target: 'code', transform: 'upper' },
                { source: 'DESC', target: 'description', transform: 'trim' },
                { source: 'QTY', target: 'quantity', transform: 'number' },
              ]);
            }}>Products</button>
          </div>
        </div>
        
        <div className="remapper-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn" onClick={saveAndClose}>✓ Apply Mappings</button>
        </div>
      </div>
      
      <style>{`
        .remapper-overlay {
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
        
        .remapper-editor {
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          width: 550px;
          max-height: 500px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .remapper-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, #00BCD4 0%, #0097A7 100%);
          color: #fff;
        }
        
        .remapper-header h3 {
          margin: 0;
          font-size: 16px;
        }
        
        .remapper-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .remapper-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        
        .remapper-options {
          margin-bottom: 16px;
          padding: 12px;
          background: #f5f5f5;
          border-radius: 8px;
        }
        
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          font-size: 13px;
        }
        
        .checkbox-label input {
          width: 16px;
          height: 16px;
        }
        
        .help-text {
          font-size: 11px;
          color: #666;
          margin: 8px 0 0 24px;
          font-style: italic;
        }
        
        .remapper-mappings {
          margin-bottom: 16px;
        }
        
        .remapper-mappings label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .no-mappings {
          padding: 20px;
          text-align: center;
          color: #999;
          background: #f5f5f5;
          border-radius: 8px;
          font-size: 13px;
        }
        
        .mapping-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        
        .mapping-row {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 10px;
          background: #E0F7FA;
          border-radius: 6px;
        }
        
        .move-buttons {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        
        .move-buttons button {
          width: 20px;
          height: 18px;
          border: none;
          border-radius: 3px;
          background: #fff;
          cursor: pointer;
          font-size: 10px;
          color: #666;
        }
        
        .move-buttons button:disabled {
          opacity: 0.3;
          cursor: not-allowed;
        }
        
        .field-input {
          flex: 1;
          padding: 6px 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 12px;
        }
        
        .arrow {
          color: #00BCD4;
          font-weight: bold;
          font-size: 14px;
        }
        
        .transform-select {
          width: 140px;
          padding: 6px 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 11px;
          background: #fff;
        }
        
        .remove-btn {
          width: 22px;
          height: 22px;
          border: none;
          border-radius: 4px;
          background: #ffebee;
          color: #f44336;
          cursor: pointer;
          font-size: 14px;
        }
        
        .remapper-add {
          margin-bottom: 16px;
        }
        
        .remapper-add label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .add-form {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        
        .add-btn {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 6px;
          background: #00BCD4;
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .remapper-templates {
          display: flex;
          align-items: center;
          gap: 8px;
          padding-top: 12px;
          border-top: 1px solid #e0e0e0;
        }
        
        .templates-label {
          font-size: 11px;
          color: #666;
        }
        
        .remapper-templates button {
          padding: 4px 10px;
          border: 1px solid #ddd;
          border-radius: 12px;
          background: #fff;
          cursor: pointer;
          font-size: 11px;
        }
        
        .remapper-templates button:hover {
          border-color: #00BCD4;
          background: #E0F7FA;
        }
        
        .remapper-footer {
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
          background: #00BCD4;
          color: #fff;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}

export default memo(PipelineRemapperNode);
