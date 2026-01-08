/** Pipeline Validate Node
 * 
 * Validates data quality.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineValidateNode({ data, selected }) {
  const rules = JSON.parse(data.rules || '[]');
  
  return (
    <div 
      className={`pipeline-node validate ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#8BC34A',
        backgroundColor: selected ? '#DCEDC8' : '#fff',
      }}
    >
      {/* Input handle (left side) */}
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#8BC34A' }}
      />
      
      <div className="node-content">
        <div className="node-icon">✅</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Validate'}</div>
          <div className="node-summary">
            {rules.length > 0 ? (
              <span>{rules.length} rule{rules.length > 1 ? 's' : ''}</span>
            ) : (
              <span className="no-rules">No rules</span>
            )}
          </div>
          {rules.length > 0 && (
            <div className="node-preview">
              {rules.slice(0, 2).map((r, i) => (
                <span key={i} className="rule-tag">
                  {r.field} {r.type}
                </span>
              ))}
              {rules.length > 2 && <span className="more">+{rules.length - 2}</span>}
            </div>
          )}
        </div>
      </div>
      
      {/* Output handle (right side) */}
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#8BC34A' }}
      />
      
      <style>{`
        .pipeline-node {
          min-width: 160px;
          border: 2px solid #8BC34A;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
          transition: all 0.2s;
        }
        
        .pipeline-node:hover {
          box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .pipeline-node.selected {
          border-color: #689F38;
          background-color: #DCEDC8;
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
        
        .no-rules {
          color: #f44336;
          font-style: italic;
        }
        
        .node-preview {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-top: 6px;
        }
        
        .rule-tag {
          padding: 2px 6px;
          background: #DCEDC8;
          border-radius: 4px;
          font-size: 9px;
          color: #689F38;
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

export default memo(PipelineValidateNode);
