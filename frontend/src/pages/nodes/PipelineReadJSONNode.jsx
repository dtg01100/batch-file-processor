/** Pipeline Read JSON Node
 * 
 * Reads and parses JSON files.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineReadJSONNode({ data, selected, onUpdate }) {
  const arrayPath = data.arrayPath || '';
  
  return (
    <div 
      className={`pipeline-node read-json ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#FFC107',
        backgroundColor: selected ? '#FFF8E1' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure JSON reading"
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
          <div className="node-label">{data.label || 'Read JSON'}</div>
          <div className="node-summary">
            <span className="json-tag">{arrayPath || 'root array'}</span>
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#FFC107' }}
      />
      
      <style>{`
        .pipeline-node.read-json {
          min-width: 130px;
          border: 2px solid #FFC107;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; font-weight: bold; color: #FFA000; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; }
        .json-tag { padding: 2px 8px; background: #FFF8E1; border-radius: 4px; font-size: 10px; color: #FFA000; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineReadJSONNode);
