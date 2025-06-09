import React, { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
import { useWorkflow } from "@/lib/WorkflowContext";
import { getWorkflowData, getCurrentFile, API_BASE_URL } from "@/services/api";
import { Save, Download, ArrowRight, ChevronLeft, Search, FileJson } from "lucide-react";
import ElementPanel from "./ElementPanel";
import ElementCreator from "./ElementCreator";
import WorkflowCanvas from "./WorkflowCanvas";
import { toast } from "@/components/ui/use-toast";
import {
  Node as RfNode,
  Edge as RfEdge,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  XYPosition,
  Position,
  ReactFlowProvider,
  useReactFlow,
  NodeChange,
  EdgeChange,
  applyNodeChanges,
  applyEdgeChanges,
  ReactFlowInstance
} from 'reactflow';
import 'reactflow/dist/style.css';

interface CustomNodeData {
  label: string;
  nodeType: "start" | "end" | "task" | "condition" | "approver" | "input";
  width?: number;
  height?: number;
}

type AppNode = RfNode<CustomNodeData>;
type AppEdge = RfEdge<any>;

interface SavedWorkflow {
  id: string;
  conditionId?: string;
  nodes: AppNode[];
  edges: AppEdge[];
  version?: number;
  timestamp?: string;
}

interface ElementItemType {
  id: string;
  name: string;
  type: 'condition' | 'approver'; 
  description: string;
  nodeRefs?: string[]; // Store references to nodes on canvas that use this item
}

const nodeStyles = {
  start: {
    background: '#63B3ED',
    color: 'white',
    border: '1px solid #2B6CB0',
    borderRadius: '50%',
    width: 80,
    height: 80,
    display: 'flex',
    alignItems: 'center' as 'center',
    justifyContent: 'center' as 'center',
    textAlign: 'center' as 'center',
    fontSize: '12px',
  },
  end: {
    background: '#63B3ED',
    color: 'white',
    border: '1px solid #2B6CB0',
    borderRadius: '50%',
    width: 80,
    height: 80,
    display: 'flex',
    alignItems: 'center' as 'center',
    justifyContent: 'center' as 'center',
    textAlign: 'center' as 'center',
    fontSize: '12px',
  },
  condition: {
    background: '#90CDF4',
    color: '#1A365D',
    border: '1px solid #2C5282',
    borderRadius: '4px',
    padding: '10px 15px',
    minWidth: 150,
    textAlign: 'center' as 'center',
    fontSize: '13px',
  },
  approver: {
    background: '#EBF8FF',
    color: '#2C5282',
    border: '1px solid #4299E1',
    borderRadius: '4px',
    padding: '10px 15px',
    minWidth: 150,
    textAlign: 'center' as 'center',
    fontSize: '13px',
  },
};

const transformApiDataToGraph = (
  apiData: any[], 
  conditionId: string
): { nodes: AppNode[], edges: AppEdge[] } => {
    const conditionData = apiData.find(item => item["Condition Serial No."] === conditionId);
    if (!conditionData) return { nodes: [], edges: [] };

    let nodes: AppNode[] = [];
    let edges: AppEdge[] = [];
    let yPos = 50;
    const xPos = 250;
    const nodeGap = 120;

    let lastNodeId = `${conditionId}_start`;

    nodes.push({
      id: lastNodeId,
      type: 'default',
      position: { x: xPos, y: yPos },
      data: { label: 'Start', nodeType: 'start' },
      style: nodeStyles.start,
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
    });
    yPos += nodeGap;

    const conditionKeys = Object.keys(conditionData)
        .filter(key => key.includes("_Metadata_Condition"))
        .sort((a,b) => {
            const numA = parseInt(a.split('_').pop() || '0');
            const numB = parseInt(b.split('_').pop() || '0');
            return numA - numB;
        });

    conditionKeys.forEach((key, index) => {
        const conditionLabel = conditionData[key];
        if (conditionLabel) {
            const conditionNodeId = `${conditionId}_cond${index + 1}`;
            nodes.push({ 
                id: conditionNodeId, 
                type: 'default',
                position: { x: xPos - 50, y: yPos },
                data: { label: conditionLabel, nodeType: 'condition' },
                style: nodeStyles.condition,
                sourcePosition: Position.Bottom,
                targetPosition: Position.Top,
            });
            edges.push({ 
                id: `e_${lastNodeId}_${conditionNodeId}`, 
                source: lastNodeId, 
                target: conditionNodeId, 
            });
            lastNodeId = conditionNodeId;
            yPos += nodeGap;
        }
    });

    const approverKeys = Object.keys(conditionData)
        .filter(key => key.includes("Approver_Level_"))
        .sort((a,b) => {
            const numA = parseInt(a.split('_').pop() || '0');
            const numB = parseInt(b.split('_').pop() || '0');
            return numA - numB;
        });

    approverKeys.forEach((key, index) => {
        const approverLabel = conditionData[key];
        if (approverLabel && approverLabel.toLowerCase() !== 'requisition approved') {
            const approverNodeId = `${conditionId}_appr${index + 1}`;
            nodes.push({ 
                id: approverNodeId, 
                type: 'default',
                position: { x: xPos, y: yPos },
                data: { label: approverLabel, nodeType: 'approver' },
                style: nodeStyles.approver,
                sourcePosition: Position.Bottom,
                targetPosition: Position.Top,
            });
            edges.push({ 
                id: `e_${lastNodeId}_${approverNodeId}`, 
                source: lastNodeId, 
                target: approverNodeId 
            });
            lastNodeId = approverNodeId;
            yPos += nodeGap;
        }
    });

    const endNodeId = `${conditionId}_end`;
    nodes.push({ 
        id: endNodeId, 
        type: 'default',
        position: { x: xPos, y: yPos }, 
        data: { label: 'End', nodeType: 'end' },
        style: nodeStyles.end,
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
    });
    edges.push({ id: `e_${lastNodeId}_${endNodeId}`, source: lastNodeId, target: endNodeId });

    return { nodes, edges };
};

interface WorkflowEditorCanvasWrapperProps {
    rfNodes: AppNode[];
    rfEdges: AppEdge[];
    onNodesChange: (changes: NodeChange[]) => void;
    onEdgesChange: (changes: EdgeChange[]) => void;
    onConnect: (connection: Connection) => void;
    handleNodeClick: (event: React.MouseEvent, node: AppNode) => void;
    handlePaneClick: () => void;
    handleNodeDragStop: (event: React.MouseEvent, node: AppNode) => void;
    onDropCanvas: (event: React.DragEvent<HTMLDivElement>) => void;
    onDragOverCanvas: (event: React.DragEvent<HTMLDivElement>) => void;
    onCanvasInit: (instance: ReactFlowInstance) => void;
    onNodesDeleted: (nodes: AppNode[]) => void;
    onEdgesDeleted: (edges: AppEdge[]) => void;
    onNodeDoubleClick: (event: React.MouseEvent, node: AppNode) => void;
}

const WorkflowEditorCanvasWrapper: React.FC<WorkflowEditorCanvasWrapperProps> = (props) => {
    const {
        rfNodes,
        rfEdges,
        onNodesChange,
        onEdgesChange,
        onConnect,
        handleNodeClick,
        handlePaneClick,
        handleNodeDragStop,
        onDropCanvas,
        onDragOverCanvas,
        onCanvasInit,
        onNodesDeleted,
        onEdgesDeleted,
        onNodeDoubleClick
    } = props;
    
    return (
        <WorkflowCanvas 
            nodes={rfNodes} 
            edges={rfEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={handleNodeClick}
            onPaneClick={handlePaneClick}
            onNodeDragStop={handleNodeDragStop}
            onDrop={onDropCanvas}
            onDragOver={onDragOverCanvas}
            onInit={onCanvasInit}
            onNodesDelete={onNodesDeleted}
            onEdgesDelete={onEdgesDeleted}
            onNodeDoubleClick={onNodeDoubleClick}
        />
    );
};

const WorkflowDesign: React.FC = () => {
  const navigate = useNavigate();
  const { markStepCompleted } = useWorkflow();
  
  const [rawData, setRawData] = useState<any[]>([]);
  const [workflowsByCondition, setWorkflowsByCondition] = useState<Record<string, { nodes: AppNode[], edges: AppEdge[] }>>({});
  
  const [rfNodes, setRfNodes, onNodesChangeReactFlow] = useNodesState<CustomNodeData>([]);
  const [rfEdges, setRfEdges, onEdgesChangeReactFlow] = useEdgesState([]);
  
  const [activeCondition, setActiveCondition] = useState<string | null>(null);
  const [conditionButtons, setConditionButtons] = useState<{id: string, label: string}[]>([]);
  const [elementLibrary, setPanelElements] = useState<{conditions: ElementItemType[], approvers: ElementItemType[]}>({ conditions: [], approvers: [] });

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savedWorkflows, setSavedWorkflows] = useState<SavedWorkflow[]>([]);
  const [referenceImageUrl, setReferenceImageUrl] = useState<string>('');
  const [activeTab, setActiveTab] = useState("editor");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);

  const [showElementCreator, setShowElementCreator] = useState(false);
  const [elementCreatorType, setElementCreatorType] = useState<"start" | "end" | "task" | "condition" | "approver" | "input">('task');
  const [elementCreatorInitialData, setElementCreatorInitialData] = useState<any>({});
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  
  const [selectedRfElement, setSelectedRfElement] = useState<AppNode | null>(null);
  const [reactFlowInstance, setReactFlowInstance] = useState<ReactFlowInstance | null>(null);

  const onCanvasInit = useCallback((instance: ReactFlowInstance) => {
    console.log("ReactFlow instance initialized", instance);
    setReactFlowInstance(instance);
  }, []);

  const processAndGenerateGraphs = (data: any[]) => {
    setRawData(data);
    const conditionIds = [...new Set(data.map(item => item["Condition Serial No."]).filter(Boolean))] as string[];
    conditionIds.sort();

    if (conditionIds.length === 0) {
        console.warn("No Condition Serial No. found in data.");
        setConditionButtons([]);
        setWorkflowsByCondition({});
        setActiveCondition(null);
        setRfNodes([]); 
        setRfEdges([]);
        return;
    }

    const generatedWorkflows: Record<string, { nodes: AppNode[], edges: AppEdge[] }> = {};
    conditionIds.forEach(id => {
        generatedWorkflows[id] = transformApiDataToGraph(data, id);
    });

    setWorkflowsByCondition(generatedWorkflows);
    const buttons = conditionIds.map(id => ({ id, label: id }));
    setConditionButtons(buttons);
    
    if (conditionIds.length > 0) {
        setActiveCondition(conditionIds[0]);
        const initialWorkflow = generatedWorkflows[conditionIds[0]];
        setRfNodes(initialWorkflow.nodes);
        setRfEdges(initialWorkflow.edges);
    } else {
        setRfNodes([]);
        setRfEdges([]);
    }
    setHasUnsavedChanges(false);
  };

  useEffect(() => {
    const fetchAndProcessData = async () => {
      setIsLoading(true);
      setError(null);
      let loadedRawData: any[] | null = null;
      let dataFromLocalStorage = false;

      try {
        const fileInfo = await getCurrentFile();
        if (fileInfo && fileInfo.filename) {
          const fetchedData = await getWorkflowData(fileInfo.filename);
          if (Array.isArray(fetchedData)) {
            loadedRawData = fetchedData;
            localStorage.setItem('workflowRawData', JSON.stringify(loadedRawData));
          } else {
              console.warn("API did not return the expected array format. Trying localStorage.");
          }
          if(fileInfo.imageUrl) {
            const imageUrl = `${API_BASE_URL}${fileInfo.imageUrl}`;
            setReferenceImageUrl(imageUrl);
          }
        }
        
        if (!loadedRawData) {
            const storedRawData = localStorage.getItem('workflowRawData');
            if (storedRawData) {
                console.log("Loading raw data from localStorage");
                loadedRawData = JSON.parse(storedRawData);
                dataFromLocalStorage = true;
            } else {
                console.log("No raw data found in API response or localStorage.");
            }
             const imageMeta = localStorage.getItem('imageMetadata');
             if (imageMeta && !referenceImageUrl) setReferenceImageUrl(JSON.parse(imageMeta).imageUrl);
        }

        if (loadedRawData && loadedRawData.length > 0) {
            processAndGenerateGraphs(loadedRawData);
            if (dataFromLocalStorage) {
              toast({ title: "Loaded from Cache", description: "Workflow data loaded from local storage.", variant: "default" });
            }
        } else {
            setError("No workflow data found or data is empty.");
            setRfNodes([]); setRfEdges([]);
        }
      } catch (err) {
        console.error("Error fetching/processing workflow data:", err);
        const errorMessage = err instanceof Error ? err.message : "Failed to load workflow data";
        setError(errorMessage);
        toast({ title: "Error Loading Data", description: errorMessage, variant: "destructive"});
        setRfNodes([]); setRfEdges([]);
      } finally {
        setIsLoading(false);
      }

      const storedSavedWorkflows = localStorage.getItem('savedWorkflows');
      if (storedSavedWorkflows) {
        try { setSavedWorkflows(JSON.parse(storedSavedWorkflows)); } 
        catch (e) { console.error("Failed to parse saved workflows:", e); }
      }
    };
    fetchAndProcessData();
  }, []);

  useEffect(() => {
    if (activeCondition && workflowsByCondition[activeCondition]) {
      const currentWorkflow = workflowsByCondition[activeCondition];
      setRfNodes(currentWorkflow.nodes);
      setRfEdges(currentWorkflow.edges);
      setSelectedRfElement(null); 
    } else if (!activeCondition && conditionButtons.length > 0) {
       setActiveCondition(conditionButtons[0].id);
    } else if (!activeCondition) {
        setRfNodes([]);
        setRfEdges([]);
    }
  }, [activeCondition, workflowsByCondition, conditionButtons, setRfNodes, setRfEdges]);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => {
        if (!activeCondition) return;
        const newNodes = applyNodeChanges(changes, rfNodes);
        setRfNodes(newNodes);

        const nonRemoveChanges = changes.filter(c => c.type !== 'remove');
        if (nonRemoveChanges.length > 0) {
             setWorkflowsByCondition(prev => ({
                ...prev,
                [activeCondition!]: { 
                    ...(prev[activeCondition!] || { nodes: [], edges: [] }),
                    nodes: applyNodeChanges(nonRemoveChanges, prev[activeCondition!]?.nodes || [])
                }
            }));
        }
        if (changes.some(c => c.type === 'position' && c.dragging === false)) setHasUnsavedChanges(true);
    },
    [activeCondition, rfNodes, setRfNodes, setWorkflowsByCondition]
  );

  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => {
        if (!activeCondition) return;
        const newEdges = applyEdgeChanges(changes, rfEdges);
        setRfEdges(newEdges);

        const nonRemoveChanges = changes.filter(c => c.type !== 'remove');
        if (nonRemoveChanges.length > 0) {
            setWorkflowsByCondition(prev => ({
                ...prev,
                [activeCondition!]: { 
                    ...(prev[activeCondition!] || { nodes: [], edges: [] }),
                    edges: applyEdgeChanges(nonRemoveChanges, prev[activeCondition!]?.edges || []) 
                }
            }));
        }
        if (changes.some(c => c.type !== 'select')) setHasUnsavedChanges(true);
    },
    [activeCondition, rfEdges, setRfEdges, setWorkflowsByCondition]
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!activeCondition) return;
      const newEdge = { ...connection, id: `edge-${Date.now()}`, type: 'smoothstep', style: { stroke: '#3B82F6', strokeWidth: 2 } };
      const updatedEdges = addEdge(newEdge, rfEdges);
      setRfEdges(updatedEdges);
      setWorkflowsByCondition(prev => ({
        ...prev,
        [activeCondition!]: { 
            ...(prev[activeCondition!] || { nodes: [], edges: [] }),
            edges: addEdge(newEdge, prev[activeCondition!]?.edges || []) 
        }
      }));
      setHasUnsavedChanges(true);
    },
    [activeCondition, rfEdges, setRfEdges, setWorkflowsByCondition]
  );

  const handleNodeClick = useCallback((_event: React.MouseEvent, node: AppNode) => {
    setSelectedRfElement(node);
  }, []);

  const handlePaneClick = useCallback(() => {
    setSelectedRfElement(null);
  }, []);

  const handleNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: AppNode) => {
      if (!activeCondition) return;
      setWorkflowsByCondition(prev => {
        const currentNodes = prev[activeCondition!]?.nodes || [];
        const updatedNodes = currentNodes.map(n =>
          n.id === node.id ? { ...n, position: node.position } : n 
        );
        return {
          ...prev,
          [activeCondition!]: { ...(prev[activeCondition!] || {edges: []}), nodes: updatedNodes }
        };
      });
      setHasUnsavedChanges(true);
    },
    [activeCondition, setWorkflowsByCondition]
  );
  
  const handleAddElementRequest = (type: 'condition' | 'approver') => {
    const nodeTypeForModal = type === 'condition' ? 'condition' : 'approver';
    setElementCreatorType(nodeTypeForModal); 
    setElementCreatorInitialData({ type: nodeTypeForModal, label: '' });
    setShowElementCreator(true);
  };

  const handleElementSave = (elementData: {
    id?: string;
    label: string;
    type: "start" | "end" | "task" | "condition" | "approver" | "input";
    position?: XYPosition
  }) => {
    const { id, label, type, position } = elementData;

    if (id) {
      if (!activeCondition) return;
      
      console.log("Element save called with data:", elementData);
      
      const isEditing = !!id;
      const nodeId = id;
      let finalPosition = position;

      if (!finalPosition && !isEditing) {
          console.log("No position provided, using default placement");
          const yOffset = rfNodes.length > 0 ? rfNodes.reduce((max, n) => Math.max(max, n.position.y), 0) + 120 : 100;
          finalPosition = { x: 250, y: yOffset };
      } else if (finalPosition) {
          console.log("Using provided position:", finalPosition);
      }
      
      const nodeData = { label, nodeType: type };
      const style = (nodeStyles[type as keyof typeof nodeStyles] || nodeStyles.approver) as React.CSSProperties;

      if (isEditing) {
          const updatedNodesReactFlow = rfNodes.map(node => 
              node.id === nodeId ? {...node, data: nodeData, style: style, position: finalPosition || node.position } : node
          );
          setRfNodes(updatedNodesReactFlow);
          setWorkflowsByCondition(prev => ({
              ...prev,
              [activeCondition!]: {
                  ...(prev[activeCondition!] || {edges: []}),
                  nodes: (prev[activeCondition!]?.nodes || []).map(node => 
                      node.id === nodeId ? {...node, data: nodeData, style: style, position: finalPosition || node.position } : node
                  )
              }
          })); 
      } else {
          const newNodeToAdd: AppNode = {
              id: nodeId,
              position: finalPosition!,
              data: nodeData,
              type: 'default',
              style: style,
              sourcePosition: Position.Bottom,
              targetPosition: Position.Top,
          };
          console.log("Adding new node:", newNodeToAdd);
          
          const updatedNodesReactFlow = rfNodes.concat(newNodeToAdd);
          setRfNodes(updatedNodesReactFlow);
          setWorkflowsByCondition(prev => ({
              ...prev,
              [activeCondition!]: { 
                  ...(prev[activeCondition!] || {edges: []}), 
                  nodes: (prev[activeCondition!]?.nodes || []).concat(newNodeToAdd) 
              }
          }));
      }
      
      setHasUnsavedChanges(true);
      setShowElementCreator(false);
      setElementCreatorInitialData({});
    } else {
      if (position) {
        // Logic for creating a new node on canvas if position is provided (drag/drop)
        // ... existing code ...
      } else if (type === 'condition' || type === 'approver') {
        // Logic for creating a new element for the panel list
        const newItemId = `${type}-${Date.now()}`;
        const newItem: ElementItemType = {
          id: newItemId,
          name: label,
          type: type,
          description: `Manually added ${type}`,
          nodeRefs: [], // Initially no nodes reference this panel element
        };

        setPanelElements(prev => ({
          ...prev,
          [type === 'condition' ? 'conditions' : 'approvers']: [
            ...prev[type === 'condition' ? 'conditions' : 'approvers'],
            newItem
          ]
        }));

        setHasUnsavedChanges(true);

        toast({
          title: "Element Added",
          description: `Added '${label}' to the workflow library. You can now drag it to the canvas.`,
          variant: "default"
        });
      }
    }
  };
  
  const onDragOverCanvas = useCallback((event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDropCanvas = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      
      // Check if we have all the required elements for a successful drop
      if (!reactFlowWrapper.current || !activeCondition) {
        console.error("Drop failed: Missing reactFlowWrapper or activeCondition");
        return;
      }
      
      // Get the dragged data
      const type = event.dataTransfer.getData('application/reactflow-nodetype') as "condition" | "approver";
      const label = event.dataTransfer.getData('application/reactflow-label') || `New ${type}`;
      const itemId = event.dataTransfer.getData('application/reactflow-item-id');
      
      if (!type) {
        console.error("Drop failed: Missing node type in dataTransfer");
        return;
      }
      
      console.log("Drop detected:", { type, label, itemId });
      
      // We need a ReactFlow instance to calculate the correct position
      if (!reactFlowInstance) {
        console.error("Drop failed: No reactFlowInstance available");
        return;
      }
      
      try {
        // Calculate drop position in the ReactFlow canvas coordinates
        const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
        const position = reactFlowInstance.project({
          x: event.clientX - reactFlowBounds.left,
          y: event.clientY - reactFlowBounds.top,
        });
        
        console.log("Calculated position:", position);
        
        // Create node directly from the panel item
        const nodeType = type === 'condition' ? 'condition' : 'approver';
        const nodeId = `${activeCondition}_${nodeType}_${Date.now()}`;
        const style = nodeStyles[nodeType as keyof typeof nodeStyles] as React.CSSProperties;
        
        // Create the new node
        const newNode: AppNode = {
          id: nodeId,
          type: 'default',
          position: position,
          data: { label, nodeType },
          style,
          sourcePosition: Position.Bottom,
          targetPosition: Position.Top,
        };
        
        // Add the node to the flow
        setRfNodes(prevNodes => [...prevNodes, newNode]);
        
        // Update workflowsByCondition to include the new node
        setWorkflowsByCondition(prev => {
          const currentFlow = prev[activeCondition!] || { nodes: [], edges: [] };
          return {
            ...prev,
            [activeCondition!]: {
              ...currentFlow,
              nodes: [...currentFlow.nodes, newNode]
            }
          };
        });
        
        // Track what panel item this node came from
        if (itemId) {
          // Update panel elements to track node references
          setPanelElements(prev => {
            const updatedElements = { ...prev };
            
            // Find and update the element in either conditions or approvers array
            const updateItemInArray = (items: ElementItemType[]) => items.map(item => {
              if (item.id === itemId) {
                return {
                  ...item,
                  nodeRefs: [...(item.nodeRefs || []), nodeId]
                };
              }
              return item;
            });
            
            updatedElements.conditions = updateItemInArray(updatedElements.conditions);
            updatedElements.approvers = updateItemInArray(updatedElements.approvers);
            
            return updatedElements;
          });
        }
        
        setHasUnsavedChanges(true);
        
        // Provide user feedback
        toast({
          title: "Node Added",
          description: `Added ${label} to the workflow`,
          variant: "default"
        });
      } catch (error) {
        console.error("Error during drop position calculation:", error);
      }
    },
    [activeCondition, reactFlowInstance, setRfNodes, setWorkflowsByCondition, setPanelElements]
  );

  const handleNodeDoubleClick = useCallback((_event: React.MouseEvent, node: AppNode) => {
    if (node.data.nodeType === 'start' || node.data.nodeType === 'end') return;
    setElementCreatorType(node.data.nodeType);
    setElementCreatorInitialData({
      id: node.id,
      type: node.data.nodeType,
      label: node.data.label,
      position: node.position
    });
    setShowElementCreator(true);
  }, []);

  const handleEditSelectedNode = useCallback((node: AppNode) => {
    if (node.data.nodeType === 'start' || node.data.nodeType === 'end') return;
    setElementCreatorType(node.data.nodeType);
    setElementCreatorInitialData({
      id: node.id,
      type: node.data.nodeType,
      label: node.data.label,
      position: node.position
    });
    setShowElementCreator(true);
  }, []);

  const performNodeDeletion = useCallback((nodeIdToDelete: string) => {
    if (!activeCondition) return;

    setRfNodes((prevNodes) => prevNodes.filter(n => n.id !== nodeIdToDelete));
    setRfEdges((prevEdges) => prevEdges.filter(e => e.source !== nodeIdToDelete && e.target !== nodeIdToDelete));

    setWorkflowsByCondition(prev => {
      const currentWf = prev[activeCondition!] || { nodes: [], edges: [] };
      return {
        ...prev,
        [activeCondition!]: {
          nodes: currentWf.nodes.filter(node => node.id !== nodeIdToDelete),
          edges: currentWf.edges.filter(edge => edge.source !== nodeIdToDelete && edge.target !== nodeIdToDelete)
        }
      };
    });

    if (selectedRfElement && selectedRfElement.id === nodeIdToDelete) {
      setSelectedRfElement(null);
    }
    setHasUnsavedChanges(true);
    toast({ title: "Node Deleted", description: `Node ${nodeIdToDelete} has been removed.`, variant: "default" });
  }, [activeCondition, selectedRfElement, setRfNodes, setRfEdges, setWorkflowsByCondition]);

  const handleDeleteSelectedNode = useCallback((nodeId: string) => {
    performNodeDeletion(nodeId);
  }, [performNodeDeletion]);

  // Handler for editing an item directly from the panel list
  const handleEditPanelItem = useCallback((item: ElementItemType) => {
    setElementCreatorType(item.type);
    setElementCreatorInitialData({
      id: item.id, // Use item id for editing panel item
      type: item.type,
      label: item.name,
      // Position is not relevant for panel items
    });
    setShowElementCreator(true);
  }, []);

  // Handler for deleting an item directly from the panel list
  const handleDeletePanelItem = useCallback((id: string, name: string) => {
    setPanelElements(prev => {
      const updatedElements = { ...prev };
      const type = id.split('-')[0]; // Assuming ID format is type-timestamp
      if (type === 'condition' || type === 'approver') {
        updatedElements[type === 'condition' ? 'conditions' : 'approvers'] = prev[type === 'condition' ? 'conditions' : 'approvers'].filter(item => item.id !== id);
      }
      return updatedElements;
    });

    toast({
      title: "Element Deleted",
      description: `Removed '${name}' from the workflow library.`,
      variant: "default"
    });
    setHasUnsavedChanges(true);
  }, []);

  const onNodesDeleted = useCallback((deletedNodes: AppNode[]) => {
    if (!activeCondition || deletedNodes.length === 0) return;
    deletedNodes.forEach(node => performNodeDeletion(node.id));
  }, [activeCondition, performNodeDeletion]);

  const onEdgesDeleted = useCallback((deletedEdges: AppEdge[]) => {
    if (!activeCondition || deletedEdges.length === 0) return;
    setWorkflowsByCondition(prev => {
        const currentWf = prev[activeCondition!] || { nodes: [], edges: [] };
        const deletedEdgeIds = new Set(deletedEdges.map(e => e.id));
        return {
            ...prev,
            [activeCondition!]: {
                ...currentWf,
                edges: currentWf.edges.filter(edge => !deletedEdgeIds.has(edge.id))
            }
        };
    });
    setHasUnsavedChanges(true);
  }, [activeCondition, setWorkflowsByCondition]);

  const handleSaveWorkflow = () => {
      if (!activeCondition) {
        toast({ title: "Cannot Save", description: "No active workflow condition selected.", variant: "destructive" });
        return;
      }
      const currentNodesForSave = rfNodes; 
      const currentEdgesForSave = rfEdges;

      if (!currentNodesForSave || currentNodesForSave.length === 0) {
          toast({ title: "Save Error", description: `No nodes to save for condition ${activeCondition}.`, variant: "destructive" });
          return;
      }

      const updatedWorkflowsMaster = {
          ...workflowsByCondition,
          [activeCondition]: {
              nodes: currentNodesForSave,
              edges: currentEdgesForSave,
          }
      };
      setWorkflowsByCondition(updatedWorkflowsMaster);

      const workflowToSave: SavedWorkflow = { 
          id: activeCondition, 
          conditionId: activeCondition,
          nodes: currentNodesForSave, 
          edges: currentEdgesForSave, 
          timestamp: new Date().toISOString(), 
          version: (savedWorkflows.find(wf => wf.id === activeCondition)?.version || 0) + 1 
      };
      const updatedSavedWorkflows = savedWorkflows.filter(wf => wf.id !== activeCondition);
      updatedSavedWorkflows.push(workflowToSave);
      setSavedWorkflows(updatedSavedWorkflows);
      localStorage.setItem('savedWorkflows', JSON.stringify(updatedSavedWorkflows));
      localStorage.setItem('workflowsByCondition', JSON.stringify(updatedWorkflowsMaster)); 
      localStorage.setItem('workflowCompleted', 'true');
      setHasUnsavedChanges(false); 
      markStepCompleted(1); 
      toast({ title: "Workflow Saved", description: `Workflow for ${activeCondition} saved successfully.` });
  };

  const handleGenerateFiles = () => {
    if (hasUnsavedChanges) {
        toast({title: "Unsaved Changes", description: "Please save your workflow before generating files.", variant: "default"});
        return;
    }
    localStorage.setItem('hasGeneratedFiles', 'true');
    markStepCompleted(2);
    navigate("/workflow/image/generate");
  };

  const handleBackToUpload = () => {
    if (hasUnsavedChanges) {
        if (!confirm("You have unsaved changes. Are you sure you want to go back? Changes will be lost.")) {
            return;
        }
    }
    navigate("/workflow/image");
  };

  // Effect to compute panel elements from raw data
  useEffect(() => {
    if (!rawData || rawData.length === 0) return;
    
    const conditions: ElementItemType[] = [];
    const approvers: ElementItemType[] = [];
    
    rawData.forEach(item => {
      const conditionId = item["Condition Serial No."];
      
      Object.keys(item).filter(k => k.includes("_Metadata_Condition")).forEach(key => {
          if (item[key] && !conditions.some(c => c.name === item[key])) {
              conditions.push({ id: `${conditionId}_${key}_panel`, name: item[key], type: 'condition', description: `From: ${conditionId}` });
          }
      });
      
      Object.keys(item).filter(k => k.includes("Approver_Level_")).forEach(key => {
          if (item[key] && item[key].toLowerCase() !== 'requisition approved' && !approvers.some(a => a.name === item[key])) {
              approvers.push({ id: `${conditionId}_${key}_panel`, name: item[key], type: 'approver', description: `From: ${conditionId}` });
          }
      });
    });
    
    const uniqueConditions = Array.from(new Map(conditions.map(item => [item.name, item])).values());
    const uniqueApprovers = Array.from(new Map(approvers.map(item => [item.name, item])).values());

    setPanelElements({ conditions: uniqueConditions, approvers: uniqueApprovers });
  }, [rawData]);

  return (
    <ReactFlowProvider>
      <div className="h-screen flex flex-col bg-slate-100 text-sm">
        <div className="flex justify-between items-center p-2.5 bg-white border-b shadow-sm flex-wrap gap-2">
           <h1 className="text-lg font-semibold text-blue-700">Workflow Generator</h1>
          {conditionButtons.length > 0 && (
               <div className="flex items-center flex-grow mx-2">
                 <span className="text-xs text-slate-600 mr-2 font-medium">FLOW:</span>
                 <div className="flex space-x-1 bg-slate-200 p-0.5 rounded-md">
                   {conditionButtons.map(button => (
                     <Button
                       key={button.id}
                       variant={activeCondition === button.id ? "default" : "ghost"}
                       size="sm"
                       className={`px-2.5 h-6 text-xs rounded-sm transition-all duration-150 font-medium shadow-sm
                         ${activeCondition === button.id 
                           ? 'bg-blue-600 text-white hover:bg-blue-700' 
                           : 'text-slate-700 hover:bg-blue-100 hover:text-blue-600 bg-white' 
                         }`}
                       onClick={() => setActiveCondition(button.id)}
                     >
                       {button.label} 
                     </Button>
                   ))}
                 </div>
               </div>
           )}
            <div className="flex gap-2 items-center">
            <Button variant="outline" onClick={handleBackToUpload} size="sm" className="text-xs px-3 h-8 border-slate-300 hover:border-blue-500 hover:text-blue-600">
              <ChevronLeft className="h-3.5 w-3.5 mr-1.5" /> Back
            </Button>
            <Button 
              onClick={handleSaveWorkflow} 
              size="sm" 
              disabled={!activeCondition || !hasUnsavedChanges}
              className={`text-xs px-3 h-8 font-semibold ${hasUnsavedChanges ? 'bg-green-500 hover:bg-green-600' : 'bg-blue-500 hover:bg-blue-600'} text-white disabled:bg-slate-400 disabled:cursor-not-allowed`}
            >
              <Save className="h-3.5 w-3.5 mr-1.5" /> Save Workflow
            </Button>
            <Button 
              size="sm"
              className="bg-slate-700 hover:bg-slate-800 text-white text-xs px-3 h-8 font-semibold disabled:bg-slate-400 disabled:cursor-not-allowed"
              onClick={handleGenerateFiles}
              disabled={hasUnsavedChanges || !activeCondition}
            >
              Next <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </Button>
          </div>
        </div>
       
        <div className="flex flex-1 overflow-hidden">
          <div className="w-72 bg-white border-r overflow-y-auto flex-shrink-0 p-3 space-y-3 shadow-sm">
            <ElementPanel 
               onAddElement={handleAddElementRequest}
               elements={elementLibrary} 
               referenceImageUrl={referenceImageUrl} 
               selectedNode={selectedRfElement}
               onEditNode={handleEditSelectedNode}
               onDeleteNode={handleDeleteSelectedNode}
               onEditItem={handleEditPanelItem}
               onDeleteItem={handleDeletePanelItem}
            /> 
          </div>

          <div className="flex-1 flex flex-col overflow-hidden" ref={reactFlowWrapper}>
            <div className="bg-white border-b flex items-center px-2 text-xs">
              {['editor', 'preview'].map(tabName => (
                <button 
                  key={tabName}
                  className={`px-4 py-2 font-medium border-b-2 capitalize transition-colors duration-150 ease-in-out focus:outline-none 
                    ${activeTab === tabName 
                      ? 'border-blue-600 text-blue-700' 
                      : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-400'}`}
                  onClick={() => setActiveTab(tabName)}
                >
                  {tabName}
                </button>
              ))}
              {hasUnsavedChanges && activeTab === 'editor' && (
                  <span className="ml-auto mr-3 text-xs font-medium text-orange-600">
                      * Unsaved changes
                  </span>
              )}
            </div>

            <div className="flex-1 overflow-auto bg-slate-50">
              {activeTab === 'editor' && (
                <div className="h-full w-full">
                  {isLoading ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="flex flex-col items-center justify-center space-y-3">
                        <div className="w-12 h-12 border-4 border-blue-400 border-t-blue-600 rounded-full animate-spin"></div>
                        <span className="text-slate-600 font-medium">Loading Editor...</span>
                      </div>
                    </div>
                  ) : error ? (
                    <div className="flex items-center justify-center h-full p-6 text-center">
                      <div className="max-w-md p-6 bg-white rounded-lg shadow-md border border-red-200">
                        <div className="text-red-600 font-semibold mb-2">Error Loading Workflow</div>
                        <p className="text-slate-700">{error}</p>
                      </div>
                    </div>
                  ) : rfNodes.length === 0 && !isLoading && activeCondition ? (
                     <div className="flex items-center justify-center h-full p-6 text-center">
                       <div className="max-w-md p-6 bg-white rounded-lg shadow-md">
                         <p className="text-slate-600">Workflow for <span className="font-semibold text-blue-600">"{activeCondition}"</span> is empty.</p>
                         <p className="text-slate-500 mt-2">Drag elements from the library or use 'Add Element' buttons to build your workflow.</p>
                       </div>
                     </div>
                  ) : rfNodes.length === 0 && !isLoading && !activeCondition ? (
                      <div className="flex items-center justify-center h-full p-6 text-center">
                        <div className="max-w-md p-6 bg-white rounded-lg shadow-md">
                          <p className="text-slate-600">Select a flow to begin.</p>
                          <p className="text-slate-500 mt-2">Choose one of the available workflow conditions from the top bar.</p>
                        </div>
                      </div>
                  ): (
                    <WorkflowEditorCanvasWrapper
                        rfNodes={rfNodes}
                        rfEdges={rfEdges}
                        onNodesChange={onNodesChange}
                        onEdgesChange={onEdgesChange}
                        onConnect={onConnect}
                        handleNodeClick={handleNodeClick}
                        handlePaneClick={handlePaneClick}
                        handleNodeDragStop={handleNodeDragStop}
                        onDropCanvas={onDropCanvas}
                        onDragOverCanvas={onDragOverCanvas}
                        onCanvasInit={onCanvasInit}
                        onNodesDeleted={onNodesDeleted}
                        onEdgesDeleted={onEdgesDeleted}
                        onNodeDoubleClick={handleNodeDoubleClick}
                    />
                  )}
                </div>
              )}
             
              {activeTab === 'preview' && (
                <div className="p-6 space-y-4">
                  <h3 className="text-lg font-semibold text-slate-700 flex items-center">
                      <span>Saved Workflows</span>
                      <span className="ml-2 px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                        {savedWorkflows.length}
                      </span>
                  </h3>
                   {savedWorkflows.length === 0 ? (
                      <div className="p-8 border border-dashed border-slate-300 rounded-lg text-center">
                        <p className="text-slate-500 mb-2">No workflows saved yet</p>
                        <p className="text-slate-400 text-xs">Design your workflow in the editor tab and click Save</p>
                      </div>
                   ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                      {savedWorkflows.map(wf => (
                          <div 
                            key={wf.id} 
                            className="p-4 border rounded-lg bg-white shadow-sm hover:shadow-md transition-shadow cursor-pointer"
                            onClick={() => setActiveCondition(wf.conditionId || wf.id)}
                          >
                              <p className="font-semibold text-blue-700 text-sm mb-2">Flow: {wf.conditionId || wf.id}</p>
                              <div className="flex space-x-4 items-center mb-2 text-xs text-slate-600">
                                <span className="px-1.5 py-1 bg-slate-100 rounded">Nodes: {wf.nodes.length}</span>
                                <span className="px-1.5 py-1 bg-slate-100 rounded">Edges: {wf.edges.length}</span>
                              </div>
                              <p className="text-slate-400 text-xs">
                                  Saved: {wf.timestamp ? new Date(wf.timestamp).toLocaleString() : 'N/A'} 
                                  <span className="ml-1 px-1.5 py-0.5 bg-blue-50 text-blue-600 rounded-full text-xxs">v{wf.version}</span>
                              </p>
                          </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
       
        {showElementCreator && (
          <ElementCreator
            open={showElementCreator}
            onClose={() => {setShowElementCreator(false); setElementCreatorInitialData({}); setSelectedRfElement(null);}}
            onSave={handleElementSave}
            initialType={elementCreatorType}
            initialData={elementCreatorInitialData}
          />
        )}
      </div>
    </ReactFlowProvider>
  );
};

export default WorkflowDesign; 