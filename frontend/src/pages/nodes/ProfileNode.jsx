/** Output Profile Node
 *
 * Custom React Flow node for representing output profiles
 * with format icons, encoding controls, and field mapping.
 */

import React, { memo, useState } from 'react';
import { Handle, Position } from 'reactflow';

const formatOptions = [
  { value: 'csv', label: 'CSV', icon: '📊', color: '#4CAF50' },
  { value: 'edi', label: 'EDI', icon: '📋', color: '#2196F3' },
  { value: 'estore-einvoice', label: 'eStore', icon: '🧾', color: '#9C27B0' },
  { value: 'fintech', label: 'Fintech', icon: '🏦', color: '#FF9800' },
  { value: 'scannerware', label: 'Scannerware', icon: '📷', color: '#607D8B' },
  { value: 'scansheet-type-a', label: 'Scansheet', icon: '📑', color: '#795548' },
  { value: 'simplified-csv', label: 'Simple CSV', icon: '📈', color: '#4CAF50' },
  { value: 'stewart-custom', label: 'Stewart', icon: '⚡', color: '#E91E63' },
  { value: 'yellowdog-csv', label: 'Yellowdog', icon: '🐕', color: '#FF5722' },
];

const encodingOptions = [
  { value: 'utf-8', label: 'UTF-8', icon: '🔤' },
  { value: 'ascii', label: 'ASCII', icon: '🔡' },
  { value: 'cp1252', label: 'Win-1252', icon: '🪟' },
];

const lineEndingOptions = [
  { value: 'lf', label: 'LF', icon: '↩' },
  { value: 'crlf', label: 'CRLF', icon: '↵' },
  { value: 'cr', label: 'CR', icon: '⏎' },
];

