/** Pipeline End Node
 * 
 * Dummy end node - exit point for the pipeline.
 * Can receive from multiple upstream nodes.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineEndNode({ data, selected }) {
  return (
    <div 
      className={`pipeline-node end ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#f44336',
        backgroundColor: selected ? '#FFEBEE' : '#fff',
      }}
    >
      {/* Input handle (left side) - multiple connections allowed */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#f44336', top: '50%' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🏁</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'End'}</div>
          <div className="node-desc">
            Pipeline exit point
          </div>
        </div>
      </div>
      
      <style>{`
        .pipeline-node.end {
          min-width: 120px;
          border: 2px solid #f44336;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node.end:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.end.selected {
          border-color: #2196F3;
          background-color: #FFEBEE;
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

export default memo(PipelineEndNode);
