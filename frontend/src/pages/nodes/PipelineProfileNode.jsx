/** Pipeline Profile Node
 * 
 * Output profile formatting node.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineProfileNode({ data, selected }) {
  const formatColors = {
    csv: '#4CAF50',
    edi: '#2196F3',
    json: '#FF9800',
    xml: '#9C27B0',
  };
  
  const formatIcons = {
    csv: '📊',
    edi: '📋',
    json: '{ }',
    xml: '< >',
  };
  
  const color = formatColors[data.format] || '#FF5722';
  const icon = formatIcons[data.format] || '📋';
  
  const mappings = JSON.parse(data.fieldMapping || '[]');
  
  return (
    <div 
      className={`pipeline-node profile ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : color,
        backgroundColor: selected ? '#FFF3E0' : '#fff',
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
        <div className="node-icon" style={{ color }}>{icon}</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Profile'}</div>
          <div className="node-format">
            <span 
              className="format-badge"
              style={{ backgroundColor: color }}
            >
              {data.format?.toUpperCase() || 'CSV'}
            </span>
            {mappings.length > 0 && (
              <span className="mapping-count">{mappings.length} fields</span>
            )}
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
        .pipeline-node {
          min-width: 160px;
          border: 2px solid #FF5722;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.selected {
          border-color: #E64A19;
          background-color: #FFF3E0;
        }
        
        .node-content {
          padding: 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .node-icon {
          font-size: 24px;
          font-weight: bold;
        }
        
        .node-text {
          flex: 1;
          min-width: 0;
        }
        
        .node-label {
          font-weight: 600;
          font-size: 13px;
          color: #333;
        }
        
        .node-format {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 4px;
        }
        
        .format-badge {
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 10px;
          color: #fff;
          font-weight: 600;
        }
        
        .mapping-count {
          font-size: 10px;
          color: #666;
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

export default memo(PipelineProfileNode);
