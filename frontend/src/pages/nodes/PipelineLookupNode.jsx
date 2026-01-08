/** Pipeline Lookup Node
 * 
 * Joins/lookups with reference data.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineLookupNode({ data, selected }) {
  return (
    <div 
      className={`pipeline-node lookup ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#E91E63',
        backgroundColor: selected ? '#FCE4EC' : '#fff',
      }}
    >
      {/* Primary input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#E91E63', top: '35%' }}
      />
      {/* Lookup input handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#E91E63', top: '65%' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🔗</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Lookup'}</div>
          <div className="node-summary">
            {data.lookupTable ? (
              <span className="has-lookup">{data.lookupTable}</span>
            ) : (
              <span className="no-lookup">No lookup table</span>
            )}
          </div>
          <div className="node-join">
            {data.joinType || 'LEFT'} JOIN on {data.sourceField} → {data.targetField}
          </div>
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#E91E63' }}
      />
      
      <style>{`
        .pipeline-node {
          min-width: 160px;
          border: 2px solid #E91E63;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.selected {
          border-color: #C2185B;
          background-color: #FCE4EC;
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
          margin-top: 2px;
        }
        
        .has-lookup {
          color: #E91E63;
          font-weight: 500;
        }
        
        .no-lookup {
          color: #f44336;
          font-style: italic;
        }
        
        .node-join {
          font-size: 10px;
          color: #999;
          margin-top: 4px;
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

export default memo(PipelineLookupNode);
