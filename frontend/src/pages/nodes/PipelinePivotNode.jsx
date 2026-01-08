/** Pipeline Pivot Node
 * 
 * Transforms rows into columns (group by + aggregate).
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelinePivotNode({ data, selected, onUpdate }) {
  const rowFields = JSON.parse(data.rowFields || '[]');
  const colField = data.colField || '';
  const valueField = data.valueField || '';
  const aggFunction = data.aggFunction || 'sum';
  
  return (
    <div 
      className={`pipeline-node pivot ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#FF9800',
        backgroundColor: selected ? '#FFF8E1' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure pivot"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#FF9800' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🔀</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Pivot'}</div>
          <div className="node-summary">
            {rowFields.length > 0 ? (
              <>
                <span className="pivot-tag">rows: {rowFields.join(', ')}</span>
                <span className="pivot-tag">col: {colField}</span>
                <span className="pivot-tag">agg: {aggFunction}</span>
              </>
            ) : (
              <span className="no-config">Not configured</span>
            )}
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#FF9800' }}
      />
      
      <style>{`
        .pipeline-node.pivot {
          min-width: 140px;
          border: 2px solid #FF9800;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap; }
        .pivot-tag { padding: 2px 6px; background: #FFF3E0; border-radius: 4px; font-size: 9px; color: #E65100; }
        .no-config { font-size: 10px; color: #999; font-style: italic; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelinePivotNode);
