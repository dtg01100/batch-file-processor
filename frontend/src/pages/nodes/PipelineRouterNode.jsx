/** Pipeline Router Node
 * 
 * Routes rows to different outputs based on conditions.
 * Splits data into TRUE and FALSE branches.
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const operators = [
  { value: 'equals', label: 'equals', symbol: '=', color: '#4CAF50' },
  { value: 'not_equals', label: 'not equals', symbol: '≠', color: '#f44336' },
  { value: 'greater', label: 'greater than', symbol: '>', color: '#2196F3' },
  { value: 'greater_equal', label: 'greater or equal', symbol: '≥', color: '#2196F3' },
  { value: 'less', label: 'less than', symbol: '<', color: '#FF9800' },
  { value: 'less_equal', label: 'less or equal', symbol: '≤', color: '#FF9800' },
  { value: 'contains', label: 'contains', symbol: '~', color: '#9C27B0' },
  { value: 'starts_with', label: 'starts with', symbol: '↗', color: '#E91E63' },
  { value: 'ends_with', label: 'ends with', symbol: '↘', color: '#E91E63' },
  { value: 'in', label: 'in list', symbol: '∈', color: '#00BCD4' },
  { value: 'not_in', label: 'not in list', symbol: '∉', color: '#f44336' },
  { value: 'is_null', label: 'is null', symbol: '∅', color: '#607D8B' },
  { value: 'is_not_null', label: 'is not null', symbol: '!∅', color: '#607D8B' },
  { value: 'regex', label: 'matches regex', symbol: '.*', color: '#795548' },
];

function PipelineRouterNode({ data, selected, onUpdate }) {
  const [showEditor, setShowEditor] = useState(false);
  
  const conditions = JSON.parse(data.conditions || '[]');
  const logic = data.logic || 'AND';
  
  // Parse conditions for display
  const displayCondition = () => {
    if (conditions.length === 0) return 'No condition set';
    if (conditions.length === 1) {
      const c = conditions[0];
      const op = operators.find(o => o.value === c.operator);
      const symbol = op?.symbol || '=';
      const value = c.value || '';
      return `${c.field} ${symbol} ${value}`;
    }
    return `${logic}: ${conditions.length} conditions`;
  };
  
  return (
    <div 
      className={`pipeline-node router ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#FF5722',
        backgroundColor: selected ? '#FFF3E0' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setShowEditor(true)}
      title="Double-click to edit routing conditions"
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#FF5722' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🔀</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Router'}</div>
          <div className="node-condition">
            {displayCondition()}
          </div>
          <div className="node-branches">
            <span className="branch-tag true">✓ TRUE</span>
            <span className="branch-tag false">✗ FALSE</span>
          </div>
        </div>
      </div>
      
      {/* TRUE output handle (right side, top) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        id="true"
        style={{ 
          backgroundColor: '#4CAF50',
          top: '30%',
        }}
      />
      
      {/* FALSE output handle (right side, bottom) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        id="false"
        style={{ 
          backgroundColor: '#f44336',
          top: '70%',
        }}
      />
      
      {/* Inline condition editor */}
      {showEditor && (
        <RouterConditionEditor
          conditions={conditions}
          logic={logic}
          onUpdate={(conds, lg) => {
            onUpdate?.(data.id, { 
              conditions: JSON.stringify(conds, null, 2),
              logic: lg 
            });
          }}
          onClose={() => setShowEditor(false)}
        />
      )}
      
      <style>{`
        .pipeline-node.router {
          min-width: 180px;
          border: 2px solid #FF5722;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.router:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.router.selected {
          border-color: #2196F3;
          background-color: #FFF3E0;
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
        
        .node-condition {
          font-size: 11px;
          color: #666;
          margin-top: 4px;
          font-family: monospace;
          background: #f5f5f5;
          padding: 4px 8px;
          border-radius: 4px;
        }
        
        .node-branches {
          display: flex;
          gap: 8px;
          margin-top: 6px;
        }
        
        .branch-tag {
          font-size: 10px;
          padding: 2px 8px;
          border-radius: 10px;
          font-weight: 600;
        }
        
        .branch-tag.true {
          background: #E8F5E9;
          color: #4CAF50;
        }
        
        .branch-tag.false {
          background: #FFEBEE;
          color: #f44336;
        }
        
        .node-handle {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          border: 2px solid #fff;
        }
        
        .node-handle#true {
          background: #4CAF50;
        }
        
        .node-handle#false {
          background: #f44336;
        }
      `}</style>
    </div>
  );
}

