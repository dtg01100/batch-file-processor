/** Pipeline Query Node
 * 
 * SQL, Python, or JavaScript query that can:
 * - Generate data (Source mode)
 * - Transform data (Transform mode)
 * - Execute/write data (Sink mode)
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const queryTypes = [
  { value: 'sql', label: 'SQL Query', icon: '🗃️', color: '#FF9800' },
  { value: 'python', label: 'Python Script', icon: '🐍', color: '#4CAF50' },
  { value: 'javascript', label: 'JavaScript', icon: '📜', color: '#FFC107' },
];

const queryModes = [
  { value: 'source', label: 'Source', icon: '📤', desc: 'Generates output only' },
  { value: 'transform', label: 'Transform', icon: '🔄', desc: 'Input → Output' },
  { value: 'sink', label: 'Sink', icon: '📥', desc: 'Consumes input only' },
];

function PipelineQueryNode({ data, selected, onUpdate }) {
  const [showEditor, setShowEditor] = useState(false);
  
  const [editData, setEditData] = useState({
    label: data.label || 'Query',
    queryType: data.queryType || 'sql',
    mode: data.mode || 'transform',
    query: data.query || '',
    inputs: data.inputs || '[]',
    outputs: data.outputs || '[]',
  });
  
  const queryType = queryTypes.find(q => q.value === editData.queryType) || queryTypes[0];
  const mode = queryModes.find(m => m.value === editData.mode) || queryModes[1];
  
  // Parse JSON safely
  const parseJson = (str, defaultVal) => {
    try {
      return JSON.parse(str);
    } catch {
      return defaultVal;
    }
  };
  
  const inputs = parseJson(editData.inputs, []);
  const outputs = parseJson(editData.outputs, []);
  
  const handleUpdate = (key, value) => {
    const newData = { ...editData, [key]: value };
    setEditData(newData);
    onUpdate?.(data.id, newData);
  };
  
  return (
    <div 
      className={`pipeline-node query ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : queryType.color,
        backgroundColor: selected ? '#FFF8E1' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => setShowEditor(true)}
      title="Double-click to edit query"
    >
      {/* Input handle - only for transform/sink modes */}
      {(editData.mode === 'transform' || editData.mode === 'sink') && (
        <Handle
          type="target"
          position={Position.Left}
          className="node-handle"
          style={{ backgroundColor: queryType.color, top: '50%' }}
        />
      )}
      
      <div className="node-content">
        <div className="node-icon" style={{ color: queryType.color }}>
          {queryType.icon}
        </div>
        <div className="node-text">
          <div className="node-label">{editData.label}</div>
          <div className="node-mode">
            <span className="mode-badge" style={{ backgroundColor: mode.icon === '📤' ? '#4CAF50' : mode.icon === '📥' ? '#f44336' : '#2196F3' }}>
              {mode.icon} {mode.label}
            </span>
            <span className="query-type">{queryType.label}</span>
          </div>
          {(inputs.length > 0 || outputs.length > 0) && (
            <div className="node-summary">
              {inputs.length > 0 && <span>📥 {inputs.length} in</span>}
              {outputs.length > 0 && <span> 📤 {outputs.length} out</span>}
            </div>
          )}
        </div>
      </div>
      
      {/* Output handle - only for source/transform modes */}
      {(editData.mode === 'source' || editData.mode === 'transform') && (
        <Handle
          type="source"
          position={Position.Right}
          className="node-handle"
          style={{ backgroundColor: queryType.color, top: '50%' }}
        />
      )}
      
      {showEditor && (
        <QueryEditor
          editData={editData}
          inputs={inputs}
          outputs={outputs}
          onUpdate={handleUpdate}
          onClose={() => setShowEditor(false)}
        />
      )}
      
      <style>{`
        .pipeline-node.query {
          min-width: 160px;
          border: 2px solid #FF9800;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.query:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.query.selected {
          border-color: #2196F3;
          background-color: #FFF8E1;
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
        
        .node-mode {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 4px;
        }
        
        .mode-badge {
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 10px;
          color: #fff;
          font-weight: 600;
        }
        
        .query-type {
          font-size: 10px;
          color: #666;
        }
        
        .node-summary {
          display: flex;
          gap: 10px;
          margin-top: 4px;
          font-size: 10px;
          color: #999;
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

// Query editor component
function QueryEditor({ editData, inputs, outputs, onUpdate, onClose }) {
  const [localInputs, setLocalInputs] = useState(inputs);
  const [localOutputs, setLocalOutputs] = useState(outputs);
  
  const queryTypes = [
    { value: 'sql', label: 'SQL Query', icon: '🗃️', color: '#FF9800' },
    { value: 'python', label: 'Python Script', icon: '🐍', color: '#4CAF50' },
    { value: 'javascript', label: 'JavaScript', icon: '📜', color: '#FFC107' },
  ];
  
  const queryModes = [
    { value: 'source', label: 'Source', icon: '📤', desc: 'Generates output from query' },
    { value: 'transform', label: 'Transform', icon: '🔄', desc: 'Processes input, outputs result' },
    { value: 'sink', label: 'Sink', icon: '📥', desc: 'Consumes input, no output' },
  ];
  
  const addInput = () => {
    setLocalInputs([...localInputs, { name: '', type: 'string' }]);
  };
  
  const updateInput = (index, field, value) => {
    const newInputs = [...localInputs];
    newInputs[index] = { ...newInputs[index], [field]: value };
    setLocalInputs(newInputs);
  };
  
  const removeInput = (index) => {
    setLocalInputs(localInputs.filter((_, i) => i !== index));
  };
  
  const addOutput = () => {
    setLocalOutputs([...localOutputs, { name: '', type: 'string' }]);
  };
  
  const updateOutput = (index, field, value) => {
    const newOutputs = [...localOutputs];
    newOutputs[index] = { ...newOutputs[index], [field]: value };
    setLocalOutputs(newOutputs);
  };
  
  const removeOutput = (index) => {
    setLocalOutputs(localOutputs.filter((_, i) => i !== index));
  };
  
  const saveAndClose = () => {
    onUpdate('mode', editData.mode);
    onUpdate('queryType', editData.queryType);
    onUpdate('query', editData.query);
    onUpdate('inputs', JSON.stringify(localInputs, null, 2));
    onUpdate('outputs', JSON.stringify(localOutputs, null, 2));
    onClose();
  };
  
  const exampleQueries = {
    sql: {
      source: 'SELECT * FROM customers WHERE active = true',
      transform: 'SELECT id, name, total * 1.1 AS total_with_tax FROM {{table}}',
      sink: 'INSERT INTO audit_log (action, timestamp) VALUES (\'processed\', NOW())',
    },
    python: {
      source: '# Generate sample data\ndata = [{"id": i, "name": f"Item {i}"} for i in range(100)]',
      transform: '# Transform input\nresult = [row for row in input_data if row["status"] == "active"]',
      sink: '# Write to file\nwith open("output.json", "w") as f:\n    json.dump(input_data, f)',
    },
    javascript: {
      source: '// Generate data\nconst data = Array.from({length: 50}, (_, i) => ({id: i + 1, value: Math.random()}));',
      transform: '// Filter and transform\nconst result = input.filter(x => x.status === "active").map(x => ({...x, processed: true}));',
      sink: '// Write to console/file\nconsole.log(`Processed ${input.length} records`);',
    },
  };
  
  return (
    <div className="query-overlay">
      <div className="query-editor">
        <div className="query-header">
          <h3>📝 Query</h3>
          <button className="query-close" onClick={onClose}>×</button>
        </div>
        
        <div className="query-content">
          {/* Mode selector */}
          <div className="query-section">
            <label>Query Mode</label>
            <div className="mode-grid">
              {queryModes.map((mode) => (
                <button
                  key={mode.value}
                  className={`mode-btn ${editData.mode === mode.value ? 'active' : ''}`}
                  onClick={() => onUpdate('mode', mode.value)}
                >
                  <span className="mode-icon">{mode.icon}</span>
                  <span className="mode-label">{mode.label}</span>
                  <span className="mode-desc">{mode.desc}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Query type */}
          <div className="query-section">
            <label>Query Type</label>
            <div className="type-row">
              {queryTypes.map((type) => (
                <button
                  key={type.value}
                  className={`type-btn ${editData.queryType === type.value ? 'active' : ''}`}
                  style={{ borderColor: type.color }}
                  onClick={() => onUpdate('queryType', type.value)}
                >
                  <span>{type.icon}</span>
                  <span>{type.label}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Label */}
          <div className="query-section">
            <label>Label</label>
            <input
              type="text"
              value={editData.label}
              onChange={(e) => onUpdate('label', e.target.value)}
              className="label-input"
              placeholder="Query name"
            />
          </div>
          
          {/* Query editor */}
          <div className="query-section">
            <label>Query / Script</label>
            <textarea
              value={editData.query}
              onChange={(e) => onUpdate('query', e.target.value)}
              className="query-textarea"
              rows={8}
              placeholder={exampleQueries[editData.queryType]?.[editData.mode] || 'Enter your query...'}
            />
            <div className="query-help">
              Use <code>{`{{param}}`}</code> for input parameters
            </div>
          </div>
          
          {/* Input parameters - only for transform/sink */}
          {(editData.mode === 'transform' || editData.mode === 'sink') && (
            <div className="query-section">
              <label>Input Parameters</label>
              {localInputs.map((input, i) => (
                <div key={i} className="param-row">
                  <input
                    type="text"
                    placeholder="Parameter name"
                    value={input.name}
                    onChange={(e) => updateInput(i, 'name', e.target.value)}
                    className="param-name"
                  />
                  <select
                    value={input.type}
                    onChange={(e) => updateInput(i, 'type', e.target.value)}
                    className="param-type"
                  >
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="array">array</option>
                    <option value="object">object</option>
                  </select>
                  <button className="param-remove" onClick={() => removeInput(i)}>×</button>
                </div>
              ))}
              <button className="param-add" onClick={addInput}>+ Add Input</button>
            </div>
          )}
          
          {/* Output fields - only for source/transform */}
          {(editData.mode === 'source' || editData.mode === 'transform') && (
            <div className="query-section">
              <label>Output Fields</label>
              {localOutputs.map((output, i) => (
                <div key={i} className="param-row">
                  <input
                    type="text"
                    placeholder="Field name"
                    value={output.name}
                    onChange={(e) => updateOutput(i, 'name', e.target.value)}
                    className="param-name"
                  />
                  <select
                    value={output.type}
                    onChange={(e) => updateOutput(i, 'type', e.target.value)}
                    className="param-type"
                  >
                    <option value="string">string</option>
                    <option value="number">number</option>
                    <option value="boolean">boolean</option>
                    <option value="date">date</option>
                    <option value="array">array</option>
                  </select>
                  <button className="param-remove" onClick={() => removeOutput(i)}>×</button>
                </div>
              ))}
              <button className="param-add" onClick={addOutput}>+ Add Output</button>
            </div>
          )}
          
          {/* Visual preview */}
          <div className="query-preview">
            <div className="preview-title">Flow Diagram</div>
            <div className="preview-flow">
              {editData.mode === 'source' && (
                <>
                  <div className="preview-node source">
                    <span className="preview-icon">📤</span>
                    <span>Query Output</span>
                  </div>
                </>
              )}
              {editData.mode === 'transform' && (
                <>
                  <div className="preview-node input">
                    <span>Input</span>
                  </div>
                  <span className="preview-arrow">→</span>
                  <div className="preview-node process">
                    <span className="preview-icon">📝</span>
                    <span>Query</span>
                  </div>
                  <span className="preview-arrow">→</span>
                  <div className="preview-node output">
                    <span>Output</span>
                  </div>
                </>
              )}
              {editData.mode === 'sink' && (
                <>
                  <div className="preview-node input">
                    <span>Input</span>
                  </div>
                  <span className="preview-arrow">→</span>
                  <div className="preview-node sink">
                    <span className="preview-icon">📥</span>
                    <span>Query (No Output)</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
        
        <div className="query-footer">
          <button className="cancel-btn" onClick={onClose}>Cancel</button>
          <button className="save-btn" onClick={saveAndClose}>✓ Apply</button>
        </div>
      </div>
      
      <style>{`
        .query-overlay {
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
        
        .query-editor {
          background: #fff;
          border-radius: 12px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.2);
          width: 480px;
          max-height: 550px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }
        
        .query-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
          color: #fff;
        }
        
        .query-header h3 {
          margin: 0;
          font-size: 16px;
        }
        
        .query-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: rgba(255,255,255,0.2);
          color: #fff;
          cursor: pointer;
          font-size: 18px;
        }
        
        .query-content {
          padding: 16px;
          overflow-y: auto;
          flex: 1;
        }
        
        .query-section {
          margin-bottom: 16px;
        }
        
        .query-section label {
          display: block;
          font-size: 12px;
          font-weight: 600;
          color: #666;
          margin-bottom: 8px;
        }
        
        .mode-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
        }
        
        .mode-btn {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 10px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .mode-btn.active {
          border-color: #2196F3;
          background: #E3F2FD;
        }
        
        .mode-icon {
          font-size: 20px;
          margin-bottom: 4px;
        }
        
        .mode-label {
          font-size: 12px;
          font-weight: 600;
          color: #333;
        }
        
        .mode-desc {
          font-size: 9px;
          color: #999;
          text-align: center;
          margin-top: 2px;
        }
        
        .type-row {
          display: flex;
          gap: 8px;
        }
        
        .type-btn {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 10px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          transition: all 0.2s;
          font-size: 12px;
        }
        
        .type-btn.active {
          border-width: 2px;
          background: #FFF8E1;
        }
        
        .label-input {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 13px;
        }
        
        .query-textarea {
          width: 100%;
          padding: 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-family: 'Monaco', 'Menlo', monospace;
          font-size: 12px;
          resize: vertical;
        }
        
        .query-help {
          font-size: 11px;
          color: #666;
          margin-top: 6px;
        }
        
        .query-help code {
          background: #f5f5f5;
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 10px;
        }
        
        .param-row {
          display: flex;
          gap: 6px;
          margin-bottom: 6px;
        }
        
        .param-name {
          flex: 1;
          padding: 8px 10px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 12px;
        }
        
        .param-type {
          width: 100px;
          padding: 8px;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 11px;
          background: #fff;
        }
        
        .param-remove {
          width: 28px;
          border: none;
          border-radius: 4px;
          background: #ffebee;
          color: #f44336;
          cursor: pointer;
          font-size: 14px;
        }
        
        .param-add {
          width: 100%;
          padding: 8px;
          border: 1px dashed #FF9800;
          border-radius: 4px;
          background: transparent;
          color: #FF9800;
          cursor: pointer;
          font-size: 12px;
        }
        
        .query-preview {
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
        
        .preview-flow {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 8px;
        }
        
        .preview-node {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 12px;
          border-radius: 6px;
          font-size: 11px;
          font-weight: 500;
        }
        
        .preview-node.input {
          background: #E3F2FD;
          color: #1976D2;
        }
        
        .preview-node.output {
          background: #E8F5E9;
          color: #388E3C;
        }
        
        .preview-node.source {
          background: #FFF8E1;
          color: #F57C00;
        }
        
        .preview-node.sink {
          background: #FFEBEE;
          color: #D32F2F;
        }
        
        .preview-node.process {
          background: #FFF8E1;
          color: #E65100;
        }
        
        .preview-icon {
          font-size: 14px;
        }
        
        .preview-arrow {
          color: #999;
          font-size: 16px;
        }
        
        .query-footer {
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
          background: #FF9800;
          color: #fff;
          cursor: pointer;
          font-size: 13px;
          font-weight: 600;
        }
      `}</style>
    </div>
  );
}

export default memo(PipelineQueryNode);
