/** Pipeline Lookup Table Node
 * 
 * Enriches data with static reference data.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineLookupTableNode({ data, selected, onUpdate }) {
  const lookupTable = JSON.parse(data.lookupTable || '[]');
  const joinKey = data.joinKey || '';
  
  return (
    <div 
      className={`pipeline-node lookup-table ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#795548',
        backgroundColor: selected ? '#EFEBE9' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure lookup table"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#795548' }}
      />
      
      <div className="node-content">
        <div className="node-icon">📖</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Lookup Table'}</div>
          <div className="node-summary">
            {lookupTable.length > 0 ? (
              <span className="lookup-tag">{lookupTable.length} rows, key: {joinKey}</span>
            ) : (
              <span className="no-config">No table data</span>
            )}
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#795548' }}
      />
      
      <style>{`
        .pipeline-node.lookup-table {
          min-width: 150px;
          border: 2px solid #795548;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; }
        .lookup-tag { padding: 2px 8px; background: #EFEBE9; border-radius: 4px; font-size: 10px; color: #5D4037; }
        .no-config { font-size: 10px; color: #999; font-style: italic; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineLookupTableNode);
