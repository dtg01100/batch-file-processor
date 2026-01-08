/** Pipeline Aggregate Node
 * 
 * Groups and aggregates data.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineAggregateNode({ data, selected }) {
  const groupFields = JSON.parse(data.groupFields || '[]');
  const aggregations = JSON.parse(data.aggregations || '[]');
  
  return (
    <div 
      className={`pipeline-node aggregate ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#00BCD4',
        backgroundColor: selected ? '#E0F7FA' : '#fff',
      }}
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#00BCD4' }}
      />
      
      <div className="node-content">
        <div className="node-icon">📊</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Aggregate'}</div>
          <div className="node-summary">
            {groupFields.length > 0 || aggregations.length > 0 ? (
              <span>
                {groupFields.length > 0 && `${groupFields.length} group${groupFields.length > 1 ? 's' : ''}`}
                {groupFields.length > 0 && aggregations.length > 0 && ', '}
                {aggregations.length > 0 && `${aggregations.length} agg${aggregations.length > 1 ? 's' : ''}`}
              </span>
            ) : (
              <span className="no-agg">Not configured</span>
            )}
          </div>
          {groupFields.length > 0 && (
            <div className="node-preview">
              GROUP BY {groupFields.join(', ')}
            </div>
          )}
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#00BCD4' }}
      />
      
      <style>{`
        .pipeline-node {
          min-width: 160px;
          border: 2px solid #00BCD4;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.selected {
          border-color: #0097A7;
          background-color: #E0F7FA;
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
        
        .no-agg {
          color: #f44336;
          font-style: italic;
        }
        
        .node-preview {
          font-size: 10px;
          color: #0097A7;
          margin-top: 4px;
          font-family: monospace;
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

export default memo(PipelineAggregateNode);
