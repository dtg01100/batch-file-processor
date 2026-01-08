/** Query Node
 *
 * Custom React Flow node for SQL/data queries with input/output mapping.
 * Can accept parameters from upstream nodes and output results to downstream nodes.
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const queryTypes = [
  { value: 'sql', label: 'SQL Query', icon: '🗃️', color: '#FF9800' },
  { value: 'python', label: 'Python Script', icon: '🐍', color: '#4CAF50' },
  { value: 'javascript', label: 'JavaScript', icon: '📜', color: '#FFC107' },
  { value: 'transform', label: 'Data Transform', icon: '🔄', color: '#2196F3' },
  { value: 'filter', label: 'Filter', icon: '🔍', color: '#9C27B0' },
  { value: 'aggregate', label: 'Aggregate', icon: '📊', color: '#E91E63' },
];

const inputOperators = [
  { value: 'equals', label: '=', icon: '=' },
  { value: 'not_equals', label: '!=', icon: '≠' },
  { value: 'greater', label: '>', icon: '>' },
  { value: 'less', label: '<', icon: '<' },
  { value: 'contains', label: 'contains', icon: '~' },
  { value: 'starts_with', label: 'starts with', icon: '↗' },
  { value: 'ends_with', label: 'ends with', icon: '↘' },
];

function QueryNode({ data, selected, onUpdate }) {
  const [editMode, setEditMode] = useState(false);
  const [activeTab, setActiveTab] = useState('query');

  const [editData, setEditData] = useState({
    label: data.label || 'Query',
    queryType: data.queryType || 'sql',
    query: data.query || 'SELECT * FROM {{table}} WHERE {{condition}}',
    inputs: data.inputs || '[]',
    outputs: data.outputs || '[]',
    conditions: data.conditions || '[]',
  });

  // Parse JSON safely
  const parseJson = (str, defaultVal) => {
    try {
      return JSON.parse(str);
    } catch {
      return defaultVal;
    }
  };

  // Handle data update
  const handleUpdate = (key, value) => {
    setEditData({ ...editData, [key]: value });
    onUpdate?.(data.id, { [key]: value });
  };

  const queryType = queryTypes.find(q => q.value === editData.queryType) || queryTypes[0];
  const inputs = parseJson(editData.inputs, []);
  const outputs = parseJson(editData.outputs, []);
  const conditions = parseJson(editData.conditions, []);

  // Add input parameter
  const addInput = () => {
    const newInputs = [...inputs, { name: '', sourceNode: '', sourceField: '' }];
    handleUpdate('inputs', JSON.stringify(newInputs, null, 2));
  };

  // Update input parameter
  const updateInput = (index, field, value) => {
    const newInputs = [...inputs];
    newInputs[index] = { ...newInputs[index], [field]: value };
    handleUpdate('inputs', JSON.stringify(newInputs, null, 2));
  };

  // Remove input parameter
  const removeInput = (index) => {
    const newInputs = inputs.filter((_, i) => i !== index);
    handleUpdate('inputs', JSON.stringify(newInputs, null, 2));
  };

  // Add output field
  const addOutput = () => {
    const newOutputs = [...outputs, { name: '', alias: '', type: 'string' }];
    handleUpdate('outputs', JSON.stringify(newOutputs, null, 2));
  };

  // Update output field
  const updateOutput = (index, field, value) => {
    const newOutputs = [...outputs];
    newOutputs[index] = { ...newOutputs[index], [field]: value };
    handleUpdate('outputs', JSON.stringify(newOutputs, null, 2));
  };

  // Remove output field
  const removeOutput = (index) => {
    const newOutputs = outputs.filter((_, i) => i !== index);
    handleUpdate('outputs', JSON.stringify(newOutputs, null, 2));
  };

  // Add condition
  const addCondition = () => {
    const newConditions = [...conditions, { field: '', operator: 'equals', value: '' }];
    handleUpdate('conditions', JSON.stringify(newConditions, null, 2));
  };

  // Update condition
  const updateCondition = (index, field, value) => {
    const newConditions = [...conditions];
    newConditions[index] = { ...newConditions[index], [field]: value };
    handleUpdate('conditions', JSON.stringify(newConditions, null, 2));
  };

  // Remove condition
  const removeCondition = (index) => {
    const newConditions = conditions.filter((_, i) => i !== index);
    handleUpdate('conditions', JSON.stringify(newConditions, null, 2));
  };

  // Edit mode - show full editor
  if (editMode) {
    return (
      <div 
        className="query-node query-node-editing"
        style={{ 
          borderColor: queryType.color,
          backgroundColor: '#FFF8E1',
          minWidth: '420px',
          maxWidth: '550px',
        }}
      >
        {/* Input handles (left side) - multiple for different inputs */}
        <Handle
          type="target"
          position={Position.Left}
          className="node-handle"
          style={{ backgroundColor: queryType.color, top: '30%' }}
        />
        <Handle
          type="target"
          position={Position.Left}
          className="node-handle"
          style={{ backgroundColor: queryType.color, top: '70%' }}
        />
        
        <div className="query-edit-content">
          {/* Header */}
          <div className="query-edit-header">
            <span className="query-edit-icon" style={{ color: queryType.color }}>
              {queryType.icon}
            </span>
            <span 
              className="query-edit-badge"
              style={{ backgroundColor: queryType.color }}
            >
              {queryType.label}
            </span>
            <input
              type="text"
              value={editData.label}
              onChange={(e) => handleUpdate('label', e.target.value)}
              className="query-edit-label-input"
              placeholder="Query name"
            />
            <button 
              className="query-edit-close"
              onClick={() => setEditMode(false)}
            >
              ✓
            </button>
          </div>

          {/* Tabs */}
          <div className="query-edit-tabs">
            {['query', 'inputs', 'outputs', 'filter'].map((tab) => (
              <button
                key={tab}
                className={`query-tab ${activeTab === tab ? 'active' : ''}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'query' && '📝 Query'}
                {tab === 'inputs' && `📥 Inputs (${inputs.length})`}
                {tab === 'outputs' && `📤 Outputs (${outputs.length})`}
                {tab === 'filter' && `🔍 Filter (${conditions.length})`}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="query-tab-content">
            {activeTab === 'query' && (
              <div className="query-section">
                <div className="query-type-selector">
                  {queryTypes.map((qt) => (
                    <button
                      key={qt.value}
                      className={`query-type-btn ${editData.queryType === qt.value ? 'active' : ''}`}
                      style={{ borderColor: qt.color }}
                      onClick={() => handleUpdate('queryType', qt.value)}
                    >
                      <span>{qt.icon}</span>
                      <span>{qt.label}</span>
                    </button>
                  ))}
                </div>

                <div className="query-editor">
                  <label>Query / Script</label>
                  {editData.queryType === 'sql' && (
                    <textarea
                      value={editData.query}
                      onChange={(e) => handleUpdate('query', e.target.value)}
                      className="query-textarea"
                      rows={6}
                      placeholder="SELECT * FROM {{table}} WHERE {{condition}}"
                    />
                  )}
                  {editData.queryType === 'python' && (
                    <textarea
                      value={editData.query}
                      onChange={(e) => handleUpdate('query', e.target.value)}
                      className="query-textarea"
                      rows={6}
                      placeholder="# Python script using input parameters"
                    />
                  )}
                  {editData.queryType === 'javascript' && (
                    <textarea
                      value={editData.query}
                      onChange={(e) => handleUpdate('query', e.target.value)}
                      className="query-textarea"
                      rows={6}
                      placeholder="// JavaScript transformation"
                    />
                  )}
                  {['transform', 'filter', 'aggregate'].includes(editData.queryType) && (
                    <textarea
                      value={editData.query}
                      onChange={(e) => handleUpdate('query', e.target.value)}
                      className="query-textarea"
                      rows={6}
                      placeholder="Enter transformation expression (e.g., field1 + field2)"
                    />
                  )}
                </div>

                {/* Quick snippets */}
                <div className="query-snippets">
                  <span>Snippets:</span>
                  <button onClick={() => handleUpdate('query', editData.query + ' SELECT * FROM {{input}}')}>SELECT *</button>
                  <button onClick={() => handleUpdate('query', editData.query + ' WHERE {{field}} = {{value}}')}>WHERE</button>
                  <button onClick={() => handleUpdate('query', editData.query + ' ORDER BY {{field}}')}>ORDER BY</button>
                  <button onClick={() => handleUpdate('query', editData.query + ' GROUP BY {{field}}')}>GROUP BY</button>
                </div>
              </div>
            )}

            {activeTab === 'inputs' && (
              <div className="query-section">
                <div className="query-section-header">
                  <label>Input Parameters</label>
                  <button className="query-add-btn" onClick={addInput}>+ Add Input</button>
                </div>
                {inputs.map((input, index) => (
                  <div key={index} className="query-input-row">
                    <input
                      type="text"
                      placeholder="Param name"
                      value={input.name}
                      onChange={(e) => updateInput(index, 'name', e.target.value)}
                      className="query-input-field"
                    />
                    <span className="query-input-arrow">←</span>
                    <input
                      type="text"
                      placeholder="Source node ID"
                      value={input.sourceNode}
                      onChange={(e) => updateInput(index, 'sourceNode', e.target.value)}
                      className="query-input-field small"
                    />
                    <span className="query-input-dot">.</span>
                    <input
                      type="text"
                      placeholder="Field"
                      value={input.sourceField}
                      onChange={(e) => updateInput(index, 'sourceField', e.target.value)}
                      className="query-input-field"
                    />
                    <button className="query-remove-btn" onClick={() => removeInput(index)}>×</button>
                  </div>
                ))}
                {inputs.length === 0 && (
                  <div className="query-empty">No input parameters defined</div>
                )}
              </div>
            )}

            {activeTab === 'outputs' && (
              <div className="query-section">
                <div className="query-section-header">
                  <label>Output Fields</label>
                  <button className="query-add-btn" onClick={addOutput}>+ Add Output</button>
                </div>
                {outputs.map((output, index) => (
                  <div key={index} className="query-output-row">
                    <input
                      type="text"
                      placeholder="Source expression"
                      value={output.name}
                      onChange={(e) => updateOutput(index, 'name', e.target.value)}
                      className="query-output-field"
                    />
                    <span className="query-output-arrow">→</span>
                    <input
                      type="text"
                      placeholder="Alias"
                      value={output.alias}
                      onChange={(e) => updateOutput(index, 'alias', e.target.value)}
                      className="query-output-field small"
                    />
                    <select
                      value={output.type || 'string'}
                      onChange={(e) => updateOutput(index, 'type', e.target.value)}
                      className="query-output-select"
                    >
                      <option value="string">string</option>
                      <option value="number">number</option>
                      <option value="date">date</option>
                      <option value="boolean">boolean</option>
                    </select>
                    <button className="query-remove-btn" onClick={() => removeOutput(index)}>×</button>
                  </div>
                ))}
                {outputs.length === 0 && (
                  <div className="query-empty">No output fields defined</div>
                )}
              </div>
            )}

            {activeTab === 'filter' && (
              <div className="query-section">
                <div className="query-section-header">
                  <label>Filter Conditions</label>
                  <button className="query-add-btn" onClick={addCondition}>+ Add Condition</button>
                </div>
                {conditions.map((cond, index) => (
                  <div key={index} className="query-condition-row">
                    <input
                      type="text"
                      placeholder="Field"
                      value={cond.field}
                      onChange={(e) => updateCondition(index, 'field', e.target.value)}
                      className="query-condition-field"
                    />
                    <select
                      value={cond.operator}
                      onChange={(e) => updateCondition(index, 'operator', e.target.value)}
                      className="query-condition-select"
                    >
                      {inputOperators.map((op) => (
                        <option key={op.value} value={op.value}>{op.icon} {op.label}</option>
                      ))}
                    </select>
                    <input
                      type="text"
                      placeholder="Value (use {{param}} for input)"
                      value={cond.value}
                      onChange={(e) => updateCondition(index, 'value', e.target.value)}
                      className="query-condition-field"
                    />
                    <button className="query-remove-btn" onClick={() => removeCondition(index)}>×</button>
                  </div>
                ))}
                {conditions.length === 0 && (
                  <div className="query-empty">No filter conditions defined</div>
                )}
              </div>
            )}
          </div>
        </div>
        
        {/* Output handle (right side) */}
        <Handle
          type="source"
          position={Position.Right}
          className="node-handle"
          style={{ backgroundColor: queryType.color }}
        />
        
        <style>{`
          .query-node-editing {
            border: 2px solid #FF9800 !important;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(255, 152, 0, 0.3) !important;
          }
          
          .query-edit-content {
            padding: 16px;
            max-height: 450px;
            overflow-y: auto;
          }
          
          .query-edit-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
          }
          
          .query-edit-icon {
            font-size: 28px;
          }
          
          .query-edit-badge {
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 11px;
            color: #fff;
            font-weight: 600;
          }
          
          .query-edit-label-input {
            flex: 1;
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
          }
          
          .query-edit-close {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: none;
            background: #4CAF50;
            color: #fff;
            cursor: pointer;
            font-size: 14px;
          }
          
          .query-edit-tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 12px;
            border-bottom: 1px solid #e0e0e0;
            padding-bottom: 8px;
          }
          
          .query-tab {
            padding: 6px 12px;
            border: none;
            border-radius: 6px;
            background: transparent;
            cursor: pointer;
            font-size: 12px;
            color: #666;
            transition: all 0.2s;
          }
          
          .query-tab:hover {
            background: #f5f5f5;
          }
          
          .query-tab.active {
            background: #FF9800;
            color: #fff;
          }
          
          .query-tab-content {
            background: #fff;
            border-radius: 8px;
            padding: 12px;
          }
          
          .query-section {
            display: flex;
            flex-direction: column;
            gap: 12px;
          }
          
          .query-section-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          
          .query-section-header label {
            font-weight: 600;
            font-size: 12px;
            color: #333;
          }
          
          .query-type-selector {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 6px;
          }
          
          .query-type-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 10px 6px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            background: #fff;
            cursor: pointer;
            transition: all 0.2s;
            gap: 4px;
          }
          
          .query-type-btn:hover {
            border-color: #bbb;
          }
          
          .query-type-btn.active {
            border-width: 2px;
            background: #FFF8E1;
          }
          
          .query-type-btn span:first-child {
            font-size: 20px;
          }
          
          .query-type-btn span:last-child {
            font-size: 10px;
            color: #666;
          }
          
          .query-editor label {
            display: block;
            font-size: 11px;
            font-weight: 600;
            color: #666;
            margin-bottom: 6px;
            text-transform: uppercase;
          }
          
          .query-textarea {
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 12px;
            resize: vertical;
          }
          
          .query-textarea:focus {
            outline: none;
            border-color: #FF9800;
          }
          
          .query-snippets {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
          }
          
          .query-snippets span {
            font-size: 11px;
            color: #666;
          }
          
          .query-snippets button {
            padding: 4px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #f5f5f5;
            cursor: pointer;
            font-size: 10px;
          }
          
          .query-snippets button:hover {
            border-color: #FF9800;
            background: #FFF8E1;
          }
          
          .query-add-btn {
            padding: 4px 10px;
            border: 1px solid #FF9800;
            border-radius: 4px;
            background: #FFF8E1;
            color: #FF9800;
            cursor: pointer;
            font-size: 11px;
            font-weight: 600;
          }
          
          .query-input-row,
          .query-output-row,
          .query-condition-row {
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;
          }
          
          .query-input-field,
          .query-output-field,
          .query-condition-field {
            flex: 1;
            padding: 6px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
          }
          
          .query-input-field.small,
          .query-output-field.small {
            flex: 0.8;
          }
          
          .query-input-arrow,
          .query-output-arrow {
            color: #FF9800;
            font-weight: bold;
          }
          
          .query-input-dot {
            color: #999;
          }
          
          .query-output-select {
            padding: 6px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 11px;
            background: #fff;
          }
          
          .query-condition-select {
            padding: 6px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 11px;
            background: #fff;
            min-width: 120px;
          }
          
          .query-remove-btn {
            width: 22px;
            height: 22px;
            border: none;
            border-radius: 4px;
            background: #ffebee;
            color: #f44336;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
          }
          
          .query-empty {
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
          }
        `}</style>
      </div>
    );
  }

  // View mode - compact display
  return (
    <div 
      className={`query-node ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : queryType.color,
        backgroundColor: selected ? '#E3F2FD' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setEditMode(true)}
      title="Double-click to edit query"
    >
      {/* Input handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: queryType.color, top: '30%' }}
      />
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: queryType.color, top: '70%' }}
      />
      
      <div className="query-view-content">
        {/* Header */}
        <div className="query-view-header">
          <span className="query-view-icon" style={{ color: queryType.color }}>
            {queryType.icon}
          </span>
          <span 
            className="query-view-badge"
            style={{ backgroundColor: queryType.color }}
          >
            {queryType.label}
          </span>
          {selected && (
            <button 
              className="query-view-edit"
              onClick={(e) => {
                e.stopPropagation();
                setEditMode(true);
              }}
            >
              ✏️
            </button>
          )}
        </div>

        {/* Label */}
        <div className="query-view-label">{editData.label}</div>

        {/* Summary */}
        <div className="query-view-summary">
          {(inputs.length > 0 || outputs.length > 0 || conditions.length > 0) && (
            <div className="query-summary-items">
              {inputs.length > 0 && (
                <span className="query-summary-item">
                  📥 {inputs.length} in
                </span>
              )}
              {outputs.length > 0 && (
                <span className="query-summary-item">
                  📤 {outputs.length} out
                </span>
              )}
              {conditions.length > 0 && (
                <span className="query-summary-item">
                  🔍 {conditions.length} filter
                </span>
              )}
            </div>
          )}
        </div>

        {/* Query preview */}
        <div className="query-view-preview">
          <code>{editData.query?.substring(0, 50)}{editData.query?.length > 50 ? '...' : ''}</code>
        </div>
      </div>
      
      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: queryType.color }}
      />
      
      <style>{`
        .query-node {
          min-width: 180px;
          border: 2px solid #FF9800;
          border-radius: 10px;
          padding: 0;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s ease;
        }
        
        .query-node:hover {
          box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .query-node.selected {
          border-color: #2196F3;
          background-color: #E3F2FD;
        }
        
        .query-view-content {
          padding: 12px;
        }
        
        .query-view-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }
        
        .query-view-icon {
          font-size: 24px;
        }
        
        .query-view-badge {
          padding: 3px 10px;
          border-radius: 14px;
          font-size: 10px;
          color: #fff;
          font-weight: 600;
        }
        
        .query-view-edit {
          margin-left: auto;
          width: 26px;
          height: 26px;
          border-radius: 50%;
          border: none;
          background: #2196F3;
          color: #fff;
          cursor: pointer;
          font-size: 12px;
        }
        
        .query-view-label {
          font-weight: 600;
          font-size: 13px;
          color: #333;
          margin-bottom: 8px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .query-view-summary {
          margin-bottom: 8px;
        }
        
        .query-summary-items {
          display: flex;
          gap: 8px;
        }
        
        .query-summary-item {
          padding: 2px 8px;
          background: #f5f5f5;
          border-radius: 10px;
          font-size: 10px;
          color: #666;
        }
        
        .query-view-preview {
          padding: 6px 8px;
          background: #f5f5f5;
          border-radius: 4px;
          font-size: 10px;
          color: #666;
          overflow: hidden;
        }
        
        .query-view-preview code {
          font-family: monospace;
          white-space: nowrap;
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

export default memo(QueryNode);