function ProfileNode({ data, selected, onUpdate }) {
  const [editMode, setEditMode] = useState(false);
  const [mappingMode, setMappingMode] = useState(false);
  const [editData, setEditData] = useState({
    label: data.label || 'Output Profile',
    format: data.format || 'csv',
    ediTweaks: data.ediTweaks || '{}',
    customSettings: data.customSettings || '{}',
    fieldMapping: data.fieldMapping || '[]',
  });

  const currentFormat = formatOptions.find(f => f.value === editData.format) || formatOptions[0];

  // Parse JSON safely
  const parseJson = (str, defaultVal) => {
    try {
      return JSON.parse(str);
    } catch {
      return defaultVal;
    }
  };

  // Handle format change
  const handleFormatChange = (format) => {
    setEditData({ ...editData, format });
    onUpdate?.(data.id, { format });
  };

  // Handle label change
  const handleLabelChange = (label) => {
    setEditData({ ...editData, label });
    onUpdate?.(data.id, { label });
  };

  // Handle EDI tweaks change
  const handleEdiTweaksChange = (key, value) => {
    const tweaks = parseJson(editData.ediTweaks, {});
    tweaks[key] = value;
    const newTweaks = JSON.stringify(tweaks, null, 2);
    setEditData({ ...editData, ediTweaks: newTweaks });
    onUpdate?.(data.id, { ediTweaks: newTweaks });
  };

  // Handle custom settings change
  const handleCustomSettingsChange = (key, value) => {
    const settings = parseJson(editData.customSettings, {});
    settings[key] = value;
    const newSettings = JSON.stringify(settings, null, 2);
    setEditData({ ...editData, customSettings: newSettings });
    onUpdate?.(data.id, { customSettings: newSettings });
  };

  // Handle field mapping change
  const handleFieldMappingChange = (index, field, value) => {
    const mapping = parseJson(editData.fieldMapping, []);
    if (!mapping[index]) mapping[index] = {};
    mapping[index][field] = value;
    const newMapping = JSON.stringify(mapping, null, 2);
    setEditData({ ...editData, fieldMapping: newMapping });
    onUpdate?.(data.id, { fieldMapping: newMapping });
  };

  // Add new field mapping
  const addFieldMapping = () => {
    const mapping = parseJson(editData.fieldMapping, []);
    mapping.push({ source: '', target: '', transform: '' });
    const newMapping = JSON.stringify(mapping, null, 2);
    setEditData({ ...editData, fieldMapping: newMapping });
    onUpdate?.(data.id, { fieldMapping: newMapping });
  };

  // Remove field mapping
  const removeFieldMapping = (index) => {
    const mapping = parseJson(editData.fieldMapping, []);
    mapping.splice(index, 1);
    const newMapping = JSON.stringify(mapping, null, 2);
    setEditData({ ...editData, fieldMapping: newMapping });
    onUpdate?.(data.id, { fieldMapping: newMapping });
  };

  const ediTweaksObj = parseJson(editData.ediTweaks, {});
  const customSettingsObj = parseJson(editData.customSettings, {});
  const fieldMapping = parseJson(editData.fieldMapping, []);

  const currentEncoding = encodingOptions.find(e => e.value === customSettingsObj.encoding) || encodingOptions[0];
  const currentLineEnding = lineEndingOptions.find(l => l.value === customSettingsObj['line ending']) || lineEndingOptions[0];
  const includeHeader = customSettingsObj['include header'] !== false;

  // Mapping mode - show field mapping editor
  if (mappingMode) {
    return (
      <div 
        className="profile-node profile-node-mapping"
        style={{ 
          borderColor: '#9C27B0',
          backgroundColor: '#F3E5F5',
          minWidth: '400px',
          maxWidth: '500px',
        }}
      >
        <Handle
          type="target"
          position={Position.Left}
          className="node-handle"
          style={{ backgroundColor: currentFormat.color }}
        />
        
        <div className="profile-mapping-content">
          {/* Header */}
          <div className="profile-mapping-header">
            <span className="profile-mapping-title">🔗 Field Mapping</span>
            <button 
              className="profile-mapping-close"
              onClick={() => setMappingMode(false)}
            >
              ✓
            </button>
          </div>

          {/* Mapping rows */}
          <div className="profile-mapping-rows">
            {fieldMapping.map((map, index) => (
              <div key={index} className="profile-mapping-row">
                <input
                  type="text"
                  placeholder="Source field"
                  value={map.source || ''}
                  onChange={(e) => handleFieldMappingChange(index, 'source', e.target.value)}
                  className="mapping-input"
                />
                <span className="mapping-arrow">→</span>
                <input
                  type="text"
                  placeholder="Target field"
                  value={map.target || ''}
                  onChange={(e) => handleFieldMappingChange(index, 'target', e.target.value)}
                  className="mapping-input"
                />
                <select
                  value={map.transform || 'none'}
                  onChange={(e) => handleFieldMappingChange(index, 'transform', e.target.value)}
                  className="mapping-select"
                >
                  <option value="none">direct</option>
                  <option value="upper">UPPER</option>
                  <option value="lower">lower</option>
                  <option value="title">Title</option>
                  <option value="trim">trim</option>
                  <option value="date">date</option>
                  <option value="number">number</option>
                </select>
                <button 
                  className="mapping-remove"
                  onClick={() => removeFieldMapping(index)}
                  title="Remove mapping"
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          {/* Add mapping button */}
          <button className="profile-mapping-add" onClick={addFieldMapping}>
            + Add Field Mapping
          </button>

          {/* Quick templates */}
          <div className="profile-mapping-templates">
            <span className="mapping-templates-label">Quick template:</span>
            <button onClick={() => {
              const template = [
                { source: 'InvoiceNumber', target: 'InvoiceNum', transform: 'none' },
                { source: 'InvoiceDate', target: 'Date', transform: 'date' },
                { source: 'TotalAmount', target: 'Amount', transform: 'number' },
                { source: 'CustomerName', target: 'Customer', transform: 'title' },
              ];
              const newMapping = JSON.stringify(template, null, 2);
              setEditData({ ...editData, fieldMapping: newMapping });
              onUpdate?.(data.id, { fieldMapping: newMapping });
            }}>Invoice</button>
            <button onClick={() => {
              const template = [
                { source: 'AccountNumber', target: 'Acct', transform: 'none' },
                { source: 'TransactionDate', target: 'Date', transform: 'date' },
                { source: 'DebitAmount', target: 'Debit', transform: 'number' },
                { source: 'CreditAmount', target: 'Credit', transform: 'number' },
              ];
              const newMapping = JSON.stringify(template, null, 2);
              setEditData({ ...editData, fieldMapping: newMapping });
              onUpdate?.(data.id, { fieldMapping: newMapping });
            }}>Bank</button>
            <button onClick={() => {
              const template = [
                { source: 'SKU', target: 'ProductCode', transform: 'none' },
                { source: 'Description', target: 'Name', transform: 'none' },
                { source: 'Quantity', target: 'Qty', transform: 'number' },
                { source: 'UnitPrice', target: 'Price', transform: 'number' },
              ];
              const newMapping = JSON.stringify(template, null, 2);
              setEditData({ ...editData, fieldMapping: newMapping });
              onUpdate?.(data.id, { fieldMapping: newMapping });
            }}>Product</button>
          </div>
        </div>
        
        <Handle
          type="source"
          position={Position.Right}
          className="node-handle"
          style={{ backgroundColor: currentFormat.color }}
        />
        
        <style>{`
          .profile-node-mapping {
            border: 2px solid #9C27B0 !important;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(156, 39, 176, 0.3) !important;
          }
          
          .profile-mapping-content {
            padding: 16px;
            max-height: 400px;
            overflow-y: auto;
          }
          
          .profile-mapping-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
          }
          
          .profile-mapping-title {
            font-weight: 600;
            font-size: 14px;
            color: #9C27B0;
          }
          
          .profile-mapping-close {
            width: 28px;
            height: 28px;
            border-radius: 50%;
            border: none;
            background: #4CAF50;
            color: #fff;
            cursor: pointer;
            font-size: 14px;
          }
          
          .profile-mapping-rows {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 12px;
          }
          
          .profile-mapping-row {
            display: flex;
            align-items: center;
            gap: 6px;
          }
          
          .mapping-input {
            flex: 1;
            padding: 6px 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12px;
            background: #fff;
          }
          
          .mapping-input:focus {
            outline: none;
            border-color: #9C27B0;
          }
          
          .mapping-arrow {
            color: #9C27B0;
            font-weight: bold;
            font-size: 14px;
          }
          
          .mapping-select {
            padding: 6px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 11px;
            background: #fff;
            cursor: pointer;
          }
          
          .mapping-remove {
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
          
          .profile-mapping-add {
            width: 100%;
            padding: 8px;
            border: 2px dashed #9C27B0;
            border-radius: 6px;
            background: transparent;
            color: #9C27B0;
            cursor: pointer;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 12px;
          }
          
          .profile-mapping-add:hover {
            background: rgba(156, 39, 176, 0.05);
          }
          
          .profile-mapping-templates {
            display: flex;
            align-items: center;
            gap: 6px;
            flex-wrap: wrap;
            padding-top: 12px;
            border-top: 1px solid #e0e0e0;
          }
          
          .mapping-templates-label {
            font-size: 11px;
            color: #666;
          }
          
          .profile-mapping-templates button {
            padding: 4px 10px;
            border: 1px solid #ddd;
            border-radius: 12px;
            background: #fff;
            cursor: pointer;
            font-size: 11px;
            transition: all 0.15s;
          }
          
          .profile-mapping-templates button:hover {
            border-color: #9C27B0;
            background: #F3E5F5;
          }
        `}</style>
      </div>
    );
  }

  // View mode - show compact display with encoding controls
  if (!editMode) {
    return (
      <div 
        className={`profile-node ${selected ? 'selected' : ''}`}
        style={{ 
          borderColor: selected ? '#2196F3' : currentFormat.color,
          backgroundColor: selected ? '#E3F2FD' : '#fff',
          cursor: 'pointer'
        }}
        onDoubleClick={() => setEditMode(true)}
        title="Double-click to edit full settings"
      >
        {/* Input handle (left side) */}
        <Handle
          type="target"
          position={Position.Left}
          className="node-handle"
          style={{ backgroundColor: currentFormat.color }}
        />
        
        <div className="profile-view-content">
          {/* Header row */}
          <div className="profile-view-header">
            <span className="profile-view-icon" style={{ color: currentFormat.color }}>
              {currentFormat.icon}
            </span>
            <span 
              className="profile-view-badge"
              style={{ backgroundColor: currentFormat.color }}
            >
              {currentFormat.label}
            </span>
            {selected && (
              <div className="profile-view-actions">
                <button 
                  className="profile-view-action"
                  onClick={(e) => {
                    e.stopPropagation();
                    setMappingMode(true);
                  }}
                  title="Field mapping"
                >
                  🔗
                </button>
                <button 
                  className="profile-view-action"
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditMode(true);
                  }}
                  title="Edit settings"
                >
                  ✏️
                </button>
              </div>
            )}
          </div>

          {/* Label */}
          <div className="profile-view-label">{data.label || 'Output Profile'}</div>

          {/* Encoding controls - always visible */}
          <div className="profile-view-encoding">
            <div className="encoding-group">
              <span className="encoding-label">ENC:</span>
              <div className="encoding-options">
                {encodingOptions.map((enc) => (
                  <button
                    key={enc.value}
                    className={`encoding-btn ${customSettingsObj.encoding === enc.value ? 'active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCustomSettingsChange('encoding', enc.value);
                    }}
                    title={enc.label}
                  >
                    {enc.icon}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="encoding-group">
              <span className="encoding-label">EOL:</span>
              <div className="encoding-options">
                {lineEndingOptions.map((le) => (
                  <button
                    key={le.value}
                    className={`encoding-btn ${customSettingsObj['line ending'] === le.value ? 'active' : ''}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCustomSettingsChange('line ending', le.value);
                    }}
                    title={le.label}
                  >
                    {le.icon}
                  </button>
                ))}
              </div>
            </div>

            <button 
              className={`header-btn ${includeHeader ? 'active' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                handleCustomSettingsChange('include header', !includeHeader);
              }}
              title={includeHeader ? 'Header row included' : 'No header row'}
            >
              H{includeHeader ? '✓' : '✗'}
            </button>
          </div>

          {/* Field mapping indicator */}
          {fieldMapping.length > 0 && (
            <div className="profile-view-mapping" onClick={(e) => { e.stopPropagation(); setMappingMode(true); }}>
              <span className="mapping-indicator">🔗</span>
              <span className="mapping-count">{fieldMapping.length} field{s.fieldMapping.length > 1 ? 's' : ''} mapped</span>
              <span className="mapping-preview">
                {fieldMapping.slice(0, 3).map(m => m.target || m.source).join(', ')}
                {fieldMapping.length > 3 && '...'}
              </span>
            </div>
          )}

          {/* EDI tweaks indicator */}
          {Object.keys(ediTweaksObj).some(k => ediTweaksObj[k]) && (
            <div className="profile-view-edi">
              <span className="edi-label">EDI:</span>
              <span className="edi-values">
                {ediTweaksObj.delimiter || '~'} / {ediTweaksObj['segment terminator'] || '*'} / {ediTweaksObj['element separator'] || '^'}
              </span>
            </div>
          )}
        </div>
        
        {/* Output handle (right side) */}
        <Handle
          type="source"
          position={Position.Right}
          className="node-handle"
          style={{ backgroundColor: currentFormat.color }}
        />
        
        <style>{`
          .profile-node {
            min-width: 200px;
            border: 2px solid #9C27B0;
            border-radius: 10px;
            padding: 0;
            background: #fff;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s ease;
          }
          
          .profile-node:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
          }
          
          .profile-node.selected {
            border-color: #2196F3;
            background-color: #E3F2FD;
          }
          
          .profile-view-content {
            padding: 12px;
          }
          
          .profile-view-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
          }
          
          .profile-view-icon {
            font-size: 24px;
          }
          
          .profile-view-badge {
            padding: 3px 10px;
            border-radius: 14px;
            font-size: 11px;
            color: #fff;
            font-weight: 600;
          }
          
          .profile-view-actions {
            display: flex;
            gap: 4px;
            margin-left: auto;
          }
          
          .profile-view-action {
            width: 26px;
            height: 26px;
            border: none;
            border-radius: 50%;
            background: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            transition: all 0.2s;
            border: 1px solid #ddd;
          }
          
          .profile-view-action:hover {
            background: #2196F3;
            border-color: #2196F3;
          }
          
          .profile-view-label {
            font-weight: 600;
            font-size: 13px;
            color: #333;
            margin-bottom: 10px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
          }
          
          .profile-view-encoding {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
          }
          
          .encoding-group {
            display: flex;
            align-items: center;
            gap: 4px;
            background: #f5f5f5;
            padding: 4px 6px;
            border-radius: 6px;
          }
          
          .encoding-label {
            font-size: 10px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
          }
          
          .encoding-options {
            display: flex;
            gap: 2px;
          }
          
          .encoding-btn {
            width: 22px;
            height: 22px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #fff;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            transition: all 0.15s;
          }
          
          .encoding-btn:hover {
            border-color: #999;
            background: #fafafa;
          }
          
          .encoding-btn.active {
            border-color: #2196F3;
            background: #E3F2FD;
            color: #1976D2;
          }
          
          .header-btn {
            width: 24px;
            height: 24px;
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #fff;
            cursor: pointer;
            font-size: 10px;
            font-weight: 600;
            color: #999;
            transition: all 0.15s;
          }
          
          .header-btn:hover {
            border-color: #999;
          }
          
          .header-btn.active {
            border-color: #4CAF50;
            background: #E8F5E9;
            color: #4CAF50;
          }
          
          .profile-view-mapping {
            margin-top: 8px;
            padding: 6px 8px;
            background: linear-gradient(135deg, #F3E5F5 0%, #E1BEE7 100%);
            border-radius: 6px;
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
          }
          
          .profile-view-mapping:hover {
            background: linear-gradient(135deg, #E1BEE7 0%, #CE93D8 100%);
          }
          
          .mapping-indicator {
            font-size: 12px;
          }
          
          .mapping-count {
            font-weight: 600;
            color: #7B1FA2;
          }
          
          .mapping-preview {
            color: #666;
            margin-left: auto;
            font-family: monospace;
            font-size: 10px;
          }
          
          .profile-view-edi {
            margin-top: 8px;
            padding: 6px 8px;
            background: #E3F2FD;
            border-radius: 6px;
            font-size: 11px;
            display: flex;
            align-items: center;
            gap: 6px;
          }
          
          .edi-label {
            font-weight: 600;
            color: #2196F3;
          }
          
          .edi-values {
            color: #666;
            font-family: monospace;
            font-size: 10px;
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

  // Edit mode - show full inline editor
  return (
    <div 
      className="profile-node profile-node-editing"
      style={{ 
        borderColor: '#2196F3',
        backgroundColor: '#E3F2FD',
        minWidth: '320px',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: currentFormat.color }}
      />
      
      <div className="profile-edit-content">
        <div className="profile-edit-header">
          <span className="profile-edit-icon" style={{ color: currentFormat.color }}>
            {currentFormat.icon}
          </span>
          <span 
            className="profile-edit-badge"
            style={{ backgroundColor: currentFormat.color }}
          >
            {currentFormat.label}
          </span>
          <button 
            className="profile-edit-close"
            onClick={() => setEditMode(false)}
            title="Done editing"
          >
            ✓
          </button>
        </div>

        <div className="profile-edit-field">
          <label>Label</label>
          <input
            type="text"
            value={editData.label}
            onChange={(e) => handleLabelChange(e.target.value)}
            className="profile-edit-input"
            autoFocus
          />
        </div>

        <div className="profile-edit-field">
          <label>Format</label>
          <div className="format-grid">
            {formatOptions.map((fmt) => (
              <button
                key={fmt.value}
                className={`format-option ${editData.format === fmt.value ? 'selected' : ''}`}
                style={{ borderColor: fmt.color }}
                onClick={() => handleFormatChange(fmt.value)}
                title={fmt.label}
              >
                <span className="format-option-icon">{fmt.icon}</span>
                <span className="format-option-label">{fmt.label}</span>
              </button>
            ))}
          </div>
        </div>

        {(editData.format === 'edi' || Object.keys(ediTweaksObj).length > 0) && (
          <div className="profile-edit-section">
            <div className="profile-edit-section-title">EDI Settings</div>
            <div className="profile-edit-field">
              <label>Delimiter</label>
              <input
                type="text"
                value={ediTweaksObj.delimiter || '~'}
                onChange={(e) => handleEdiTweaksChange('delimiter', e.target.value)}
                className="profile-edit-input"
                placeholder="~"
              />
            </div>
            <div className="profile-edit-field">
              <label>Segment Terminator</label>
              <input
                type="text"
                value={ediTweaksObj['segment terminator'] || '*'}
                onChange={(e) => handleEdiTweaksChange('segment terminator', e.target.value)}
                className="profile-edit-input"
                placeholder="*"
              />
            </div>
            <div className="profile-edit-field">
              <label>Element Separator</label>
              <input
                type="text"
                value={ediTweaksObj['element separator'] || '^'}
                onChange={(e) => handleEdiTweaksChange('element separator', e.target.value)}
                className="profile-edit-input"
                placeholder="^"
              />
            </div>
          </div>
        )}

        <div className="profile-edit-section">
          <div className="profile-edit-section-title">Custom Settings</div>
          <div className="profile-edit-field">
            <label>Encoding</label>
            <select
              value={customSettingsObj.encoding || 'utf-8'}
              onChange={(e) => handleCustomSettingsChange('encoding', e.target.value)}
              className="profile-edit-select"
            >
              <option value="utf-8">UTF-8</option>
              <option value="ascii">ASCII</option>
              <option value="cp1252">Windows-1252</option>
            </select>
          </div>
          <div className="profile-edit-field">
            <label>Line Ending</label>
            <select
              value={customSettingsObj['line ending'] || 'lf'}
              onChange={(e) => handleCustomSettingsChange('line ending', e.target.value)}
              className="profile-edit-select"
            >
              <option value="lf">LF (Unix)</option>
              <option value="crlf">CRLF (Windows)</option>
              <option value="cr">CR (Old Mac)</option>
            </select>
          </div>
          <div className="profile-edit-field checkbox-field">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={customSettingsObj['include header'] !== false}
                onChange={(e) => handleCustomSettingsChange('include header', e.target.checked)}
              />
              <span>Include Header Row</span>
            </label>
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: currentFormat.color }}
      />
      
      <style>{`
        .profile-node-editing {
          border: 2px solid #2196F3 !important;
          border-radius: 12px;
          box-shadow: 0 8px 24px rgba(33, 150, 243, 0.3) !important;
        }
        
        .profile-edit-content {
          padding: 16px;
          max-height: 400px;
          overflow-y: auto;
        }
        
        .profile-edit-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
        }
        
        .profile-edit-icon {
          font-size: 28px;
        }
        
        .profile-edit-badge {
          padding: 4px 12px;
          border-radius: 16px;
          font-size: 11px;
          color: #fff;
          font-weight: 600;
          flex: 1;
        }
        
        .profile-edit-close {
          width: 28px;
          height: 28px;
          border-radius: 50%;
          border: none;
          background: #4CAF50;
          color: #fff;
          font-size: 14px;
          cursor: pointer;
        }
        
        .profile-edit-field {
          margin-bottom: 12px;
        }
        
        .profile-edit-field label {
          display: block;
          font-size: 11px;
          font-weight: 600;
          color: #666;
          margin-bottom: 4px;
          text-transform: uppercase;
        }
        
        .profile-edit-input {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 13px;
          background: #fff;
        }
        
        .profile-edit-input:focus {
          outline: none;
          border-color: #2196F3;
          box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.2);
        }
        
        .profile-edit-select {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 13px;
          background: #fff;
          cursor: pointer;
        }
        
        .format-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 6px;
        }
        
        .format-option {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 8px 4px;
          border: 2px solid #e0e0e0;
          border-radius: 8px;
          background: #fff;
          cursor: pointer;
          transition: all 0.2s;
        }
        
        .format-option:hover {
          border-color: #bbb;
          background: #f5f5f5;
        }
        
        .format-option.selected {
          border-width: 2px;
          background: #E3F2FD;
        }
        
        .format-option-icon {
          font-size: 20px;
        }
        
        .format-option-label {
          font-size: 9px;
          color: #666;
          margin-top: 2px;
          text-align: center;
        }
        
        .profile-edit-section {
          background: rgba(255, 255, 255, 0.7);
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 12px;
        }
        
        .profile-edit-section-title {
          font-size: 12px;
          font-weight: 600;
          color: #2196F3;
          margin-bottom: 10px;
          padding-bottom: 6px;
          border-bottom: 1px solid #e0e0e0;
        }
        
        .checkbox-field {
          margin-top: 8px;
        }
        
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          cursor: pointer;
        }
        
        .checkbox-label input[type="checkbox"] {
          width: 16px;
          height: 16px;
          cursor: pointer;
        }
      `}</style>
    </div>
  );
}

export default memo(ProfileNode);
