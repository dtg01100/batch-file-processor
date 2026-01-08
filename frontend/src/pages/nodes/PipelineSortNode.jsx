/** Pipeline Sort Node
 * 
 * Sorts data by one or more fields, ascending or descending.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineSortNode({ data, selected, onUpdate }) {
  const sortFields = JSON.parse(data.sortFields || '[]');
  
  return (
    <div 
      className={`pipeline-node sort ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#2196F3',
        backgroundColor: selected ? '#E3F2FD' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure sort"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#2196F3' }}
      />
      
      <div className="node-content">
        <div className="node-icon">📊</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Sort'}</div>
          <div className="node-summary">
            {sortFields.length > 0 ? (
              sortFields.map((s, i) => (
                <span key={i} className="sort-tag">
                  {s.field} {s.direction === 'desc' ? '↓' : '↑'}
                </span>
              ))
            ) : (
              <span className="no-config">No sort configured</span>
            )}
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#2196F3' }}
      />
      
      <style>{`
        .pipeline-node.sort {
          min-width: 140px;
          border: 2px solid #2196F3;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap; }
        .sort-tag { padding: 2px 6px; background: #E3F2FD; border-radius: 4px; font-size: 10px; color: #1976D2; }
        .no-config { font-size: 10px; color: #999; font-style: italic; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineSortNode);
