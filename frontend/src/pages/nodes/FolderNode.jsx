/** Folder Input Node
 * 
 * Custom React Flow node for representing input folders
 * with connection type icons and status indicators.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

const connectionIcons = {
  local: '💻',
  smb: '🪟',
  sftp: '🔐',
  ftp: '🌐',
};

const connectionColors = {
  local: '#4CAF50',
  smb: '#2196F3',
  sftp: '#9C27B0',
  ftp: '#FF9800',
};

function FolderNode({ data, selected }) {
  const icon = connectionIcons[data.connectionType] || '📁';
  const color = connectionColors[data.connectionType] || '#666';
  
  return (
    <div 
      className={`folder-node ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : color,
        backgroundColor: selected ? '#E3F2FD' : '#fff'
      }}
    >
      {/* Input handle (right side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: color }}
      />
      
      <div className="node-content">
        <div className="node-icon" style={{ color }}>
          {icon}
        </div>
        
        <div className="node-text">
          <div className="node-label">{data.label || 'Input Folder'}</div>
          <div className="node-sublabel">
            {data.connectionType?.toUpperCase()}: {data.path || 'No path set'}
          </div>
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: color }}
      />
      
      <style>{`
        .folder-node {
          min-width: 180px;
          border: 2px solid #666;
          border-radius: 8px;
          padding: 0;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s ease;
        }
        
        .folder-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .folder-node.selected {
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

export default memo(FolderNode);
