import React from 'react';
import ReactFlow, {
  Controls,
  Background,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
  Node,
  Edge,
  BackgroundVariant,
  DefaultEdgeOptions,
  FitViewOptions,
  ReactFlowInstance,
  Panel
} from 'reactflow';
import 'reactflow/dist/style.css';

// Later, we can define and import custom node types:
// import StartNode from './customNodes/StartNode';
// const nodeTypes = { startNode: StartNode, ... };

interface WorkflowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: OnNodesChange;
  onEdgesChange: OnEdgesChange;
  onConnect: OnConnect;
  onNodeClick?: (event: React.MouseEvent, node: Node) => void;
  onEdgeClick?: (event: React.MouseEvent, edge: Edge) => void;
  onPaneClick?: (event: React.MouseEvent) => void;
  onNodeDragStop?: (event: React.MouseEvent, node: Node, nodesPresent: Node[]) => void;
  fitView?: boolean;
  fitViewOptions?: FitViewOptions;
  onDrop?: (event: React.DragEvent<HTMLDivElement>) => void;
  onDragOver?: (event: React.DragEvent<HTMLDivElement>) => void;
  onInit?: (reactFlowInstance: ReactFlowInstance) => void;
  deleteKeyCode?: string | string[] | null;
  onNodesDelete?: (nodes: Node[]) => void;
  onEdgesDelete?: (edges: Edge[]) => void;
  onNodeDoubleClick?: (event: React.MouseEvent, node: Node) => void;
  // nodeTypes?: any; // To pass custom node components
}

const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  onEdgeClick,
  onPaneClick,
  onNodeDragStop,
  fitView = true,
  fitViewOptions = { padding: 0.2, includeHiddenNodes: true },
  onDrop,
  onDragOver,
  onInit,
  deleteKeyCode = 'Delete',
  onNodesDelete,
  onEdgesDelete,
  onNodeDoubleClick
}) => {
  const defaultEdgeOptions: DefaultEdgeOptions = {
    style: { stroke: '#3B82F6', strokeWidth: 2 }, // Blue-500
    type: 'smoothstep', // A nice default edge type
  };

  return (
    <div className="workflow-canvas-container h-full w-full bg-slate-50 relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onNodeDragStop={onNodeDragStop}
        onNodeDoubleClick={onNodeDoubleClick}
        fitView={fitView}
        fitViewOptions={fitViewOptions}
        defaultEdgeOptions={defaultEdgeOptions}
        nodesDraggable={true}
        nodesConnectable={true}
        elementsSelectable={true}
        proOptions={{ hideAttribution: true }}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onInit={onInit}
        deleteKeyCode={deleteKeyCode}
        onNodesDelete={onNodesDelete}
        onEdgesDelete={onEdgesDelete}
        className="workflow-canvas"
        snapToGrid={true}
        snapGrid={[15, 15]}
        connectionRadius={40}
        minZoom={0.1}
        maxZoom={1.5}
      >
        <Background 
          variant={BackgroundVariant.Dots} 
          gap={15} 
          size={1} 
          color="#CBD5E1"
          className="bg-slate-50" 
        />
        
        <Panel position="top-right" className="bg-white shadow-md p-2 rounded-md text-xs border border-slate-200">
          <div className="flex items-center space-x-2.5 text-slate-600">
            <div className="flex items-center space-x-1.5">
              <span className="inline-block w-3 h-3 bg-blue-500 rounded-full"></span>
              <span>Double click node to edit</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="inline-block w-3 h-3 bg-red-500 rounded-full"></span>
              <span>Press Delete to remove</span>
            </div>
          </div>
        </Panel>

        <Controls 
          showZoom={true}
          showFitView={true} 
          showInteractive={false}
          position="bottom-right"
          style={{
            display: 'flex',
            flexDirection: 'column',
            padding: '6px',
            gap: '6px',
            background: 'white',
            borderRadius: '6px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24)',
            border: '1px solid #EDF2F7'
          }}
        />
      </ReactFlow>
    </div>
  );
};

export default WorkflowCanvas; 