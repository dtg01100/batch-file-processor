/** Pipeline Graph Editor
 * 
 * Visual DAG editor for building acyclic data processing pipelines.
 * Each output profile has its own processing graph.
 */

import React, { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  applyNodeChanges,
  applyEdgeChanges,
} from 'reactflow';
import 'reactflow/dist/style.css';

// Import custom node components
import PipelineFolderNode from './nodes/PipelineFolderNode';
import PipelineExtractNode from './nodes/PipelineExtractNode';
import PipelineRemapperNode from './nodes/PipelineRemapperNode';
import PipelineTransformNode from './nodes/PipelineTransformNode';
import PipelineFilterNode from './nodes/PipelineFilterNode';
import PipelineRouterNode from './nodes/PipelineRouterNode';
import PipelineJoinNode from './nodes/PipelineJoinNode';
import PipelineAggregateNode from './nodes/PipelineAggregateNode';
import PipelineValidateNode from './nodes/PipelineValidateNode';
import PipelineQueryNode from './nodes/PipelineQueryNode';
import PipelineProfileNode from './nodes/PipelineProfileNode';
import PipelineOutputNode from './nodes/PipelineOutputNode';
import PipelineStartNode from './nodes/PipelineStartNode';
import PipelineEndNode from './nodes/PipelineEndNode';
import PipelineTriggerNode from './nodes/PipelineTriggerNode';
import PipelineSortNode from './nodes/PipelineSortNode';
import PipelineDedupeNode from './nodes/PipelineDedupeNode';
import PipelineUnionNode from './nodes/PipelineUnionNode';
import PipelinePivotNode from './nodes/PipelinePivotNode';
import PipelineUnpivotNode from './nodes/PipelineUnpivotNode';
import PipelineTextNode from './nodes/PipelineTextNode';
import PipelineDateNode from './nodes/PipelineDateNode';
import PipelineImputeNode from './nodes/PipelineImputeNode';
import PipelineNormalizeNode from './nodes/PipelineNormalizeNode';
import PipelineOutlierNode from './nodes/PipelineOutlierNode';
import PipelineLookupTableNode from './nodes/PipelineLookupTableNode';
import PipelineAPIEnrichNode from './nodes/PipelineAPIEnrichNode';
import PipelineDelayNode from './nodes/PipelineDelayNode';
import PipelineCacheNode from './nodes/PipelineCacheNode';
import PipelineReadJSONNode from './nodes/PipelineReadJSONNode';
import PipelineWriteJSONNode from './nodes/PipelineWriteJSONNode';
import PipelineReadExcelNode from './nodes/PipelineReadExcelNode';
import PipelineWriteExcelNode from './nodes/PipelineWriteExcelNode';

// Node type registry
const NODE_TYPES = {
  folderSource: PipelineFolderNode,
  extract: PipelineExtractNode,
  remapper: PipelineRemapperNode,
  transform: PipelineTransformNode,
  filter: PipelineFilterNode,
  router: PipelineRouterNode,
  join: PipelineJoinNode,
  aggregate: PipelineAggregateNode,
  validate: PipelineValidateNode,
  query: PipelineQueryNode,
  profile: PipelineProfileNode,
  output: PipelineOutputNode,
  start: PipelineStartNode,
  end: PipelineEndNode,
  trigger: PipelineTriggerNode,
  sort: PipelineSortNode,
  dedupe: PipelineDedupeNode,
  union: PipelineUnionNode,
  pivot: PipelinePivotNode,
  unpivot: PipelineUnpivotNode,
  text: PipelineTextNode,
  date: PipelineDateNode,
  impute: PipelineImputeNode,
  normalize: PipelineNormalizeNode,
  outlier: PipelineOutlierNode,
  lookupTable: PipelineLookupTableNode,
  apiEnrich: PipelineAPIEnrichNode,
  delay: PipelineDelayNode,
  cache: PipelineCacheNode,
  readJson: PipelineReadJSONNode,
  writeJson: PipelineWriteJSONNode,
  readExcel: PipelineReadExcelNode,
  writeExcel: PipelineWriteExcelNode,
};

// Node categories for sidebar
const NODE_CATEGORIES = {
  '🚀 Control': [
    { type: 'start', label: 'Start', icon: '🚀', color: '#4CAF50' },
    { type: 'end', label: 'End', icon: '🏁', color: '#f44336' },
    { type: 'trigger', label: 'Trigger', icon: '⚡', color: '#E91E63' },
  ],
  '📥 Sources': [
    { type: 'folderSource', label: 'Input Source', icon: '📥', color: '#4CAF50' },
    { type: 'query', label: 'Query (Source)', icon: '📤', color: '#FF9800' },
    { type: 'readJson', label: 'Read JSON', icon: '{ }', color: '#FFC107' },
    { type: 'readExcel', label: 'Read Excel', icon: '📗', color: '#4CAF50' },
  ],
  '🔄 Transforms': [
    { type: 'extract', label: 'Select Fields', icon: '📋', color: '#2196F3' },
    { type: 'remapper', label: 'Remapper', icon: '🔄', color: '#00BCD4' },
    { type: 'transform', label: 'Calculate', icon: '⚡', color: '#FF9800' },
    { type: 'sort', label: 'Sort', icon: '📊', color: '#2196F3' },
    { type: 'dedupe', label: 'Dedupe', icon: '🔁', color: '#9C27B0' },
    { type: 'filter', label: 'Filter Rows', icon: '🔍', color: '#9C27B0' },
    { type: 'router', label: 'Router', icon: '🔀', color: '#FF5722' },
    { type: 'join', label: 'Join', icon: '🔗', color: '#4CAF50' },
    { type: 'union', label: 'Union', icon: '➕', color: '#4CAF50' },
    { type: 'aggregate', label: 'Aggregate', icon: '📊', color: '#00BCD4' },
    { type: 'pivot', label: 'Pivot', icon: '🔀', color: '#FF9800' },
    { type: 'unpivot', label: 'Unpivot', icon: '🔄', color: '#00BCD4' },
  ],
  '📝 Text': [
    { type: 'text', label: 'Text Ops', icon: '🔤', color: '#607D8B' },
  ],
  '📅 Date': [
    { type: 'date', label: 'Date Ops', icon: '📅', color: '#9C27B0' },
  ],
  '✓ Quality': [
    { type: 'validate', label: 'Validate', icon: '✅', color: '#8BC34A' },
    { type: 'impute', label: 'Impute', icon: '🧩', color: '#00BCD4' },
    { type: 'normalize', label: 'Normalize', icon: '📐', color: '#8BC34A' },
    { type: 'outlier', label: 'Outlier', icon: '🚨', color: '#f44336' },
  ],
  '🔗 Enrich': [
    { type: 'lookupTable', label: 'Lookup Table', icon: '📖', color: '#795548' },
    { type: 'apiEnrich', label: 'API Enrich', icon: '🌐', color: '#9C27B0' },
  ],
  '⏱ Flow': [
    { type: 'delay', label: 'Delay', icon: '⏳', color: '#607D8B' },
    { type: 'cache', label: 'Cache', icon: '💾', color: '#FF9800' },
  ],
  '📝 Scripts': [
    { type: 'query', label: 'Query (Transform)', icon: '📝', color: '#FFC107' },
  ],
  '📤 Output': [
    { type: 'query', label: 'Query (Sink)', icon: '📥', color: '#f44336' },
    { type: 'profile', label: 'Profile', icon: '📋', color: '#FF5722' },
    { type: 'output', label: 'Output Destination', icon: '📤', color: '#795548' },
    { type: 'writeJson', label: 'Write JSON', icon: '{ }', color: '#FFC107' },
    { type: 'writeExcel', label: 'Write Excel', icon: '📗', color: '#4CAF50' },
  ],
};

