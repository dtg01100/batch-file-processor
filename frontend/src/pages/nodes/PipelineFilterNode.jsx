/** Pipeline Filter Node
 * 
 * Filters rows based on conditions.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineFilterNode({ data, selected }) {
  const conditions = JSON.parse(data.conditions || '[]');
  const logic = data.logic || 'AND';
  
  return (
    <div 
      className={`pipeline-node filter ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#9C27B0',
        backgroundColor: selected ? '#F3E5F5' : '#fff',
      }}
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#9C27B0' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🔍</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Filter'}</div>
          <div className="node-summary">
            {conditions.length > 0 ? (
              <span>{conditions.length} condition{conditions.length > 1 ? 's' : ''} ({logic})</span>
            ) : (
              <span className="no-filter">No conditions</span>
            )}
          </div>
          {conditions.length > 0 && (
            <div className="node-preview">
              {conditions.slice(0, 2).map((c, i) => (
                <span key={i} className="condition-tag">
                  {c.field} {c.operator}
                </span>
              ))}
              {conditions.length > 2 && <span className="more">+{conditions.length - 2}</span>}
            </div>
          )}
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#9C27B0' }}
      />
      
      <style>{`
        .pipeline-node {
          min-width: 160px;
          border: 2px solid #9C27B0;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.selected {
          border-color: #7B1FA2;
          background-color: #F3E5F5;
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
        
        .no-filter {
          color: #f44336;
          font-style: italic;
        }
        
        .node-preview {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 6px;
        }
        
        .condition-tag {
          padding: 2px 6px;
          background: #F3E5F5;
          border-radius: 4px;
          font-size: 9px;
          color: #7B1FA2;
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

export default memo(PipelineFilterNode);
