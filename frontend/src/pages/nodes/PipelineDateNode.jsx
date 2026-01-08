/** Pipeline Date Node
 * 
 * Date operations: parse, extract, diff.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const dateOperations = [
  { value: 'parse', label: 'Parse', icon: '📅' },
  { value: 'extract', label: 'Extract', icon: '📆' },
  { value: 'diff', label: 'Diff', icon: '⏱' },
];

function PipelineDateNode({ data, selected, onUpdate }) {
  const operation = data.operation || 'parse';
  const opInfo = dateOperations.find(o => o.value === operation) || dateOperations[0];
  
  return (
    <div 
      className={`pipeline-node date ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#9C27B0',
        backgroundColor: selected ? '#F3E5F5' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure date operation"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#9C27B0' }}
      />
      
      <div className="node-content">
        <div className="node-icon">{opInfo.icon}</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Date'}</div>
          <div className="node-operation">
            <span className="op-badge">{opInfo.label}</span>
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#9C27B0' }}
      />
      
      <style>{`
        .pipeline-node.date {
          min-width: 130px;
          border: 2px solid #9C27B0;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-operation { margin-top: 4px; }
        .op-badge { padding: 2px 8px; background: #F3E5F5; border-radius: 4px; font-size: 10px; color: #7B1FA2; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineDateNode);
