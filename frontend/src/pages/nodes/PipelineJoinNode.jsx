/** Pipeline Join Node
 * 
 * SQL-style join for combining multiple datasets.
 * Supports INNER, LEFT, RIGHT, FULL, and CROSS joins.
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const joinTypes = [
  { value: 'inner', label: 'INNER JOIN', icon: '∩', color: '#4CAF50', desc: 'Only matching rows' },
  { value: 'left', label: 'LEFT JOIN', icon: 'A', color: '#2196F3', desc: 'All from A, matching from B' },
  { value: 'right', label: 'RIGHT JOIN', icon: 'B', color: '#FF9800', desc: 'Matching from A, all from B' },
  { value: 'full', label: 'FULL JOIN', icon: '∪', color: '#9C27B0', desc: 'All rows from both' },
  { value: 'cross', label: 'CROSS JOIN', icon: '×', color: '#E91E63', desc: 'Cartesian product' },
];

function PipelineJoinNode({ data, selected, onUpdate }) {
  const [showEditor, setShowEditor] = useState(false);
  
  const joinType = data.joinType || 'left';
  const joinKeys = JSON.parse(data.joinKeys || '[]');
  const outputFields = JSON.parse(data.outputFields || '[]');
  const prefixTables = data.prefixTables !== false;
  
  const typeInfo = joinTypes.find(t => t.value === joinType) || joinTypes[0];
  
  const displaySummary = () => {
    if (joinType === 'cross') return 'Cross join - all combinations';
    if (joinKeys.length === 0) return 'No join keys set';
    if (joinKeys.length === 1) return `Join on: ${joinKeys[0].left} = ${joinKeys[0].right}`;
    return `Join on: ${joinKeys.length} keys`;
  };
  
  return (
    <div 
      className={`pipeline-node join ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : typeInfo.color,
        backgroundColor: selected ? '#E3F2FD' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setShowEditor(true)}
      title="Double-click to edit join configuration"
    >
      {/* Left input handle (Primary) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        id="left"
        style={{ backgroundColor: '#2196F3', top: '35%' }}
      />
      
      {/* Right input handle (Secondary) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        id="right"
        style={{ backgroundColor: '#FF9800', top: '65%' }}
      />
      
      <div className="node-content">
        <div className="node-icon" style={{ color: typeInfo.color }}>{typeInfo.icon}</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Join'}</div>
          <div className="node-type" style={{ color: typeInfo.color }}>
            {typeInfo.label}
          </div>
          <div className="node-summary">
            {displaySummary()}
          </div>
          {outputFields.length > 0 && (
            <div className="node-fields">
              {outputFields.slice(0, 3).map((f, i) => (
                <span key={i} className="field-tag">{f.name}</span>
              ))}
              {outputFields.length > 3 && <span className="more">+{outputFields.length - 3}</span>}
            </div>
          )}
        </div>
      </div>
      
      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: typeInfo.color }}
      />
      
      {showEditor && (
        <JoinEditor
          joinType={joinType}
          joinKeys={joinKeys}
          outputFields={outputFields}
          prefixTables={prefixTables}
          onUpdate={(jt, jk, of, pt) => {
            onUpdate?.(data.id, { 
              joinType: jt,
              joinKeys: JSON.stringify(jk, null, 2),
              outputFields: JSON.stringify(of, null, 2),
              prefixTables: pt
            });
          }}
          onClose={() => setShowEditor(false)}
        />
      )}
      
      <style>{`
        .pipeline-node.join {
          min-width: 180px;
          border: 2px solid #4CAF50;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.join:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.join.selected {
          border-color: #1976D2;
          background-color: #E3F2FD;
        }
        
        .node-content {
          padding: 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .node-icon {
          font-size: 28px;
          font-weight: bold;
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
          font-size: 11px;
          font-weight: 600;
          margin-top: 2px;
        }
        
        .node-summary {
          font-size: 10px;
          color: #666;
          margin-top: 2px;
          font-family: monospace;
        }
        
        .node-fields {
          display: flex;
          gap: 4px;
          margin-top: 4px;
          flex-wrap: wrap;
        }
        
        .field-tag {
          padding: 2px 6px;
          background: #f5f5f5;
          border-radius: 4px;
          font-size: 9px;
          color: #666;
        }
        
        .more {
          padding: 2px 6px;
          background: #e3f2fd;
          border-radius: 4px;
          font-size: 9px;
          color: #1976D2;
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

// Join editor component
function JoinEditor({ joinType, joinKeys, outputFields, prefixTables, onUpdate, onClose }) {
  const [localJoinType, setLocalJoinType] = useState(joinType);
  const [localJoinKeys, setLocalJoinKeys] = useState(joinKeys);
  const [localOutputFields, setLocalOutputFields] = useState(outputFields);
  const [localPrefixTables, setLocalPrefixTables] = useState(prefixTables);
  
  const [newLeftKey, setNewLeftKey] = useState('');
  const [newRightKey, setNewRightKey] = useState('');
  
  const addJoinKey = () => {
    if (!newLeftKey.trim() || !newRightKey.trim()) return;
    setLocalJoinKeys([...localJoinKeys, { left: newLeftKey, right: newRightKey }]);
    setNewLeftKey('');
    setNewRightKey('');
  };
  
  const removeJoinKey = (index) => {
    setLocalJoinKeys(localJoinKeys.filter((_, i) => i !== index));
  };
  
  const addOutputField = (table, field) => {
    setLocalOutputFields([...localOutputFields, { 
      name: field, 
      source: table,
      alias: '' 
    }]);
  };
  
  const removeOutputField = (index) => {
    setLocalOutputFields(localOutputFields.filter((_, i) => i !== index));
  };
  
  const updateOutputField = (index, field, value) => {
    const newFields = [...localOutputFields];
    newFields[index] = { ...newFields[index], [field]: value };
    setLocalOutputFields(newFields);
  };
  
  const saveAndClose = () => {
    onUpdate(localJoinType, localJoinKeys, localOutputFields, localPrefixTables);
    onClose();
  };
  
  return (
    <div className="join-overlay">
      <div className="join-editor">
        <div className="join-header">
          <h3>🔗 SQL Join</h3>
          <button className="join-close" onClick={onClose}>×</button>
        </div>
        
        <div className="join-content">
          {/* Join type selector */}
          <div className="join-types">
            <label>Join Type</label>
            <div className="type-grid">
              {joinTypes.map((type) => (
                <button
                  key={type.value}
                  className={`type-btn ${localJoinType === type.value ? 'active' : ''}`}
                  style={{ borderColor: type.color }}
                  onClick={() => setLocalJoinType(type.value)}
                >
                  <span className="type-icon" style={{ backgroundColor: type.color }}>{type.icon}</span>
                  <span className="type-label">{type.label}</span>
                  <span className="type-desc">{type.desc}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Join keys */}
          {localJoinType !== 'cross' && (
            <div className="join-keys-section">
              <label>Join Keys</label>
              <div className="keys-list">
                {localJoinKeys.map((k, i) => (
                  <div key={i} className="key-row">
                    <span className="left-table">LEFT</span>
                    <span className="key-field">{k.left}</span>
                    <span className="equals">=</span>
                    <span className="right-table">RIGHT</span>
                    <span className="key-field">{k.right}</span>
                    <button className="remove-key" onClick={() => removeJoinKey(i)}>×</button>
                  </div>
                ))}
              </div>
              <div className="add-key">
                <span className="add-label">LEFT.</span>
                <input
                  type="text"
                  placeholder="field"
                  value={newLeftKey}
                  onChange={(e) => setNewLeftKey(e.target.value)}
                  className="key-input"
                />
                <span className="add-label">=</span>
                <span className="add-label">RIGHT.</span>
                <input
                  type="text"
                  placeholder="field"
                  value={newRightKey}
                  onChange={(e) => setNewRightKey(e.target.value)}
                  className="key-input"
                />
                <button className="add-btn" onClick={addJoinKey}>+</button>
              </div>
            </div>
          )}
          
          {/* Output fields */}
          <div className="output-section">
            <label>Output Fields</label>
            <div className="output-options">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={localPrefixTables}
                  onChange={(e) => setLocalPrefixTables(e.target.checked)}
                />
                <span>Prefix field names with table (LEFT_/RIGHT_)</span>
              </label>
            </div>
            
            {localOutputFields.length === 0 ? (
              <div className="no-fields">No fields selected</div>
            ) : (
              <div className="fields-list">
                {localOutputFields.map((f, i) => (
                  <div key={i} className="field-row">
                    <select
                      value={f.source}
                      onChange={(e) => updateOutputField(i, 'source', e.target.value)}
                      className="source-select"
                    >
                      <option value="LEFT">LEFT</option>
                      <option value="RIGHT">RIGHT</option>
                    </select>
                    <input
                      type="text"
                      placeholder="field"
                      value={f.name}
                      onChange={(e) => updateOutputField(i, 'name', e.target.value)}
                      className="field-name-input"
                    />
                    <input
                      type="text"
                      placeholder="alias"
                      value={f.alias || ''}
                      onChange={(e) => updateOutputField(i, 'alias', e.target.value)}
                      className="alias-input"
                    />
                    <button className="remove-field" onClick={() => removeOutputField(i)}>×</button>
                  </div>
                ))}
              </div>
            )}
            
            <div className="quick-add">
              <span>Quick add:</span>
              <button onClick={() => addOutputField('LEFT', '*')}>LEFT.*</button>
              <button onClick={() => addOutputField('RIGHT', '*')}>RIGHT.*</button>
              <button onClick={() => addOutputField('LEFT', 'id')}>LEFT.id</button>
              <button onClick={() => addOutputField('RIGHT', 'id')}>RIGHT.id</button>
            </div>
          </div>
          
          {/* Preview */}
          <div className="join-preview">
            <div className="preview-title">Join Preview</div>
            <div className="preview-diagram">
              <div className="preview-table left">
                <div className="table-name">LEFT</div>
                <div className="table-rows">
                  <div className="table-row">row1</div>
                  <div className="table-row">row2</div>
                  <div className="table-row">row3</div>
                </div>
              </div>
              <div className="preview-join">
                <span className="join-symbol" style={{ color: joinTypes.find(t => t.value === localJoinType)?.color }}>
                  {joinTypes.find(t => t.value === localJoinType)?.icon}
                </span>
                <span className="join-type">{localJoinType.toUpperCase()}</span>
              </div>
              <div className="preview-table right">
                <div className="table-name">RIGHT</div>
                <div className="table-rows">
                  <div className="table-row">match1</div>
                  <div className="table-row">match2</div>
                </div>
              </div>
            </div>
            <div className="preview-result">
              → {localJoinType === 'inner' ? 'Matching rows only' :
                 localJoinType === 'left' ? 'All LEFT + matching RIGHT' :
                 localJoinType === 'right' ? 'Matching LEFT + all RIGHT' :
                 localJoinType === 'full' ? 'All rows from both' :
                 'All combinations (LEFT × RIGHT)'}
            </div>
          </div>
        </div>
        
        <div className="join-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn" onClick={saveAndClose}>✓ Apply Join</button>
        </div>
      </div>
      
      <style>{`
        .join-overlay {
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
        
        .join-editor {
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          width: 520px;
          max-height: 550px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .join-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, #4CAF50 0%, #388E3C 100%);
          color: #fff;
        }
        
        .join-header h3 {
          margin: 0;
          font-size: 16px;
        }
        
        .join-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .join-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        
        .join-types {
          margin-bottom: 16px;
        }
        
        .join-types label {
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
        
        .type-btn:hover {
          border-color: #bbb;
        }
        
        .type-btn.active {
          background: #E8F5E9;
          border-width: 2px;
        }
        
        .type-icon {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: #fff;
          font-size: 14px;
          font-weight: bold;
          margin-bottom: 6px;
        }
        
        .type-label {
          font-size: 11px;
          font-weight: 600;
          color: #333;
        }
        
        .type-desc {
          font-size: 9px;
          color: #999;
          margin-top: 2px;
          text-align: center;
        }
        
        .join-keys-section {
          margin-bottom: 16px;
        }
        
        .join-keys-section label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .keys-list {
          margin-bottom: 8px;
        }
        
        .key-row {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 10px;
          background: #E8F5E9;
          border-radius: 6px;
          margin-bottom: 4px;
        }
        
        .left-table, .right-table {
          font-size: 10px;
          font-weight: 600;
          padding: 2px 6px;
          border-radius: 4px;
        }
        
        .left-table {
          background: #2196F3;
          color: #fff;
        }
        
        .right-table {
          background: #FF9800;
          color: #fff;
        }
        
        .key-field {
          flex: 1;
          font-family: monospace;
          font-size: 12px;
          color: #333;
        }
        
        .equals {
          color: #4CAF50;
          font-weight: bold;
        }
        
        .remove-key {
          width: 20px;
          height: 20px;
          border: none;
          border-radius: 4px;
          background: #ffebee;
          color: #f44336;
          cursor: pointer;
          font-size: 12px;
        }
        
        .add-key {
          display: flex;
          align-items: center;
          gap: 4px;
        }
        
        .add-label {
          font-size: 10px;
          font-weight: 600;
          color: #666;
        }
        
        .key-input {
          width: 80px;
          padding: 6px 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 11px;
          font-family: monospace;
        }
        
        .add-btn {
          width: 24px;
          height: 24px;
          border: none;
          border-radius: 4px;
          background: #4CAF50;
          color: #fff;
          cursor: pointer;
          font-size: 14px;
        }
        
        .output-section label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .output-options {
          margin-bottom: 10px;
        }
        
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          cursor: pointer;
        }
        
        .no-fields {
          padding: 16px;
          text-align: center;
          color: #999;
          background: #f5f5f5;
          border-radius: 6px;
          font-size: 12px;
        }
        
        .fields-list {
          margin-bottom: 10px;
        }
        
        .field-row {
          display: flex;
          gap: 6px;
          margin-bottom: 6px;
        }
        
        .source-select {
          width: 70px;
          padding: 6px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 600;
        }
        
        .field-name-input {
          flex: 1;
          padding: 6px 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 11px;
          font-family: monospace;
        }
        
        .alias-input {
          width: 80px;
          padding: 6px 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 11px;
        }
        
        .remove-field {
          width: 22px;
          height: 22px;
          border: none;
          border-radius: 4px;
          background: #ffebee;
          color: #f44336;
          cursor: pointer;
          font-size: 12px;
        }
        
        .quick-add {
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
        }
        
        .quick-add span {
          font-size: 11px;
          color: #666;
        }
        
        .quick-add button {
          padding: 4px 10px;
          border: 1px solid #ddd;
          border-radius: 12px;
          background: #fff;
          cursor: pointer;
          font-size: 10px;
          font-family: monospace;
        }
        
        .quick-add button:hover {
          border-color: #4CAF50;
          background: #E8F5E9;
        }
        
        .join-preview {
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
          gap: 16px;
        }
        
        .preview-table {
          background: #fff;
          border-radius: 8px;
          overflow: hidden;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .table-name {
          padding: 6px 12px;
          font-size: 11px;
          font-weight: 600;
          color: #fff;
        }
        
        .preview-table.left .table-name {
          background: #2196F3;
        }
        
        .preview-table.right .table-name {
          background: #FF9800;
        }
        
        .table-rows {
          padding: 8px;
        }
        
        .table-row {
          font-size: 10px;
          color: #666;
          padding: 2px 8px;
          font-family: monospace;
        }
        
        .preview-join {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
        }
        
        .join-symbol {
          font-size: 24px;
          font-weight: bold;
        }
        
        .join-type {
          font-size: 10px;
          color: #666;
          font-weight: 600;
        }
        
        .preview-result {
          margin-top: 12px;
          text-align: center;
          font-size: 12px;
          color: #666;
          padding-top: 10px;
          border-top: 1px solid #e0e0e0;
        }
        
        .join-footer {
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

export default memo(PipelineJoinNode);
