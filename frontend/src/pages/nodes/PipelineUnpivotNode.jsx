/** Pipeline Unpivot Node
 * 
 * Transforms columns into rows (wide to long format).
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineUnpivotNode({ data, selected, onUpdate }) {
  const keepFields = JSON.parse(data.keepFields || '[]');
  const valueColumn = data.valueColumn || 'value';
  const nameColumn = data.nameColumn || 'column';
  
  return (
    <div 
      className={`pipeline-node unpivot ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#00BCD4',
        backgroundColor: selected ? '#E0F7FA' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure unpivot"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#00BCD4' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🔄</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Unpivot'}</div>
          <div className="node-summary">
            {keepFields.length > 0 ? (
              <>
                <span className="unpivot-tag">keep: {keepFields.join(', ')}</span>
                <span className="unpivot-tag">→ {valueColumn}/{nameColumn}</span>
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
        style={{ backgroundColor: '#00BCD4' }}
      />
      
      <style>{`
        .pipeline-node.unpivot {
          min-width: 140px;
          border: 2px solid #00BCD4;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; display: flex; gap: 4px; flex-wrap: wrap; }
        .unpivot-tag { padding: 2px 6px; background: #E0F7FA; border-radius: 4px; font-size: 9px; color: #00838F; }
        .no-config { font-size: 10px; color: #999; font-style: italic; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineUnpivotNode);
