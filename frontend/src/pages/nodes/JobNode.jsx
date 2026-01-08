/** Job Processing Node
 * 
 * Custom React Flow node for representing processing jobs
 * with enabled/disabled status and processing indicators.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function JobNode({ data, selected }) {
  const isEnabled = data.enabled !== false;
  const statusColor = isEnabled ? '#4CAF50' : '#9E9E9E';
  const statusIcon = isEnabled ? '✅' : '⏸️';
  
  return (
    <div 
      className={`job-node ${selected ? 'selected' : ''} ${!isEnabled ? 'disabled' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : statusColor,
        backgroundColor: selected ? '#E3F2FD' : '#fff'
      }}
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: statusColor }}
      />
      
      <div className="node-content">
        <div className="node-icon" style={{ color: statusColor }}>
          {data.icon || '⚙️'}
        </div>
        
        <div className="node-text">
          <div className="node-label">{data.label || 'Process Files'}</div>
          <div className="node-status">
            <span className="status-badge" style={{ backgroundColor: statusColor }}>
              {statusIcon} {isEnabled ? 'Enabled' : 'Disabled'}
            </span>
          </div>
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: statusColor }}
      />
      
      <style>{`
        .job-node {
          min-width: 160px;
          border: 2px solid #4CAF50;
          border-radius: 8px;
          padding: 0;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s ease;
        }
        
        .job-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .job-node.selected {
          border-color: #2196F3;
          background-color: #E3F2FD;
        }
        
        .job-node.disabled {
          border-color: #9E9E9E;
          opacity: 0.7;
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
        }
        
        .node-status {
          margin-top: 4px;
        }
        
        .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 11px;
          color: #fff;
          font-weight: 500;
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

export default memo(JobNode);