// Condition editor component
function RouterConditionEditor({ conditions, logic, onUpdate, onClose }) {
  const [localConditions, setLocalConditions] = useState(conditions);
  const [localLogic, setLocalLogic] = useState(logic);
  const [newField, setNewField] = useState('');
  const [newOperator, setNewOperator] = useState('equals');
  const [newValue, setNewValue] = useState('');
  
  const addCondition = () => {
    if (!newField.trim()) return;
    setLocalConditions([
      ...localConditions,
      { field: newField, operator: newOperator, value: newValue }
    ]);
    setNewField('');
    setNewValue('');
  };
  
  const removeCondition = (index) => {
    setLocalConditions(localConditions.filter((_, i) => i !== index));
  };
  
  const saveAndClose = () => {
    onUpdate(localConditions, localLogic);
    onClose();
  };
  
  return (
    <div className="router-editor-overlay">
      <div className="router-editor">
        <div className="router-editor-header">
          <h3>🔀 Route Conditions</h3>
          <button className="router-close" onClick={onClose}>×</button>
        </div>
        
        <div className="router-editor-content">
          {/* Logic selector */}
          <div className="router-logic">
            <label>Match conditions using:</label>
            <div className="logic-buttons">
              <button 
                className={localLogic === 'AND' ? 'active' : ''}
                onClick={() => setLocalLogic('AND')}
              >
                AND - All conditions must match
              </button>
              <button 
                className={localLogic === 'OR' ? 'active' : ''}
                onClick={() => setLocalLogic('OR')}
              >
                OR - Any condition can match
              </button>
            </div>
          </div>
          
          {/* Existing conditions */}
          <div className="router-conditions">
            <label>Conditions:</label>
            {localConditions.length === 0 ? (
              <div className="no-conditions">No conditions added yet</div>
            ) : (
              localConditions.map((c, i) => {
                const op = operators.find(o => o.value === c.operator);
                return (
                  <div key={i} className="condition-row">
                    <span className="condition-field">{c.field}</span>
                    <span className="condition-op" style={{ color: op?.color }}>{op?.symbol || '='}</span>
                    <span className="condition-value">{c.value}</span>
                    <button className="condition-remove" onClick={() => removeCondition(i)}>×</button>
                  </div>
                );
              })
            )}
          </div>
          
          {/* Add new condition */}
          <div className="router-add">
            <label>Add Condition:</label>
            <div className="condition-form">
              <input
                type="text"
                placeholder="Field name"
                value={newField}
                onChange={(e) => setNewField(e.target.value)}
                className="field-input"
              />
              <select
                value={newOperator}
                onChange={(e) => setNewOperator(e.target.value)}
                className="operator-select"
              >
                {operators.map((op) => (
                  <option key={op.value} value={op.value}>
                    {op.symbol} {op.label}
                  </option>
                ))}
              </select>
              <input
                type="text"
                placeholder="Value"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                className="value-input"
              />
              <button className="add-btn" onClick={addCondition}>+</button>
            </div>
            <p className="help-text">Tip: For null checks, leave value empty</p>
          </div>
          
          {/* Preview */}
          <div className="router-preview">
            <div className="preview-true">
              <span className="preview-icon">✓</span>
              <span>TRUE → Active records</span>
            </div>
            <div className="preview-false">
              <span className="preview-icon">✗</span>
              <span>FALSE → Inactive records</span>
            </div>
          </div>
        </div>
        
        <div className="router-editor-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn" onClick={saveAndClose}>✓ Apply Conditions</button>
        </div>
      </div>
      
      <style>{`
        .router-editor-overlay {
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
        
        .router-editor {
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          width: 450px;
          max-height: 500px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .router-editor-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, #FF5722 0%, #E64A19 100%);
          color: #fff;
        }
        
        .router-editor-header h3 {
          margin: 0;
          font-size: 16px;
        }
        
        .router-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .router-editor-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        
        .router-logic {
          margin-bottom: 16px;
        }
        
        .router-logic label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .logic-buttons {
          display: flex;
          gap: 8px;
        }
        
        .logic-buttons button {
          flex: 1;
          padding: 10px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          font-size: 12px;
          transition: all 0.2s;
        }
        
        .logic-buttons button.active {
          border-color: #FF5722;
          background: #FFF3E0;
          color: #E64A19;
        }
        
        .router-conditions {
          margin-bottom: 16px;
        }
        
        .router-conditions label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .no-conditions {
          padding: 20px;
          text-align: center;
          color: #999;
          background: #f5f5f5;
          border-radius: 8px;
          font-size: 13px;
        }
        
        .condition-row {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 12px;
          background: #f5f5f5;
          border-radius: 6px;
          margin-bottom: 6px;
        }
        
        .condition-field {
          font-weight: 600;
          font-size: 13px;
          color: #333;
        }
        
        .condition-op {
          font-weight: bold;
          font-size: 14px;
        }
        
        .condition-value {
          flex: 1;
          font-size: 13px;
          color: #666;
          font-family: monospace;
        }
        
        .condition-remove {
          width: 22px;
          height: 22px;
          border: none;
          border-radius: 4px;
          background: #ffebee;
          color: #f44336;
          cursor: pointer;
          font-size: 14px;
        }
        
        .router-add {
          margin-bottom: 16px;
        }
        
        .router-add label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .condition-form {
          display: flex;
          gap: 6px;
        }
        
        .field-input {
          flex: 1;
          padding: 8px 10px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 12px;
        }
        
        .operator-select {
          width: 140px;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 12px;
          background: #fff;
        }
        
        .value-input {
          flex: 1;
          padding: 8px 10px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 12px;
        }
        
        .add-btn {
          width: 32px;
          border: none;
          border-radius: 6px;
          background: #4CAF50;
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .help-text {
          font-size: 11px;
          color: #999;
          margin-top: 6px;
          font-style: italic;
        }
        
        .router-preview {
          display: flex;
          gap: 12px;
          padding: 12px;
          background: #f5f5f5;
          border-radius: 8px;
        }
        
        .preview-true,
        .preview-false {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px;
          border-radius: 6px;
          font-size: 12px;
        }
        
        .preview-true {
          background: #E8F5E9;
          color: #4CAF50;
        }
        
        .preview-false {
          background: #FFEBEE;
          color: #f44336;
        }
        
        .preview-icon {
          width: 20px;
          height: 20px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 12px;
          font-weight: bold;
        }
        
        .preview-true .preview-icon {
          background: #4CAF50;
          color: #fff;
        }
        
        .preview-false .preview-icon {
          background: #f44336;
          color: #fff;
        }
        
        .router-editor-footer {
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

export default memo(PipelineRouterNode);