function PipelineGraph({ pipelineId, onSave }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [nodeChanges, setNodeChanges] = useState([]);
  const [edgeChanges, setEdgeChanges] = useState([]);
  
  // Create a new node with defaults
  const createNode = useCallback((type, position) => {
    const id = `${type}_${Date.now()}`;
    const nodeConfigs = {
      folderSource: {
        label: 'Input Source',
        protocol: 'local',
        config: '{}',
        filePattern: '*.csv',
      },
      extract: {
        label: 'Extract',
        sourceFields: [],
        fieldMappings: '[]',
      },
      remapper: {
        label: 'Remapper',
        mappings: '[]',
        dropOthers: true,
        icon: '🔄',
      },
      transform: {
        label: 'Transform',
        transformations: '[]',
        expressions: '[]',
      },
      filter: {
        label: 'Filter',
        conditions: '[]',
        logic: 'AND',
      },
      router: {
        label: 'Router',
        conditions: '[]',
        logic: 'AND',
        icon: '🔀',
      },
      join: {
        label: 'Join',
        joinType: 'left',
        joinKeys: '[]',
        outputFields: '[]',
        prefixTables: true,
        icon: '🔗',
      },
      aggregate: {
        label: 'Aggregate',
        groupFields: '[]',
        aggregations: '[]',
      },
      validate: {
        label: 'Validate',
        rules: '[]',
        errorHandling: 'skip',
      },
      query: {
        label: 'Query',
        queryType: 'sql',
        mode: 'transform',
        query: '',
        inputs: '[]',
        outputs: '[]',
      },
      start: {
        label: 'Start',
      },
      end: {
        label: 'End',
      },
      trigger: {
        label: 'Trigger',
        triggerType: 'manual',
        config: '{}',
      },
      sort: {
        label: 'Sort',
        sortFields: '[]',
      },
      dedupe: {
        label: 'Dedupe',
        dedupeFields: '[]',
        keep: 'first',
      },
      union: {
        label: 'Union',
        sources: '[]',
      },
      pivot: {
        label: 'Pivot',
        rowFields: '[]',
        colField: '',
        valueField: '',
        aggFunction: 'sum',
      },
      unpivot: {
        label: 'Unpivot',
        keepFields: '[]',
        valueColumn: 'value',
        nameColumn: 'column',
      },
      text: {
        label: 'Text',
        operation: 'replace',
      },
      date: {
        label: 'Date',
        operation: 'parse',
      },
      impute: {
        label: 'Impute',
        imputeFields: '[]',
        method: 'fixed',
        value: '',
      },
      normalize: {
        label: 'Normalize',
        fields: '[]',
        method: 'minmax',
      },
      outlier: {
        label: 'Outlier',
        fields: '[]',
        method: 'iqr',
        action: 'flag',
      },
      lookupTable: {
        label: 'Lookup Table',
        lookupTable: '[]',
        joinKey: '',
      },
      apiEnrich: {
        label: 'API Enrich',
        apiUrl: '',
        method: 'GET',
      },
      delay: {
        label: 'Delay',
        duration: 5,
        unit: 'seconds',
      },
      cache: {
        label: 'Cache',
        ttl: 3600,
      },
      readJson: {
        label: 'Read JSON',
        arrayPath: '',
      },
      writeJson: {
        label: 'Write JSON',
        rootKey: '',
        pretty: true,
      },
      readExcel: {
        label: 'Read Excel',
        sheetName: 'Sheet1',
        hasHeader: true,
      },
      writeExcel: {
        label: 'Write Excel',
        sheetName: 'Sheet1',
      },
      profile: {
        label: 'Output Profile',
        format: 'csv',
        fieldMapping: '[]',
        outputOptions: '{}',
      },
      output: {
        label: 'Output Destination',
        protocol: 'local',
        config: '{}',
      },
    };
    
    const nodeConfig = nodeConfigs[type] || {};
    
    const newNode = {
      id,
      type,
      position,
      data: {
        ...nodeConfig,
        id,
      },
    };
    
    return newNode;
  }, []);
  
  // Add node to graph
  const addNode = useCallback((type, position) => {
    const newNode = createNode(type, position);
    setNodes((nds) => nds.concat(newNode));
    setSelectedNode(newNode);
  }, [createNode, setNodes]);
  
  // Handle connect
  const onConnect = useCallback((params) => {
    const newEdge = {
      ...params,
      type: 'smoothstep',
      animated: true,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: '#666',
      },
      style: {
        stroke: '#666',
        strokeWidth: 2,
      },
    };
    setEdges((eds) => addEdge(newEdge, eds));
  }, [setEdges]);
  
  // Update node data
  const updateNodeData = useCallback((nodeId, newData) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, ...newData } }
          : node
      )
    );
  }, [setNodes]);
  
  // Delete selected node
  const deleteSelectedNode = useCallback(() => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((n) => n.id !== selectedNode.id));
      setEdges((eds) =>
        eds.filter(
          (e) => e.source !== selectedNode.id && e.target !== selectedNode.id
        )
      );
      setSelectedNode(null);
    }
  }, [selectedNode, setNodes, setEdges]);
  
  // Handle node click
  const onNodeClick = useCallback((event, node) => {
    setSelectedNode(node);
  }, []);
  
  // Handle background click
  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
  }, []);
  
  // Save pipeline
  const savePipeline = useCallback(() => {
    const pipelineData = {
      id: pipelineId || `pipeline_${Date.now()}`,
      nodes: nodes.map(({ id, type, position, data }) => ({
        id,
        type,
        position,
        data,
      })),
      edges: edges.map(({ id, source, target, type, label }) => ({
        id,
        source,
        target,
        type,
        label,
      })),
      savedAt: new Date().toISOString(),
    };
    
    onSave?.(pipelineData);
    alert('Pipeline saved successfully!');
  }, [nodes, edges, pipelineId, onSave]);
  
  // Load pipeline
  const loadPipeline = useCallback((data) => {
    if (data?.nodes) {
      setNodes(data.nodes.map((n) => ({ ...n, selected: false })));
    }
    if (data?.edges) {
      setEdges(
        data.edges.map((e) => ({
          ...e,
          type: 'smoothstep',
          animated: true,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#666',
          },
          style: {
            stroke: '#666',
            strokeWidth: 2,
          },
        }))
      );
    }
  }, [setNodes, setEdges]);
  
  // Check for cycles (basic DFS)
  const hasCycle = useCallback(() => {
    const graph = {};
    nodes.forEach((node) => {
      graph[node.id] = [];
    });
    edges.forEach((edge) => {
      if (graph[edge.source]) {
        graph[edge.source].push(edge.target);
      }
    });
    
    const visited = new Set();
    const recursionStack = new Set();
    
    const dfs = (nodeId) => {
      visited.add(nodeId);
      recursionStack.add(nodeId);
      
      const neighbors = graph[nodeId] || [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (dfs(neighbor)) return true;
        } else if (recursionStack.has(neighbor)) {
          return true;
        }
      }
      
      recursionStack.delete(nodeId);
      return false;
    };
    
    for (const node of nodes) {
      if (!visited.has(node.id)) {
        if (dfs(node.id)) return true;
      }
    }
    
    return false;
  }, [nodes, edges]);
  
  // Get node by ID
  const getNode = useCallback((id) => {
    return nodes.find((n) => n.id === id);
  }, [nodes]);
  
  // Get connected nodes
  const getConnectedNodes = useCallback((nodeId, direction = 'both') => {
    const result = { upstream: [], downstream: [] };
    
    edges.forEach((edge) => {
      if (direction === 'upstream' || direction === 'both') {
        if (edge.target === nodeId) {
          const sourceNode = getNode(edge.source);
          if (sourceNode) result.upstream.push(sourceNode);
        }
      }
      if (direction === 'downstream' || direction === 'both') {
        if (edge.source === nodeId) {
          const targetNode = getNode(edge.target);
          if (targetNode) result.downstream.push(targetNode);
        }
      }
    });
    
    return result;
  }, [edges, getNode]);
  
  return (
    <div className="pipeline-graph-container">
      {/* Top toolbar */}
      <div className="pipeline-toolbar">
        <div className="pipeline-title">
          <span className="pipeline-icon">⚡</span>
          <span>Pipeline Editor</span>
          {pipelineId && <span className="pipeline-id">#{pipelineId}</span>}
        </div>
        
        <div className="pipeline-actions">
          <button className="pipeline-btn" onClick={() => setNodes([])}>
            🗑️ Clear
          </button>
          <button className="pipeline-btn" onClick={() => loadPipeline({ nodes: [], edges: [] })}>
            📄 New
          </button>
          <button className="pipeline-btn primary" onClick={savePipeline}>
            💾 Save Pipeline
          </button>
        </div>
      </div>
      
      <div className="pipeline-main">
        {/* Sidebar - Node palette */}
        <div className="pipeline-sidebar">
          <div className="sidebar-title">Node Palette</div>
          
          {Object.entries(NODE_CATEGORIES).map(([category, items]) => (
            <div key={category} className="node-category">
              <div className="category-title">{category}</div>
              <div className="category-items">
                {items.map((item) => (
                  <button
                    key={item.type}
                    className="palette-item"
                    onClick={() => {
                      const { x, y } = flowToScreenPosition(
                        nodes.length * 100 + 100,
                        nodes.length * 50 + 100
                      );
                      addNode(item.type, { x: 300, y: 100 + nodes.length * 50 });
                    }}
                    style={{ borderLeftColor: item.color }}
                  >
                    <span className="palette-icon">{item.icon}</span>
                    <span className="palette-label">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
          
          <div className="sidebar-help">
            <p>💡 <strong>Tips:</strong></p>
            <ul>
              <li>Drag from handles to connect nodes</li>
              <li>Double-click to edit node</li>
              <li>Data flows left → right</li>
              <li>No cycles allowed</li>
            </ul>
          </div>
        </div>
        
        {/* Main canvas */}
        <div className="pipeline-canvas" ref={(el) => el && (window.flowToScreenPosition = (x, y) => {
          const rect = el.getBoundingClientRect();
          return { x: rect.left + x, y: rect.top + y };
        })}>
          <ReactFlow
            nodes={nodes.map((n) => ({ ...n, selected: n.id === selectedNode?.id }))}
            edges={edges}
            onNodesChange={(changes) => {
              onNodesChange(changes);
              setNodeChanges(changes);
            }}
            onEdgesChange={(changes) => {
              onEdgesChange(changes);
              setEdgeChanges(changes);
            }}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
            onPaneClick={onPaneClick}
            nodeTypes={NODE_TYPES}
            fitView
            attributionPosition="bottom-left"
          >
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                const colors = {
                  folderSource: '#4CAF50',
                  extract: '#2196F3',
                  remapper: '#00BCD4',
                  transform: '#FF9800',
                  filter: '#9C27B0',
                  router: '#FF5722',
                  join: '#4CAF50',
                  aggregate: '#00BCD4',
                  validate: '#8BC34A',
                  query: '#FFC107',
                  profile: '#FF5722',
                  output: '#795548',
                  start: '#4CAF50',
                  end: '#f44336',
                  trigger: '#E91E63',
                  sort: '#2196F3',
                  dedupe: '#9C27B0',
                  union: '#4CAF50',
                  pivot: '#FF9800',
                  unpivot: '#00BCD4',
                  text: '#607D8B',
                  date: '#9C27B0',
                  impute: '#00BCD4',
                  normalize: '#8BC34A',
                  outlier: '#f44336',
                  lookupTable: '#795548',
                  apiEnrich: '#9C27B0',
                  delay: '#607D8B',
                  cache: '#FF9800',
                  readJson: '#FFC107',
                  writeJson: '#FFC107',
                  readExcel: '#4CAF50',
                  writeExcel: '#4CAF50',
                };
                return colors[node.type] || '#666';
              }}
            />
            <Background color="#e0e0e0" gap={20} />
          </ReactFlow>
          
          {/* Graph stats */}
          <div className="graph-stats">
            <span>📊 {nodes.length} nodes</span>
            <span>🔗 {edges.length} connections</span>
            <span className={hasCycle() ? 'error' : 'ok'}>
              {hasCycle() ? '⚠️ Cycle detected!' : '✅ Valid DAG'}
            </span>
          </div>
        </div>
        
        {/* Right panel - Node properties */}
        {selectedNode && (
          <div className="pipeline-properties">
            <div className="properties-header">
              <span className="properties-title">Node Properties</span>
            <button 
              className="node-palette-item"
              onClick={() => addNode('extract', { x: 700, y: 200 })}
            >
              <span className="node-icon">📋</span>
              <span>Select Fields</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('remapper', { x: 700, y: 200 })}
            >
              <span className="node-icon">🔄</span>
              <span>Remapper</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('transform', { x: 700, y: 200 })}
            >
              <span className="node-icon">⚡</span>
              <span>Calculate</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('remapper', { x: 700, y: 200 })}
            >
              <span className="node-icon">🔄</span>
              <span>Remapper</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('transform', { x: 700, y: 200 })}
            >
              <span className="node-icon">⚡</span>
              <span>Transform</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('router', { x: 700, y: 200 })}
            >
              <span className="node-icon">🔀</span>
              <span>Router</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('join', { x: 700, y: 200 })}
            >
              <span className="node-icon">🔗</span>
              <span>Join</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('aggregate', { x: 700, y: 200 })}
            >
              <span className="node-icon">📊</span>
              <span>Aggregate</span>
            </button>
            
            <button 
              className="node-palette-item"
              onClick={() => addNode('lookup', { x: 700, y: 200 })}
            >
              <span className="node-icon">🔗</span>
              <span>Lookup/Join</span>
            </button>
            </div>
            
            <div className="properties-content">
              <div className="property-group">
                <label>Node Type</label>
                <div className="node-type-badge">{selectedNode.type}</div>
              </div>
              
              <PropertyField
                label="Label"
                value={selectedNode.data.label || ''}
                onChange={(v) => updateNodeData(selectedNode.id, { label: v })}
              />
              
              {/* Type-specific properties */}
              {selectedNode.type === 'folderSource' && (
                <>
                  <PropertyField
                    label="Folder Path"
                    value={selectedNode.data.folderPath || ''}
                    onChange={(v) => updateNodeData(selectedNode.id, { folderPath: v })}
                    placeholder="/path/to/input/folder"
                  />
                  <PropertyField
                    label="File Pattern"
                    value={selectedNode.data.filePattern || '*.csv'}
                    onChange={(v) => updateNodeData(selectedNode.id, { filePattern: v })}
                    placeholder="*.csv, *.txt, *.*"
                  />
                </>
              )}
              
              {selectedNode.type === 'extract' && (
                <FieldMappingEditor
                  value={selectedNode.data.fieldMappings || '[]'}
                  onChange={(v) => updateNodeData(selectedNode.id, { fieldMappings: v })}
                />
              )}
              
              {selectedNode.type === 'remapper' && (
                <RemapperEditor
                  value={selectedNode.data.mappings || '[]'}
                  dropOthers={selectedNode.data.dropOthers !== false}
                  onChange={(v) => updateNodeData(selectedNode.id, { mappings: v })}
                  onDropChange={(d) => updateNodeData(selectedNode.id, { dropOthers: d })}
                />
              )}
              
              {selectedNode.type === 'transform' && (
                <TransformEditor
                  value={selectedNode.data.transformations || '[]'}
                  onChange={(v) => updateNodeData(selectedNode.id, { transformations: v })}
                />
              )}
              
              {selectedNode.type === 'filter' && (
                <FilterEditor
                  value={selectedNode.data.conditions || '[]'}
                  logic={selectedNode.data.logic || 'AND'}
                  onChange={(v) => updateNodeData(selectedNode.id, { conditions: v })}
                  onLogicChange={(l) => updateNodeData(selectedNode.id, { logic: l })}
                />
              )}
              
              {selectedNode.type === 'router' && (
                <RouterEditor
                  value={selectedNode.data.conditions || '[]'}
                  logic={selectedNode.data.logic || 'AND'}
                  onChange={(v) => updateNodeData(selectedNode.id, { conditions: v })}
                  onLogicChange={(l) => updateNodeData(selectedNode.id, { logic: l })}
                />
              )}
              
              {selectedNode.type === 'join' && (
                <JoinEditor
                  value={selectedNode.data.joinKeys || '[]'}
                  joinType={selectedNode.data.joinType || 'left'}
                  outputFields={selectedNode.data.outputFields || '[]'}
                  prefixTables={selectedNode.data.prefixTables !== false}
                  onChange={(v) => updateNodeData(selectedNode.id, { joinKeys: v })}
                  onJoinTypeChange={(jt) => updateNodeData(selectedNode.id, { joinType: jt })}
                  onOutputFieldsChange={(of) => updateNodeData(selectedNode.id, { outputFields: of })}
                  onPrefixChange={(p) => updateNodeData(selectedNode.id, { prefixTables: p })}
                />
              )}
              
              {selectedNode.type === 'aggregate' && (
                <AggregateEditor
                  value={selectedNode.data}
                  onChange={(v) => updateNodeData(selectedNode.id, v)}
                />
              )}
              
              {selectedNode.type === 'validate' && (
                <ValidateEditor
                  value={selectedNode.data.rules || '[]'}
                  onChange={(v) => updateNodeData(selectedNode.id, { rules: v })}
                />
              )}
              
              {selectedNode.type === 'profile' && (
                <>
                  <SelectField
                    label="Output Format"
                    value={selectedNode.data.format || 'csv'}
                    options={[
                      { value: 'csv', label: 'CSV' },
                      { value: 'edi', label: 'EDI' },
                      { value: 'json', label: 'JSON' },
                      { value: 'xml', label: 'XML' },
                    ]}
                    onChange={(v) => updateNodeData(selectedNode.id, { format: v })}
                  />
                  <FieldMappingEditor
                    label="Output Field Mapping"
                    value={selectedNode.data.fieldMapping || '[]'}
                    onChange={(v) => updateNodeData(selectedNode.id, { fieldMapping: v })}
                  />
                </>
              )}
              
              {selectedNode.type === 'output' && (
                <>
                  <div className="property-group">
                    <label>Output Destination (double-click node to edit)</label>
                    <div style={{ 
                      padding: '12px', 
                      background: '#EFEBE9', 
                      borderRadius: '6px',
                      fontSize: '12px',
                      color: '#795548'
                    }}>
                      Protocol: {selectedNode.data.protocol || 'local'}
                    </div>
                  </div>
                </>
              )}
              
              {/* Upstream/Downstream info */}
              <ConnectedNodesInfo
                node={selectedNode}
                getConnectedNodes={getConnectedNodes}
              />
            </div>
            
            <div className="properties-footer">
              <button className="delete-btn" onClick={deleteSelectedNode}>
                🗑️ Delete Node
              </button>
            </div>
          </div>
        )}
      </div>
      
      <style>{`
        .pipeline-graph-container {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: #f5f5f5;
        }
        
        .pipeline-toolbar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 20px;
          background: #fff;
          border-bottom: 1px solid #e0e0e0;
          box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        
        .pipeline-title {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 18px;
          font-weight: 600;
          color: #333;
        }
        
        .pipeline-icon {
          font-size: 24px;
        }
        
        .pipeline-id {
          padding: 2px 8px;
          background: #e3f2fd;
          border-radius: 10px;
          font-size: 12px;
          color: #1976d2;
        }
        
        .pipeline-actions {
          display: flex;
          gap: 10px;
        }
        
        .pipeline-btn {
          padding: 8px 16px;
          border: 1px solid #ddd;
          border-radius: 6px;
          background: #fff;
          cursor: pointer;
          font-size: 13px;
          transition: all 0.2s;
        }
        
        .pipeline-btn:hover {
          border-color: #999;
          background: #f5f5f5;
        }
        
        .pipeline-btn.primary {
          background: #2196F3;
          border-color: #2196F3;
          color: #fff;
        }
        
        .pipeline-btn.primary:hover {
          background: #1976D2;
        }
        
        .pipeline-main {
          display: flex;
          flex: 1;
          overflow: hidden;
        }
        
        .pipeline-sidebar {
          width: 220px;
          background: #fff;
          border-right: 1px solid #e0e0e0;
          overflow-y: auto;
          padding: 16px;
        }
        
        .sidebar-title {
          font-size: 14px;
          font-weight: 600;
          color: #333;
          margin-bottom: 16px;
          padding-bottom: 8px;
          border-bottom: 2px solid #2196F3;
        }
        
        .node-category {
          margin-bottom: 20px;
        }
        
        .category-title {
          font-size: 12px;
          font-weight: 600;
          color: #666;
          text-transform: uppercase;
          margin-bottom: 8px;
        }
        
        .category-items {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .palette-item {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 12px;
          border: none;
          border-left: 3px solid #ddd;
          border-radius: 0 6px 6px 0;
          background: #fafafa;
          cursor: pointer;
          text-align: left;
          transition: all 0.2s;
        }
        
        .palette-item:hover {
          background: #e3f2fd;
          border-left-color: #2196F3;
        }
        
        .palette-icon {
          font-size: 18px;
        }
        
        .palette-label {
          font-size: 13px;
          color: #333;
        }
        
        .sidebar-help {
          margin-top: 20px;
          padding: 12px;
          background: #fff8e1;
          border-radius: 8px;
          font-size: 12px;
        }
        
        .sidebar-help p {
          margin: 0 0 8px 0;
          color: #f57c00;
        }
        
        .sidebar-help ul {
          margin: 0;
          padding-left: 16px;
          color: #666;
        }
        
        .sidebar-help li {
          margin-bottom: 4px;
        }
        
        .pipeline-canvas {
          flex: 1;
          position: relative;
        }
        
        .graph-stats {
          position: absolute;
          bottom: 20px;
          right: 20px;
          display: flex;
          gap: 16px;
          padding: 10px 16px;
          background: rgba(255,255,255,0.95);
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
          font-size: 12px;
          color: #666;
        }
        
        .graph-stats .ok {
          color: #4CAF50;
          font-weight: 600;
        }
        
        .graph-stats .error {
          color: #f44336;
          font-weight: 600;
        }
        
        .pipeline-properties {
          width: 320px;
          background: #fff;
          border-left: 1px solid #e0e0e0;
          display: flex;
          flex-direction: column;
        }
        
        .properties-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          border-bottom: 1px solid #e0e0e0;
        }
        
        .properties-title {
          font-size: 14px;
          font-weight: 600;
          color: #333;
        }
        
        .properties-close {
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 50%;
          background: #f5f5f5;
          cursor: pointer;
          font-size: 18px;
          color: #666;
        }
        
        .properties-content {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
        }
        
        .property-group {
          margin-bottom: 16px;
        }
        
        .property-group label {
          display: block;
          font-size: 11px;
          font-weight: 600;
          color: #666;
          text-transform: uppercase;
          margin-bottom: 6px;
        }
        
        .node-type-badge {
          padding: 6px 12px;
          background: #e3f2fd;
          border-radius: 6px;
          font-size: 12px;
          color: #1976d2;
          font-family: monospace;
        }
        
        .properties-footer {
          padding: 16px;
          border-top: 1px solid #e0e0e0;
        }
        
        .delete-btn {
          width: 100%;
          padding: 10px;
          border: 1px solid #f44336;
          border-radius: 6px;
          background: #fff;
          color: #f44336;
          cursor: pointer;
          font-size: 13px;
        }
        
        .delete-btn:hover {
          background: #ffebee;
        }
      `}</style>
    </div>
  );
}

