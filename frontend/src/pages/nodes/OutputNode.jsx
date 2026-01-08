/** Output Folder Node
 * 
 * Custom React Flow node for representing output folders
 * with destination path and status indicators.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function OutputNode({ data, selected }) {
  const color = '#FF9800';
  
  return (
    <div 
      className={`output-node ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : color,
        backgroundColor: selected ? '#E3F2FD' : '#fff'
      }}
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: color }}
      />
      
      <div className="node-content">
        <div className="node-icon" style={{ color }}>
          {data.icon || '📤'}
        </div>
        
        <div className="node-text">
          <div className="node-label">{data.label || 'Output Folder'}</div>
          <div className="node-sublabel">
            {data.path || 'No path set'}
          </div>
        </div>
      </div>
      
      <style>{`
        .output-node {
          min-width: 160px;
          border: 2px solid #FF9800;
          border-radius: 8px;
          padding: 0;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s ease;
        }
        
        .output-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .output-node.selected {
          border-color: #2196F3;
          background-color: #E3F2FD;
        }
        
        .node-content {
          padding: 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .node-icon {
          font-size: 24px;
        }
        
        .node-text {
          flex: 1;
          min-width: 0;
        }
        
        .node-label {
          font-weight: 600;
          font-size: 14px;
          color: #333;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .node-sublabel {
          font-size: 11px;
          color: #666;
          margin-top: 2px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        
        .node-handle {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          border: 2px solid #fff;
        }
      `}</style>
    </div>
  );
}

export default memo(OutputNode);
