/** Pipeline Outlier Node
 * 
 * Detects and handles outliers (flag or remove).
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const outlierMethods = [
  { value: 'iqr', label: 'IQR (1.5×)' },
  { value: 'zscore', label: 'Z-Score (>3)' },
  { value: 'percentile', label: 'Percentile (1-99)' },
];

function PipelineOutlierNode({ data, selected, onUpdate }) {
  const method = data.method || 'iqr';
  const action = data.action || 'flag';
  
  return (
    <div 
      className={`pipeline-node outlier ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#f44336',
        backgroundColor: selected ? '#FFEBEE' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure outlier detection"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#f44336' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🚨</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Outlier'}</div>
          <div className="node-summary">
            <span className="out-tag">{method.toUpperCase()}</span>
            <span className="out-tag">{action}</span>
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#f44336' }}
      />
      
      <style>{`
        .pipeline-node.outlier {
          min-width: 140px;
          border: 2px solid #f44336;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; display: flex; gap: 4px; }
        .out-tag { padding: 2px 6px; background: #FFEBEE; border-radius: 4px; font-size: 10px; color: #D32F2F; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineOutlierNode);
