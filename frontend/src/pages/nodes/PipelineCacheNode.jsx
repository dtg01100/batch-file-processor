/** Pipeline Cache Node
 * 
 * Caches intermediate results for reuse.
 */

import React, { memo } from 'react';
import { Handle, Position } from 'reactflow';

function PipelineCacheNode({ data, selected, onUpdate }) {
  const ttl = data.ttl || 3600; // seconds
  
  return (
    <div 
      className={`pipeline-node cache ${selected ? 'selected' : ''}`}
      style={{ 
        borderColor: selected ? '#2196F3' : '#FF9800',
        backgroundColor: selected ? '#FFF8E1' : '#fff',
        cursor: 'pointer'
      }}
      onDoubleClick={() => onUpdate?.(data.id, { showEditor: true })}
      title="Double-click to configure caching"
    >
      <Handle
        type="target"
        position={Position.Left}
        className="node-handle"
        style={{ backgroundColor: '#FF9800' }}
      />
      
      <div className="node-content">
        <div className="node-icon">💾</div>
        <div className="node-text">
          <div className="node-label">{data.label || 'Cache'}</div>
          <div className="node-summary">
            <span className="cache-tag">TTL: {ttl}s</span>
          </div>
        </div>
      </div>
      
      <Handle
        type="source"
        position={Position.Right}
        className="node-handle"
        style={{ backgroundColor: '#FF9800' }}
      />
      
      <style>{`
        .pipeline-node.cache {
          min-width: 120px;
          border: 2px solid #FF9800;
          border-radius: 8px;
          background: #fff;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .node-content { padding: 12px; display: flex; align-items: center; gap: 10px; }
        .node-icon { font-size: 24px; }
        .node-label { font-weight: 600; font-size: 13px; }
        .node-summary { margin-top: 4px; }
        .cache-tag { padding: 2px 8px; background: #FFF3E0; border-radius: 4px; font-size: 10px; color: #E65100; }
        .node-handle { width: 10px; height: 10px; border-radius: 50%; border: 2px solid #fff; }
      `}</style>
    </div>
  );
}

export default memo(PipelineCacheNode);
