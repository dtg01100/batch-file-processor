/** Pipeline Text Node
 * 
 * Text operations: replace, split, concatenate, extract.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const textOperations = [
  { value: 'replace', label: 'Replace', icon: '🔤' },
  { value: 'split', label: 'Split', icon: '✂️' },
  { value: 'concatenate', label: 'Concatenate', icon: '🔗' },
  { value: 'extract', label: 'Extract', icon: '🎯' },
];

function PipelineTextNode({ data, selected, onUpdate }) {
  const operation = data.operation || 'replace';
  const opInfo = textOperations.find(o => o.value === operation) || textOperations[0];
  
  return (
    <div 
      className={`pipeline-node text ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#607D8B',
        backgroundColor: selected ? '#ECEFF1' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure text operation"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#607D8B' }}
      />
      
      <div className="node-content">
        <div className="node-icon">{opInfo.icon}</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Text'}</div>
          <div className="node-operation">
            <span className="op-badge">{opInfo.label}</span>
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#607D8B' }}
      />
      
      <style>{`
        .pipeline-node.text {
          min-width: 130px;
          border: 2px solid #607D8B;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-operation { margin-top: 4px; }
        .op-badge { padding: 2px 8px; background: #ECEFF1; border-radius: 4px; font-size: 10px; color: #455A64; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineTextNode);
