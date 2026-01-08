/** Pipeline Normalize Node
 * 
 * Scales numerical values (min-max, z-score).
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const normalizeMethods = [
  { value: 'minmax', label: 'Min-Max (0-1)' },
  { value: 'zscore', label: 'Z-Score' },
  { value: 'robust', label: 'Robust (IQR)' },
];

function PipelineNormalizeNode({ data, selected, onUpdate }) {
  const method = data.method || 'minmax';
  const fields = JSON.parse(data.fields || '[]');
  
  return (
    <div 
      className={`pipeline-node normalize ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#8BC34A',
        backgroundColor: selected ? '#DCEDC8' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure normalization"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#8BC34A' }}
      />
      
      <div className="node-content">
        <div className="node-icon">📐</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Normalize'}</div>
          <div className="node-summary">
            <span className="norm-tag">{method === 'minmax' ? 'Min-Max' : method === 'zscore' ? 'Z-Score' : 'Robust'}</span>
            {fields.length > 0 && <span className="norm-tag">{fields.length} fields</span>}
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#8BC34A' }}
      />
      
      <style>{`
        .pipeline-node.normalize {
          min-width: 140px;
          border: 2px solid #8BC34A;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; display: flex; gap: 4px; }
        .norm-tag { padding: 2px 6px; background: #DCEDC8; border-radius: 4px; font-size: 10px; color: #558B2F; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineNormalizeNode);