// Property field component
function PropertyField({ label, value, onChange, placeholder, type = 'text' }) {
  return (
    <div className="property-group">
      <label>{label}</label>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="property-input"
        style={{
          width: '100%',
          padding: '8px 12px',
          border: '1px solid #ddd',
          borderRadius: '6px',
          fontSize: '13px',
        }}
      />
    </div>
  );
}

// Select field component
function SelectField({ label, value, options, onChange }) {
  return (
    <div className="property-group">
      <label>{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="property-select"
        style={{
          width: '100%',
          padding: '8px 12px',
          border: '1px solid #ddd',
          borderRadius: '6px',
          fontSize: '13px',
          background: '#fff',
        }}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}

// Field mapping editor
function FieldMappingEditor({ label = 'Field Mappings', value, onChange }) {
  const mappings = JSON.parse(value || '[]');
  
  const updateMapping = (index, field, val) => {
    const newMappings = [...mappings];
    newMappings[index] = { ...newMappings[index], [field]: val };
    onChange(JSON.stringify(newMappings, null, 2));
  };
  
  const addMapping = () => {
    const newMappings = [...mappings, { source: '', target: '', transform: 'none' }];
    onChange(JSON.stringify(newMappings, null, 2));
  };
  
  const removeMapping = (index) => {
    const newMappings = mappings.filter((_, i) => i !== index);
    onChange(JSON.stringify(newMappings, null, 2));
  };
  
  return (
    <div className="property-group">
      <label>{label}</label>
      {mappings.map((m, i) => (
        <div key={i} className="mapping-row" style={{ display: 'flex', gap: '6px', marginBottom: '8px' }}>
          <input
            placeholder="Source"
            value={m.source}
            onChange={(e) => updateMapping(i, 'source', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <span style={{ color: '#999', alignSelf: 'center' }}>→</span>
          <input
            placeholder="Target"
            value={m.target}
            onChange={(e) => updateMapping(i, 'target', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <button
            onClick={() => removeMapping(i)}
            style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      ))}
      <button
        onClick={addMapping}
        style={{ padding: '6px 12px', border: '1px dashed #2196F3', borderRadius: '4px', background: 'transparent', color: '#2196F3', cursor: 'pointer', width: '100%', fontSize: '12px' }}
      >
        + Add Mapping
      </button>
    </div>
  );
}

// Remapper editor
function RemapperEditor({ value, dropOthers, onChange, onDropChange }) {
  const mappings = JSON.parse(value || '[]');
  
  const updateMapping = (index, field, val) => {
    const newMappings = [...mappings];
    newMappings[index] = { ...newMappings[index], [field]: val };
    onChange(JSON.stringify(newMappings, null, 2));
  };
  
  const addMapping = () => {
    const newMappings = [...mappings, { source: '', target: '', transform: 'none' }];
    onChange(JSON.stringify(newMappings, null, 2));
  };
  
  const removeMapping = (index) => {
    const newMappings = mappings.filter((_, i) => i !== index);
    onChange(JSON.stringify(newMappings, null, 2));
  };
  
  const transforms = [
    { value: 'none', label: 'None' },
    { value: 'upper', label: 'UPPER' },
    { value: 'lower', label: 'lower' },
    { value: 'title', label: 'Title' },
    { value: 'trim', label: 'trim' },
    { value: 'number', label: 'number' },
  ];
  
  return (
    <div className="property-group">
      <label>
        <input
          type="checkbox"
          checked={dropOthers}
          onChange={(e) => onDropChange(e.target.checked)}
          style={{ marginRight: '8px' }}
        />
        Drop unmapped fields
      </label>
      
      {mappings.map((m, i) => (
        <div key={i} className="remapper-row" style={{ display: 'flex', gap: '6px', marginBottom: '8px', alignItems: 'center' }}>
          <input
            placeholder="Source"
            value={m.source}
            onChange={(e) => updateMapping(i, 'source', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <span style={{ color: '#00BCD4', fontWeight: 'bold' }}>→</span>
          <input
            placeholder="Target"
            value={m.target}
            onChange={(e) => updateMapping(i, 'target', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <select
            value={m.transform}
            onChange={(e) => updateMapping(i, 'transform', e.target.value)}
            style={{ padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '11px' }}
          >
            {transforms.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <button
            onClick={() => removeMapping(i)}
            style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      ))}
      <button
        onClick={addMapping}
        style={{ padding: '6px 12px', border: '1px dashed #00BCD4', borderRadius: '4px', background: 'transparent', color: '#00BCD4', cursor: 'pointer', width: '100%', fontSize: '12px' }}
      >
        + Add Field Mapping
      </button>
    </div>
  );
}

// Join editor
function JoinEditor({ value, joinType, outputFields, prefixTables, onChange, onJoinTypeChange, onOutputFieldsChange, onPrefixChange }) {
  const joinKeys = JSON.parse(value || '[]');
  
  const updateKey = (index, field, val) => {
    const newKeys = [...joinKeys];
    newKeys[index] = { ...newKeys[index], [field]: val };
    onChange(JSON.stringify(newKeys, null, 2));
  };
  
  const addKey = () => {
    const newKeys = [...joinKeys, { left: '', right: '' }];
    onChange(JSON.stringify(newKeys, null, 2));
  };
  
  const removeKey = (index) => {
    const newKeys = joinKeys.filter((_, i) => i !== index);
    onChange(JSON.stringify(newKeys, null, 2));
  };
  
  const joinTypes = [
    { value: 'inner', label: 'INNER - Only matches' },
    { value: 'left', label: 'LEFT - All left, matching right' },
    { value: 'right', label: 'RIGHT - Matching left, all right' },
    { value: 'full', label: 'FULL - All from both' },
    { value: 'cross', label: 'CROSS - All combinations' },
  ];
  
  return (
    <div className="property-group">
      <label>Join Type</label>
      <select
        value={joinType}
        onChange={(e) => onJoinTypeChange(e.target.value)}
        style={{ width: '100%', padding: '8px', border: '1px solid #ddd', borderRadius: '6px', fontSize: '13px', marginBottom: '12px' }}
      >
        {joinTypes.map((jt) => (
          <option key={jt.value} value={jt.value}>{jt.label}</option>
        ))}
      </select>
      
      {joinType !== 'cross' && (
        <>
          <label>Join Keys</label>
          {joinKeys.map((k, i) => (
            <div key={i} className="join-key-row" style={{ display: 'flex', gap: '6px', marginBottom: '8px', alignItems: 'center' }}>
              <span style={{ fontSize: '10px', fontWeight: '600', color: '#2196F3' }}>LEFT.</span>
              <input
                placeholder="field"
                value={k.left}
                onChange={(e) => updateKey(i, 'left', e.target.value)}
                style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px', fontFamily: 'monospace' }}
              />
              <span style={{ color: '#4CAF50', fontWeight: 'bold' }}>=</span>
              <span style={{ fontSize: '10px', fontWeight: '600', color: '#FF9800' }}>RIGHT.</span>
              <input
                placeholder="field"
                value={k.right}
                onChange={(e) => updateKey(i, 'right', e.target.value)}
                style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px', fontFamily: 'monospace' }}
              />
              <button
                onClick={() => removeKey(i)}
                style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
              >
                ×
              </button>
            </div>
          ))}
          <button
            onClick={addKey}
            style={{ padding: '6px 12px', border: '1px dashed #4CAF50', borderRadius: '4px', background: 'transparent', color: '#4CAF50', cursor: 'pointer', width: '100%', fontSize: '12px' }}
          >
            + Add Join Key
          </button>
        </>
      )}
      
      <label style={{ marginTop: '16px', display: 'block' }}>
        <input
          type="checkbox"
          checked={prefixTables}
          onChange={(e) => onPrefixChange(e.target.checked)}
          style={{ marginRight: '8px' }}
        />
        Prefix fields with LEFT_/RIGHT_
      </label>
    </div>
  );
}

// Transform editor
function TransformEditor({ value, onChange }) {
  const transforms = JSON.parse(value || '[]');
  
  const updateTransform = (index, field, val) => {
    const newTransforms = [...transforms];
    newTransforms[index] = { ...newTransforms[index], [field]: val };
    onChange(JSON.stringify(newTransforms, null, 2));
  };
  
  const addTransform = () => {
    const newTransforms = [...transforms, { field: '', expression: '', alias: '' }];
    onChange(JSON.stringify(newTransforms, null, 2));
  };
  
  const removeTransform = (index) => {
    const newTransforms = transforms.filter((_, i) => i !== index);
    onChange(JSON.stringify(newTransforms, null, 2));
  };
  
  return (
    <div className="property-group">
      <label>Transformations</label>
      {transforms.map((t, i) => (
        <div key={i} className="transform-row" style={{ background: '#f5f5f5', padding: '10px', borderRadius: '6px', marginBottom: '8px' }}>
          <div style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}>
            <input
              placeholder="Field"
              value={t.field}
              onChange={(e) => updateTransform(i, 'field', e.target.value)}
              style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
            />
            <input
              placeholder="Expression"
              value={t.expression}
              onChange={(e) => updateTransform(i, 'expression', e.target.value)}
              style={{ flex: 2, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
            />
            <button
              onClick={() => removeTransform(i)}
              style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
            >
              ×
            </button>
          </div>
          <input
            placeholder="Alias (optional)"
            value={t.alias || ''}
            onChange={(e) => updateTransform(i, 'alias', e.target.value)}
            style={{ width: '100%', padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
        </div>
      ))}
      <button
        onClick={addTransform}
        style={{ padding: '6px 12px', border: '1px dashed #FF9800', borderRadius: '4px', background: 'transparent', color: '#FF9800', cursor: 'pointer', width: '100%', fontSize: '12px' }}
      >
        + Add Transformation
      </button>
    </div>
  );
}

// Filter editor
function FilterEditor({ value, logic, onChange, onLogicChange }) {
  const conditions = JSON.parse(value || '[]');
  
  const updateCondition = (index, field, val) => {
    const newConditions = [...conditions];
    newConditions[index] = { ...newConditions[index], [field]: val };
    onChange(JSON.stringify(newConditions, null, 2));
  };
  
  const addCondition = () => {
    const newConditions = [...conditions, { field: '', operator: 'equals', value: '' }];
    onChange(JSON.stringify(newConditions, null, 2));
  };
  
  const removeCondition = (index) => {
    const newConditions = conditions.filter((_, i) => i !== index);
    onChange(JSON.stringify(newConditions, null, 2));
  };
  
  const operators = [
    { value: 'equals', label: '=', icon: '=' },
    { value: 'not_equals', label: '!=', icon: '≠' },
    { value: 'greater', label: '>', icon: '>' },
    { value: 'less', label: '<', icon: '<' },
    { value: 'contains', label: 'contains', icon: '~' },
    { value: 'is_null', label: 'is null', icon: '∅' },
    { value: 'is_not_null', label: 'is not null', icon: '!∅' },
  ];
  
  return (
    <div className="property-group">
      <label>Filter Conditions</label>
      <div className="logic-selector" style={{ marginBottom: '10px' }}>
        <span style={{ fontSize: '12px', color: '#666', marginRight: '8px' }}>Logic:</span>
        <label style={{ fontSize: '12px', cursor: 'pointer', marginRight: '12px' }}>
          <input
            type="radio"
            name="logic"
            checked={logic === 'AND'}
            onChange={() => onLogicChange('AND')}
          /> AND
        </label>
        <label style={{ fontSize: '12px', cursor: 'pointer' }}>
          <input
            type="radio"
            name="logic"
            checked={logic === 'OR'}
            onChange={() => onLogicChange('OR')}
          /> OR
        </label>
      </div>
      {conditions.map((c, i) => (
        <div key={i} className="condition-row" style={{ display: 'flex', gap: '6px', marginBottom: '8px', alignItems: 'center' }}>
          <input
            placeholder="Field"
            value={c.field}
            onChange={(e) => updateCondition(i, 'field', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <select
            value={c.operator}
            onChange={(e) => updateCondition(i, 'operator', e.target.value)}
            style={{ padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          >
            {operators.map((op) => (
              <option key={op.value} value={op.value}>{op.icon} {op.label}</option>
            ))}
          </select>
          <input
            placeholder="Value"
            value={c.value}
            onChange={(e) => updateCondition(i, 'value', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <button
            onClick={() => removeCondition(i)}
            style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      ))}
      <button
        onClick={addCondition}
        style={{ padding: '6px 12px', border: '1px dashed #9C27B0', borderRadius: '4px', background: 'transparent', color: '#9C27B0', cursor: 'pointer', width: '100%', fontSize: '12px' }}
      >
        + Add Condition
      </button>
    </div>
  );
}

// Router editor (similar to filter but for TRUE/FALSE splitting)
function RouterEditor({ value, logic, onChange, onLogicChange }) {
  const conditions = JSON.parse(value || '[]');
  
  const updateCondition = (index, field, val) => {
    const newConditions = [...conditions];
    newConditions[index] = { ...newConditions[index], [field]: val };
    onChange(JSON.stringify(newConditions, null, 2));
  };
  
  const addCondition = () => {
    const newConditions = [...conditions, { field: '', operator: 'equals', value: '' }];
    onChange(JSON.stringify(newConditions, null, 2));
  };
  
  const removeCondition = (index) => {
    const newConditions = conditions.filter((_, i) => i !== index);
    onChange(JSON.stringify(newConditions, null, 2));
  };
  
  const operators = [
    { value: 'equals', label: '=', icon: '=' },
    { value: 'not_equals', label: '!=', icon: '≠' },
    { value: 'greater', label: '>', icon: '>' },
    { value: 'less', label: '<', icon: '<' },
    { value: 'contains', label: 'contains', icon: '~' },
    { value: 'is_null', label: 'is null', icon: '∅' },
    { value: 'is_not_null', label: 'is not null', icon: '!∅' },
  ];
  
  return (
    <div className="property-group">
      <label>Routing Conditions</label>
      <div className="router-branches-preview" style={{ display: 'flex', gap: '10px', marginBottom: '12px' }}>
        <div style={{ flex: 1, padding: '10px', background: '#E8F5E9', borderRadius: '6px', textAlign: 'center' }}>
          <div style={{ fontSize: '20px', marginBottom: '4px' }}>✓</div>
          <div style={{ fontSize: '11px', color: '#4CAF50', fontWeight: '600' }}>TRUE Branch</div>
          <div style={{ fontSize: '10px', color: '#666' }}>Matches condition</div>
        </div>
        <div style={{ flex: 1, padding: '10px', background: '#FFEBEE', borderRadius: '6px', textAlign: 'center' }}>
          <div style={{ fontSize: '20px', marginBottom: '4px' }}>✗</div>
          <div style={{ fontSize: '11px', color: '#f44336', fontWeight: '600' }}>FALSE Branch</div>
          <div style={{ fontSize: '10px', color: '#666' }}>Doesn't match</div>
        </div>
      </div>
      
      <div className="logic-selector" style={{ marginBottom: '10px' }}>
        <span style={{ fontSize: '12px', color: '#666', marginRight: '8px' }}>Match using:</span>
        <label style={{ fontSize: '12px', cursor: 'pointer', marginRight: '12px' }}>
          <input
            type="radio"
            name="router-logic"
            checked={logic === 'AND'}
            onChange={() => onLogicChange('AND')}
          /> AND
        </label>
        <label style={{ fontSize: '12px', cursor: 'pointer' }}>
          <input
            type="radio"
            name="router-logic"
            checked={logic === 'OR'}
            onChange={() => onLogicChange('OR')}
          /> OR
        </label>
      </div>
      {conditions.map((c, i) => (
        <div key={i} className="condition-row" style={{ display: 'flex', gap: '6px', marginBottom: '8px', alignItems: 'center' }}>
          <input
            placeholder="Field"
            value={c.field}
            onChange={(e) => updateCondition(i, 'field', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <select
            value={c.operator}
            onChange={(e) => updateCondition(i, 'operator', e.target.value)}
            style={{ padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          >
            {operators.map((op) => (
              <option key={op.value} value={op.value}>{op.icon} {op.label}</option>
            ))}
          </select>
          <input
            placeholder="Value"
            value={c.value}
            onChange={(e) => updateCondition(i, 'value', e.target.value)}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <button
            onClick={() => removeCondition(i)}
            style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      ))}
      <button
        onClick={addCondition}
        style={{ padding: '6px 12px', border: '1px dashed #FF5722', borderRadius: '4px', background: 'transparent', color: '#FF5722', cursor: 'pointer', width: '100%', fontSize: '12px' }}
      >
        + Add Condition
      </button>
    </div>
  );
}

// Aggregate editor
function AggregateEditor({ value, onChange }) {
  const groupFields = JSON.parse(value.groupFields || '[]');
  const aggregations = JSON.parse(value.aggregations || '[]');
  
  const updateGroupFields = (fields) => {
    onChange({ ...value, groupFields: JSON.stringify(fields, null, 2) });
  };
  
  const updateAggregations = (aggs) => {
    onChange({ ...value, aggregations: JSON.stringify(aggs, null, 2) });
  };
  
  const addGroupField = () => updateGroupFields([...groupFields, '']);
  const removeGroupField = (i) => updateGroupFields(groupFields.filter((_, idx) => idx !== i));
  
  const addAggregation = () => updateAggregations([...aggregations, { field: '', function: 'SUM', alias: '' }]);
  const removeAggregation = (i) => updateAggregations(aggregations.filter((_, idx) => idx !== i));
  const updateAggregation = (i, field, val) => {
    const newAggs = [...aggregations];
    newAggs[i] = { ...newAggs[i], [field]: val };
    updateAggregations(newAggs);
  };
  
  return (
    <div className="property-group">
      <label>Group By Fields</label>
      {groupFields.map((f, i) => (
        <div key={i} style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}>
          <input
            placeholder="Field"
            value={f}
            onChange={(e) => {
              const newFields = [...groupFields];
              newFields[i] = e.target.value;
              updateGroupFields(newFields);
            }}
            style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
          <button
            onClick={() => removeGroupField(i)}
            style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
          >
            ×
          </button>
        </div>
      ))}
      <button
        onClick={addGroupField}
        style={{ padding: '4px 8px', border: '1px dashed #00BCD4', borderRadius: '4px', background: 'transparent', color: '#00BCD4', cursor: 'pointer', width: '100%', fontSize: '11px', marginBottom: '16px' }}
      >
        + Add Group Field
      </button>
      
      <label>Aggregations</label>
      {aggregations.map((a, i) => (
        <div key={i} className="agg-row" style={{ background: '#e3f2fd', padding: '10px', borderRadius: '6px', marginBottom: '8px' }}>
          <div style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}>
            <select
              value={a.function}
              onChange={(e) => updateAggregation(i, 'function', e.target.value)}
              style={{ padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
            >
              <option value="SUM">SUM</option>
              <option value="AVG">AVG</option>
              <option value="COUNT">COUNT</option>
              <option value="MIN">MIN</option>
              <option value="MAX">MAX</option>
            </select>
            <input
              placeholder="Field"
              value={a.field}
              onChange={(e) => updateAggregation(i, 'field', e.target.value)}
              style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
            />
            <button
              onClick={() => removeAggregation(i)}
              style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
            >
              ×
            </button>
          </div>
          <input
            placeholder="Alias (optional)"
            value={a.alias || ''}
            onChange={(e) => updateAggregation(i, 'alias', e.target.value)}
            style={{ width: '100%', padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
        </div>
      ))}
      <button
        onClick={addAggregation}
        style={{ padding: '6px 12px', border: '1px dashed #00BCD4', borderRadius: '4px', background: 'transparent', color: '#00BCD4', cursor: 'pointer', width: '100%', fontSize: '12px' }}
      >
        + Add Aggregation
      </button>
    </div>
  );
}

// Validate editor
function ValidateEditor({ value, onChange }) {
  const rules = JSON.parse(value || '[]');
  
  const updateRule = (index, field, val) => {
    const newRules = [...rules];
    newRules[index] = { ...newRules[index], [field]: val };
    onChange(JSON.stringify(newRules, null, 2));
  };
  
  const addRule = () => {
    const newRules = [...rules, { field: '', type: 'required', message: '' }];
    onChange(JSON.stringify(newRules, null, 2));
  };
  
  const removeRule = (index) => {
    const newRules = rules.filter((_, i) => i !== index);
    onChange(JSON.stringify(newRules, null, 2));
  };
  
  const ruleTypes = [
    { value: 'required', label: 'Required' },
    { value: 'email', label: 'Email' },
    { value: 'numeric', label: 'Numeric' },
    { value: 'date', label: 'Date' },
    { value: 'pattern', label: 'Pattern' },
    { value: 'range', label: 'Range' },
    { value: 'unique', label: 'Unique' },
  ];
  
  return (
    <div className="property-group">
      <label>Validation Rules</label>
      {rules.map((r, i) => (
        <div key={i} className="rule-row" style={{ background: '#e8f5e9', padding: '10px', borderRadius: '6px', marginBottom: '8px' }}>
          <div style={{ display: 'flex', gap: '6px', marginBottom: '6px' }}>
            <input
              placeholder="Field"
              value={r.field}
              onChange={(e) => updateRule(i, 'field', e.target.value)}
              style={{ flex: 1, padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
            />
            <select
              value={r.type}
              onChange={(e) => updateRule(i, 'type', e.target.value)}
              style={{ padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
            >
              {ruleTypes.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <button
              onClick={() => removeRule(i)}
              style={{ padding: '6px 10px', border: 'none', background: '#ffebee', borderRadius: '4px', color: '#f44336', cursor: 'pointer' }}
            >
              ×
            </button>
          </div>
          <input
            placeholder="Error message"
            value={r.message || ''}
            onChange={(e) => updateRule(i, 'message', e.target.value)}
            style={{ width: '100%', padding: '6px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '12px' }}
          />
        </div>
      ))}
      <button
        onClick={addRule}
        style={{ padding: '6px 12px', border: '1px dashed #8BC34A', borderRadius: '4px', background: 'transparent', color: '#8BC34A', cursor: 'pointer', width: '100%', fontSize: '12px' }}
      >
        + Add Validation Rule
      </button>
    </div>
  );
}

// Connected nodes info
function ConnectedNodesInfo({ node, getConnectedNodes }) {
  const { upstream, downstream } = getConnectedNodes(node.id);
  
  return (
    <div className="property-group" style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid #e0e0e0' }}>
      <label style={{ fontSize: '11px', color: '#999', textTransform: 'uppercase' }}>Data Flow</label>
      
      {upstream.length > 0 && (
        <div style={{ marginBottom: '10px' }}>
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>📥 From:</div>
          {upstream.map((n) => (
            <div key={n.id} style={{ padding: '6px 10px', background: '#f5f5f5', borderRadius: '4px', fontSize: '12px', marginBottom: '4px' }}>
              {n.data?.label || n.type}
            </div>
          ))}
        </div>
      )}
      
      {downstream.length > 0 && (
        <div>
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '6px' }}>📤 To:</div>
          {downstream.map((n) => (
            <div key={n.id} style={{ padding: '6px 10px', background: '#f5f5f5', borderRadius: '4px', fontSize: '12px', marginBottom: '4px' }}>
              {n.data?.label || n.type}
            </div>
          ))}
        </div>
      )}
      
      {upstream.length === 0 && downstream.length === 0 && (
        <div style={{ fontSize: '12px', color: '#999', fontStyle: 'italic' }}>
          No connections yet. Connect nodes to establish data flow.
        </div>
      )}
    </div>
  );
}

export default PipelineGraph;
