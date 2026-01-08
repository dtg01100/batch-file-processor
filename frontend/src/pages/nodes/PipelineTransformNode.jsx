/** Pipeline Transform Node
 * 
 * Applies field-level transformations and calculations.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineTransformNode({ data, selected }) {
  const transforms = JSON.parse(data.transformations || '[]');
  
  return (
    <div 
      className={`pipeline-node transform ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#FF9800',
        backgroundColor: selected ? '#FFF8E1' : '#fff',
      }}
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#FF9800' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🔄</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Transform'}</div>
          <div className="node-summary">
            {transforms.length > 0 ? (
              <span>{transforms.length} transform{transforms.length > 1 ? 's' : ''}</span>
            ) : (
              <span className="no-transform">No transforms</span>
            )}
          </div>
          {transforms.length > 0 && (
            <div className="node-preview">
              {transforms.slice(0, 2).map((t, i) => (
                <span key={i} className="transform-tag">
                  {t.field} = {t.alias || t.expression?.substring(0, 15)}...
                </span>
              ))}
              {transforms.length > 2 && <span className="more">+{transforms.length - 2}</span>}
            </div>
          )}
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#FF9800' }}
      />
      
      <style>{`
        .pipeline-node {
          min-width: 160px;
          border: 2px solid #FF9800;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.selected {
          border-color: #F57C00;
          background-color: #FFF8E1;
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
        
        .no-transform {
          color: #f44336;
          font-style: italic;
        }
        
        .node-preview {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 6px;
        }
        
        .transform-tag {
          padding: 2px 6px;
          background: #FFF3E0;
          border-radius: 4px;
          font-size: 9px;
          color: #E65100;
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

export default memo(PipelineTransformNode);
