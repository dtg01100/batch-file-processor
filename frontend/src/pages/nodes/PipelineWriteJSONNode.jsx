/** Pipeline Write JSON Node
 * 
 * Writes data to JSON files.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineWriteJSONNode({ data, selected, onUpdate }) {
  const rootKey = data.rootKey || '';
  const pretty = data.pretty !== false;
  
  return (
    <div 
      className={`pipeline-node write-json ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#FFC107',
        backgroundColor: selected ? '#FFF8E1' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure JSON writing"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#FFC107' }}
      />
      
      <div className="node-content">
        <div className="node-icon">{ }</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Write JSON'}</div>
          <div className="node-summary">
            <span className="json-tag">{rootKey || 'root'}</span>
            <span className="json-tag">{pretty ? 'pretty' : 'compact'}</span>
          </div>
        </div>
      </div>
      
      <style>{`
        .pipeline-node.write-json {
          min-width: 140px;
          border: 2px solid #FFC107;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; font-weight: bold; color: #FFA000; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; display: flex; gap: 4px; }
        .json-tag { padding: 2px 6px; background: #FFF8E1; border-radius: 4px; font-size: 9px; color: #FFA000; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineWriteJSONNode);
