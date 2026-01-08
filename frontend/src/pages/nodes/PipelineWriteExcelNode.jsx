/** Pipeline Write Excel Node
 * 
 * Writes data to Excel files.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineWriteExcelNode({ data, selected, onUpdate }) {
  const sheetName = data.sheetName || 'Sheet1';
  
  return (
    <div 
      className={`pipeline-node write-excel ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#4CAF50',
        backgroundColor: selected ? '#E8F5E9' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure Excel writing"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#4CAF50' }}
      />
      
      <div className="node-content">
        <div className="node-icon">📗</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Write Excel'}</div>
          <div className="node-summary">
            <span className="excel-tag">{sheetName}</span>
          </div>
        </div>
      </div>
      
      <style>{`
        .pipeline-node.write-excel {
          min-width: 140px;
          border: 2px solid #4CAF50;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; }
        .excel-tag { padding: 2px 8px; background: #E8F5E9; border-radius: 4px; font-size: 10px; color: #388E3C; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineWriteExcelNode);
