/** Pipeline API Enrich Node
 * 
 * Enriches data by calling external APIs.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineAPIEnrichNode({ data, selected, onUpdate }) {
  const apiUrl = data.apiUrl || '';
  const method = data.method || 'GET';
  
  return (
    <div 
      className={`pipeline-node api-enrich ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#9C27B0',
        backgroundColor: selected ? '#F3E5F5' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure API enrichment"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#9C27B0' }}
      />
      
      <div className="node-content">
        <div className="node-icon">🌐</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'API Enrich'}</div>
          <div className="node-summary">
            {apiUrl ? (
              <span className="api-tag">{method} {apiUrl.substring(0, 30)}...</span>
            ) : (
              <span className="no-config">No API configured</span>
            )}
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#9C27B0' }}
      />
      
      <style>{`
        .pipeline-node.api-enrich {
          min-width: 150px;
          border: 2px solid #9C27B0;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; }
        .api-tag { padding: 2px 8px; background: #F3E5F5; border-radius: 4px; font-size: 10px; color: #7B1FA2; font-family: monospace; }
        .no-config { font-size: 10px; color: #999; font-style: italic; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineAPIEnrichNode);
