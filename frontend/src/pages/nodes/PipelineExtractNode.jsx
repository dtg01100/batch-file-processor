/** Pipeline Extract Node
 * 
 * Extracts and maps fields from input data.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineExtractNode({ data, selected }) {
  const mappings = JSON.parse(data.fieldMappings || '[]');
  
  return (
    <div 
      className={`pipeline-node extract ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#2196F3',
        backgroundColor: selected ? '#E3F2FD' : '#fff',
      }}
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#2196F3' }}
      />
      
      <div className="node-content">
        <div className="node-icon">📋</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Extract'}</div>
          <div className="node-summary">
            {mappings.length > 0 ? (
              <span>{mappings.length} field{mappings.length > 1 ? 's' : ''} mapped</span>
            ) : (
              <span className="no-mapping">No mappings</span>
            )}
          </div>
          {mappings.length > 0 && (
            <div className="node-preview">
              {mappings.slice(0, 3).map((m, i) => (
                <span key={i} className="mapping-tag">
                  {m.source} → {m.target}
                </span>
              ))}
              {mappings.length > 3 && <span className="more">+{mappings.length - 3}</span>}
            </div>
          )}
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#2196F3' }}
      />
      
      <style>{`
        .pipeline-node {
          min-width: 160px;
          border: 2px solid #2196F3;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.selected {
          border-color: #1976D2;
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
          font-size: 13px;
          color: #333;
        }
        
        .node-summary {
          font-size: 11px;
          color: #666;
          margin-top: 2px;
        }
        
        .no-mapping {
          color: #f44336;
          font-style: italic;
        }
        
        .node-preview {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 6px;
        }
        
        .mapping-tag {
          padding: 2px 6px;
          background: #e3f2fd;
          border-radius: 4px;
          font-size: 9px;
          color: #1976D2;
        }
        
        .more {
          padding: 2px 6px;
          background: #f5f5f5;
          border-radius: 4px;
          font-size: 9px;
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

export default memo(PipelineExtractNode);
