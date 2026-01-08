/** Pipeline Start Node
 * 
 * Dummy start node - entry point for the pipeline.
 * Provides a visual starting point and can pass through data.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineStartNode({ data, selected }) {
  return (
    <div 
      className={`pipeline-node start ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#4CAF50',
        backgroundColor: selected ? '#E8F5E9' : '#fff',
      }}
    >
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#4CAF50' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🚀</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Start'}</div>
          <div className="node-desc">
            Pipeline entry point
          </div>
        </div>
      </div>
      
      <style>{`
        .pipeline-node.start {
          min-width: 120px;
          border: 2px solid #4CAF50;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.start:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.start.selected {
          border-color: #2196F3;
          background-color: #E8F5E9;
        }
        
        .node-content {
          padding: 12px;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        
        .node-icon {
          font-size: 28px;
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
        
        .node-desc {
          font-size: 10px;
          color: #999;
          margin-top: 2px;
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

export default memo(PipelineStartNode);
