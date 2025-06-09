import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Search, RefreshCw, AlertCircle, Shuffle, Network, List, GitBranch, FolderTree, Minus, Plus } from "lucide-react";
import HierarchyTree from "./HierarchyTree";
import { Input } from "../ui/input";
import { useToast } from "@/components/ui/use-toast";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Pagination } from "../ui/pagination";
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue 
} from "../ui/select";

// Import React Flow
import ReactFlow, { 
  Background, 
  Controls, 
  Panel, 
  useNodesState, 
  useEdgesState, 
  MarkerType,
  Position,
  Handle
} from 'reactflow';
import 'reactflow/dist/style.css';
import { transformTreeData } from "@/services/api";

interface TreeTabProps {
  onPrevious?: () => void;
  onNext?: () => void;
  isProcessing?: boolean;
  treeData?: any;
  setIsProcessing?: (isProcessing: boolean) => void;
  setProcessingStage?: (stage: "extracting" | "validating" | "generating" | "complete" | "error") => void;
  setProcessingError?: (error: string) => void;
  onFilePathsReceived?: (paths: { mcw_file?: string; wcm_file?: string }) => void;
  projectId?: string;
}

// Custom node component for users
const UserNode = ({ data }: { data: any }) => (
  <div className="p-2 rounded-md border bg-white shadow-sm max-w-[200px] relative">
    <Handle
      type="target"
      position={Position.Top}
      style={{ background: '#555', width: '8px', height: '8px' }}
      id="target"
    />
    <div className="flex items-center gap-2">
      <div className="h-7 w-7 rounded-full bg-blue-100 flex items-center justify-center font-medium text-blue-800">
        {(data.label || "U").substring(0, 1).toUpperCase()}
      </div>
      <div className="overflow-hidden">
        <p className="font-medium text-sm truncate">{data.label || "User"}</p>
        <p className="text-gray-500 text-xs truncate">{data.role || data.user || "email@example.com"}</p>
      </div>
    </div>
  </div>
);

// Custom node component for path nodes
const PathNode = ({ data }: { data: any }) => (
  <div className="p-3 rounded-md border bg-white shadow-sm relative">
    <Handle
      type="target"
      position={Position.Top}
      style={{ background: '#555', width: '8px', height: '8px' }}
    />
    <div>{data.label}</div>
    <Handle
      type="source"
      position={Position.Bottom}
      style={{ background: '#555', width: '8px', height: '8px' }}
    />
  </div>
);

// Custom node component for workflow nodes
const WorkflowNode = ({ data }: { data: any }) => (
  <div className={`p-3 rounded-md border shadow-sm relative ${
    data.level === 0 
      ? 'bg-purple-50 border-purple-200' 
      : data.level === 1 
        ? 'bg-blue-50 border-blue-200'
        : data.level === 2
          ? 'bg-green-50 border-green-200'
          : 'bg-amber-50 border-amber-200'
  }`}>
    <Handle
      type="target"
      position={Position.Top}
      style={{ background: '#555', width: '8px', height: '8px' }}
    />
    <div className="font-medium text-sm">{data.label}</div>
    {data.userCount > 0 && (
      <div className="text-xs text-gray-500 mt-1">
        Users: {data.userCount}
      </div>
    )}
    <Handle
      type="source"
      position={Position.Bottom}
      style={{ background: '#555', width: '8px', height: '8px' }}
    />
  </div>
);

// Custom node types
const nodeTypes = {
  userNode: UserNode,
  pathNode: PathNode,
  workflowNode: WorkflowNode,
};

// Component for Graph View
const GraphView: React.FC<{ treeData: any }> = ({ treeData }) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [isReady, setIsReady] = useState(false);

  // Default edge options for better visibility
  const defaultEdgeOptions = {
    style: { strokeWidth: 2 },
    markerEnd: {
      type: MarkerType.ArrowClosed,
    },
    zIndex: 1000, // Ensure edges appear above nodes
  };

  // Function to convert tree data to nodes and edges
  const convertTreeToFlow = useCallback((treeData: any) => {
    if (!treeData) return { nodes: [], edges: [] };
    
    const flowNodes: any[] = [];
    const flowEdges: any[] = [];
    let nodeCount = 0;
    
    // Process nodes recursively
    const processNode = (node: any, parentId: string | null = null, level = 0, position = { x: 0, y: 0 }, index = 0, siblingCount = 1) => {
      if (!node) return null;
      
      const nodeId = node.id?.toString() || `node-${Math.random().toString(36).substring(2, 9)}`;
      const label = node.label || "Unnamed Node";
      
      // Calculate position based on level and siblings
      const horizontalGap = 300; // Increased from 250 for more horizontal space
      const verticalGap = 200;   // Increased from 150 for more vertical space
      
      // For root node, center it
      let xPos = position.x;
      // For children, distribute them horizontally
      if (level > 0) {
        // Distribute siblings evenly
        const totalWidth = (siblingCount - 1) * horizontalGap;
        const startX = position.x - totalWidth / 2;
        xPos = startX + index * horizontalGap;
      }
      
      const yPos = level * verticalGap;
      
      // Node style based on level
      let style: any = { width: 180 };
      let nodeType = 'default';
      
      if (level === 0) {
        style = { ...style, background: 'rgba(147, 51, 234, 0.1)', borderColor: 'rgba(147, 51, 234, 0.3)', borderWidth: 2 };
      } else if (level === 1) {
        style = { ...style, background: 'rgba(59, 130, 246, 0.1)', borderColor: 'rgba(59, 130, 246, 0.3)', borderWidth: 2 };
      } else if (level === 2) {
        style = { ...style, background: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.3)', borderWidth: 2 };
      } else {
        style = { ...style, background: 'rgba(245, 158, 11, 0.1)', borderColor: 'rgba(245, 158, 11, 0.3)', borderWidth: 1 };
      }

      // Add node
      const newNode = {
        id: nodeId,
        data: { 
          label, 
          userCount: node.users?.length || 0,
          level,
        },
        position: { x: xPos, y: yPos },
        style,
        type: 'workflowNode',
      };
      
      flowNodes.push(newNode);
      nodeCount++;
      
      // Add edge from parent to this node
      if (parentId) {
        flowEdges.push({
          id: `e-${parentId}-${nodeId}`,
          source: parentId,
          target: nodeId,
          type: 'smoothstep',
          animated: false,
          markerEnd: {
            type: MarkerType.ArrowClosed,
            width: 15,
            height: 15,
          },
          style: { stroke: '#94a3b8' },
        });
      }
      
      // Process children
      if (node.children && node.children.length > 0) {
        node.children.forEach((child: any, idx: number) => {
          processNode(
            child, 
            nodeId, 
            level + 1, 
            { x: xPos, y: yPos + verticalGap }, 
            idx, 
            node.children.length
          );
        });
      }
      
      // Add user nodes if any
      if (node.users && node.users.length > 0) {
        const usersPerRow = 3;
        const userHorizontalGap = 200; // Increased from 150
        const userVerticalGap = 100;   // Increased from 80
        const parentUserVerticalOffset = 150; // Increased from 100
        
        node.users.forEach((user: any, userIdx: number) => {
          const row = Math.floor(userIdx / usersPerRow);
          const col = userIdx % usersPerRow;
          const userId = `user-${nodeId}-${userIdx}`;
          
          // Center the user grid below the parent node
          const totalUsersWidth = (Math.min(usersPerRow, node.users.length) - 1) * userHorizontalGap;
          const startX = xPos - totalUsersWidth / 2;
          const userX = startX + col * userHorizontalGap;
          const userY = yPos + parentUserVerticalOffset + row * userVerticalGap;
          
          flowNodes.push({
            id: userId,
            data: { 
              label: user.label,
              role: user.role,
              user: user.user
            },
            position: { x: userX, y: userY },
            type: 'userNode',
            sourcePosition: Position.Bottom,
            targetPosition: Position.Top,
          });
          
          // Add edge from node to user
          flowEdges.push({
            id: `e-${nodeId}-${userId}`,
            source: nodeId,
            target: userId,
            type: 'straight',
            animated: true,
            style: { stroke: '#cbd5e1', strokeWidth: 2 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 12,
              height: 12,
            },
          });
        });
      }
    };
    
    // Start processing from root node
    processNode(treeData);
    
    return { nodes: flowNodes, edges: flowEdges };
  }, []);
  
  // Update nodes and edges when tree data changes
  useEffect(() => {
    if (treeData) {
      const { nodes: newNodes, edges: newEdges } = convertTreeToFlow(treeData);
      setNodes(newNodes);
      setEdges(newEdges);
      setIsReady(true);
    } else {
      setNodes([]);
      setEdges([]);
      setIsReady(true);
    }
  }, [treeData, convertTreeToFlow, setNodes, setEdges]);
  
  // If no tree data or processing not yet complete
  if (!isReady || !treeData) {
    return (
      <div className="flex items-center justify-center h-[500px]">
        <div className="text-center">
          <Network className="w-16 h-16 mx-auto text-gray-400" />
          <p className="mt-4 text-gray-500">Loading graph visualization...</p>
        </div>
      </div>
    );
  }
  
  // If no nodes to display
  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-[500px]">
        <div className="text-center">
          <Network className="w-16 h-16 mx-auto text-gray-400" />
          <p className="mt-4 text-gray-500">No tree structure to visualize</p>
          <p className="text-sm text-gray-400 mt-2">Create nodes in the Hierarchical view first</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[500px] border rounded-lg bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        defaultEdgeOptions={defaultEdgeOptions}
        connectionLineStyle={{ stroke: '#ddd', strokeWidth: 2 }}
        elementsSelectable={true}
        nodesConnectable={false}
      >
        <Background />
        <Controls />
      </ReactFlow>
      <div className="text-center text-xs text-gray-500 p-2 border-t">
        <p>Interactive graph view. Edit nodes in the Hierarchical view.</p>
      </div>
    </div>
  );
};

// Component for Individual Condition View
const IndividualConditionView: React.FC<{ treeData: any }> = ({ treeData }) => {
  const [conditions, setConditions] = useState<any[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState("");
  const [subView, setSubView] = useState<"list" | "flow">("list");
  const [selectedCondition, setSelectedCondition] = useState<any>(null);
  
  // For debugging
  useEffect(() => {
    console.log("Condition View received tree data:", treeData);
  }, [treeData]);
  
  useEffect(() => {
    if (treeData) {
      // Flatten the tree to get individual conditions
      const flattenedConditions: any[] = [];
      
      const flattenTree = (node: any, path: string[] = [], level: number = 0) => {
        if (!node) {
          console.log("Attempted to flatten null node in ConditionView");
          return;
        }
        
        // Skip adding "Approval Workflow" (root node) to the path
        const currentPath = level === 0 ? [] : [...path, node.label || "Unnamed Node"];
        
        if (node.users && node.users.length > 0) {
          // This is a condition with users
          flattenedConditions.push({
            id: node.id || `node-${Math.random()}`,
            path: currentPath,
            condition: currentPath.join(' > '),
            users: node.users,
            level // Track the level for styling
          });
        }
        
        if (node.children && node.children.length > 0) {
          // If this is the root node, pass an empty path to children
          const nextPath = level === 0 ? [] : currentPath;
          node.children.forEach((child: any) => flattenTree(child, nextPath, level + 1));
        }
      };
      
      try {
        flattenTree(treeData);
        console.log("Flattened conditions:", flattenedConditions);
        setConditions(flattenedConditions);
      } catch (error) {
        console.error("Error flattening tree:", error);
        setConditions([]);
      }
    } else {
      setConditions([]);
    }
  }, [treeData]);
  
  // Filter conditions based on search query
  const filteredConditions = conditions.filter(condition => 
    condition.condition.toLowerCase().includes(searchQuery.toLowerCase()) ||
    condition.users.some((user: any) => 
      (user.label || "").toLowerCase().includes(searchQuery.toLowerCase()) ||
      (user.user || "").toLowerCase().includes(searchQuery.toLowerCase())
    )
  );
  
  // Calculate pagination
  const totalPages = Math.ceil(filteredConditions.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedConditions = filteredConditions.slice(startIndex, startIndex + itemsPerPage);
  
  // Function to get background color based on condition level
  const getConditionColor = (level: number) => {
    const colors = [
      "bg-blue-50 border-blue-200",
      "bg-purple-50 border-purple-200",
      "bg-green-50 border-green-200",
      "bg-amber-50 border-amber-200",
      "bg-red-50 border-red-200",
    ];
    return colors[level % colors.length];
  };

  // Flow View Component
  const ConditionFlowView: React.FC<{ condition?: any }> = ({ condition }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);

    // Default edge options for better visibility
    const defaultEdgeOptions = {
      style: { strokeWidth: 2 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
      },
      zIndex: 1000, // Ensure edges appear above nodes
    };

    useEffect(() => {
      if (condition) {
        const flowNodes: any[] = [];
        const flowEdges: any[] = [];
        const path = condition.path;
        
        // Create nodes for each path item
        path.forEach((item: string, index: number) => {
          const nodeId = `path-${index}`;
          flowNodes.push({
            id: nodeId,
            data: { label: item },
            position: { x: index * 300, y: 100 }, // Increased from 250
            type: 'pathNode',
            style: {
              background: '#fff',
              borderRadius: '8px',
              width: 180,
            }
          });

          // Create edge to next path item
          if (index < path.length - 1) {
            flowEdges.push({
              id: `edge-${index}`,
              source: nodeId,
              target: `path-${index + 1}`,
              type: 'smoothstep',
              animated: true,
              style: { stroke: '#94a3b8' },
              markerEnd: {
                type: MarkerType.ArrowClosed,
                width: 20,
                height: 20,
              },
            });
          }
        });

        // Add user nodes in a grid layout
        const usersPerRow = 3;
        const userHorizontalGap = 200; // Increased from 150
        const userVerticalGap = 120;   // Increased from 80
        const pathUserVerticalOffset = 160; // Increased from 120
        const lastPathNodeId = `path-${path.length - 1}`;
        let lastPathNodeX = 0;
        const lastPathNode = flowNodes.find(n => n.id === lastPathNodeId);
        if (lastPathNode) {
          lastPathNodeX = lastPathNode.position.x;
        }
        
        condition.users.forEach((user: any, userIndex: number) => {
          const row = Math.floor(userIndex / usersPerRow);
          const col = userIndex % usersPerRow;
          const userId = `user-${userIndex}`;
          
          // Center the user grid below the last path node
          const totalUsersWidth = (Math.min(usersPerRow, condition.users.length) - 1) * userHorizontalGap;
          const startX = lastPathNodeX - totalUsersWidth / 2;
          const userX = startX + col * userHorizontalGap;
          const userY = 100 + pathUserVerticalOffset + row * userVerticalGap; // Start below path line
          
          flowNodes.push({
            id: userId,
            data: { 
              label: user.label,
              role: user.role,
              user: user.user
            },
            position: { x: userX, y: userY },
            type: 'userNode',
            sourcePosition: Position.Bottom,
            targetPosition: Position.Top,
          });

          // Connect user to the last path node
          flowEdges.push({
            id: `edge-to-user-${userIndex}`,
            source: lastPathNodeId,
            target: userId,
            type: 'straight',
            animated: true,
            style: { stroke: '#cbd5e1', strokeWidth: 2 },
            markerEnd: {
              type: MarkerType.ArrowClosed,
              width: 12,
              height: 12,
            },
          });
        });

        setNodes(flowNodes);
        setEdges(flowEdges);
      }
    }, [condition]);

    if (!condition) {
      return (
        <div className="flex items-center justify-center h-[400px] flex-col gap-3 text-gray-500">
          <Network className="w-16 h-16 text-gray-300" />
          <p>Select a condition to view its flow</p>
        </div>
      );
    }

    return (
      <div className="h-[500px] border rounded-lg bg-white">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          defaultEdgeOptions={defaultEdgeOptions}
          connectionLineStyle={{ stroke: '#ddd', strokeWidth: 2 }}
          elementsSelectable={true}
          nodesConnectable={false}
        >
          <Background />
          <Controls />
        </ReactFlow>
      </div>
    );
  };
  
  // Check if there are any conditions
  const hasConditions = conditions.length > 0;
  
  return (
    <div className="p-4 border rounded-lg bg-white h-[500px] overflow-auto">
      {hasConditions ? (
        <>
          <div className="mb-6">
            <div className="flex gap-4 items-start">
              <div className="flex-1">
                <h2 className="text-lg font-semibold mb-2 text-gray-800">Approval Conditions</h2>
                <p className="text-sm text-gray-500">View and manage your approval workflow conditions</p>
              </div>
              <div className="flex gap-3">
                <div className="w-64">
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                      <Search className="h-4 w-4 text-gray-400" />
                    </div>
                    <Input
                      type="search"
                      placeholder="Search conditions or users..."
                      className="pl-10"
                      value={searchQuery}
                      onChange={(e) => {
                        setSearchQuery(e.target.value);
                        setCurrentPage(1);
                      }}
                    />
                  </div>
                </div>
                <Select
                  value={itemsPerPage.toString()}
                  onValueChange={(value) => {
                    setItemsPerPage(parseInt(value));
                    setCurrentPage(1);
                  }}
                >
                  <SelectTrigger className="w-[130px]">
                    <SelectValue placeholder="10 per page" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="5">5 per page</SelectItem>
                    <SelectItem value="10">10 per page</SelectItem>
                    <SelectItem value="20">20 per page</SelectItem>
                    <SelectItem value="50">50 per page</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          {subView === "list" ? (
            <div>
              {paginatedConditions.length > 0 ? (
                <div className="space-y-4">
                  {paginatedConditions.map((condition) => (
                    <div 
                      key={condition.id} 
                      className={`group relative overflow-hidden rounded-lg border bg-white transition-all duration-200 hover:shadow-lg ${getConditionColor(condition.level)}`}
                    >
                      <div className="p-5">
                        {/* Path Header */}
                        <div className="flex items-start justify-between mb-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <GitBranch className="h-4 w-4 text-gray-500" />
                              <h3 className="font-medium text-gray-900">Condition Path</h3>
                            </div>
                            {condition.path.length > 0 ? (
                              <div className="flex flex-wrap items-center gap-2">
                                {condition.path.map((pathItem: string, pathIndex: number) => (
                                  <React.Fragment key={pathIndex}>
                                    {pathIndex > 0 && (
                                      <svg className="h-4 w-4 text-gray-400 flex-shrink-0" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M6 12L10 8L6 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                                      </svg>
                                    )}
                                    <div 
                                      className={`
                                        px-2.5 py-1 rounded-full text-sm font-medium
                                        ${pathIndex === condition.path.length - 1 
                                          ? 'bg-primary text-primary-foreground' 
                                          : 'bg-gray-100 text-gray-700'}
                                      `}
                                    >
                                      {pathItem}
                                    </div>
                                  </React.Fragment>
                                ))}
                              </div>
                            ) : (
                              <div className="text-sm text-gray-500 italic">Root level condition</div>
                            )}
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                            onClick={() => {
                              setSelectedCondition(condition);
                              setSubView("flow");
                            }}
                          >
                            <Network className="w-4 h-4 mr-2" />
                            View Flow
                          </Button>
                        </div>

                        {/* Users Grid */}
                        <div className="mt-4">
                          <div className="flex items-center gap-2 mb-3">
                            <svg className="w-4 h-4 text-gray-500" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                              <circle cx="12" cy="7" r="4"></circle>
                            </svg>
                            <h4 className="font-medium text-gray-700">
                              Assigned Users <span className="text-xs text-gray-500 font-normal">({condition.users.length})</span>
                            </h4>
                          </div>
                          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                            {condition.users.map((user: any, index: number) => (
                              <div 
                                key={index} 
                                className="flex items-center gap-3 bg-white/50 p-3 rounded-lg border border-gray-100 hover:border-gray-200 transition-colors"
                              >
                                <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center font-medium text-blue-800">
                                  {(user.label || "U").substring(0, 1).toUpperCase()}
                                </div>
                                <div className="min-w-0">
                                  <p className="font-medium text-gray-900 text-sm truncate">{user.label || "Unnamed User"}</p>
                                  <p className="text-gray-500 text-xs truncate">{user.user || "No email"}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}

                  {totalPages > 1 && (
                    <div className="flex items-center justify-between pt-4 mt-6 border-t">
                      <p className="text-sm text-gray-500">
                        Showing <span className="font-medium">{startIndex + 1}-{Math.min(startIndex + itemsPerPage, filteredConditions.length)}</span> of <span className="font-medium">{filteredConditions.length}</span> conditions
                      </p>
                      
                      <div className="flex items-center gap-2">
                        <Button 
                          variant="outline" 
                          size="sm"
                          className="h-8 w-8 p-0"
                          disabled={currentPage === 1}
                          onClick={() => setCurrentPage(1)}
                        >
                          «
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          className="h-8 w-8 p-0"
                          disabled={currentPage === 1}
                          onClick={() => setCurrentPage(currentPage - 1)}
                        >
                          ‹
                        </Button>
                        
                        <div className="flex items-center gap-1">
                          {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                            let pageNumber;
                            if (totalPages <= 5) {
                              pageNumber = i + 1;
                            } else if (currentPage <= 3) {
                              pageNumber = i + 1;
                            } else if (currentPage >= totalPages - 2) {
                              pageNumber = totalPages - 4 + i;
                            } else {
                              pageNumber = currentPage - 2 + i;
                            }
                            
                            return (
                              <Button 
                                key={i}
                                variant={currentPage === pageNumber ? "default" : "outline"}
                                size="sm"
                                className="h-8 w-8 p-0"
                                onClick={() => setCurrentPage(pageNumber)}
                              >
                                {pageNumber}
                              </Button>
                            );
                          })}
                        </div>
                        
                        <Button 
                          variant="outline" 
                          size="sm"
                          className="h-8 w-8 p-0"
                          disabled={currentPage === totalPages}
                          onClick={() => setCurrentPage(currentPage + 1)}
                        >
                          ›
                        </Button>
                        <Button 
                          variant="outline" 
                          size="sm"
                          className="h-8 w-8 p-0"
                          disabled={currentPage === totalPages}
                          onClick={() => setCurrentPage(totalPages)}
                        >
                          »
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center h-[400px] flex-col gap-3 text-gray-500">
                  <Search className="w-12 h-12 text-gray-300" />
                  <p className="text-lg font-medium">No matching conditions found</p>
                  <p className="text-sm text-gray-400">Try adjusting your search terms</p>
                  {searchQuery && (
                    <Button variant="outline" size="sm" onClick={() => setSearchQuery("")}>
                      Clear search
                    </Button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="relative">
              {selectedCondition && (
                <div className="mb-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSubView("list");
                      setSelectedCondition(null);
                    }}
                    className="mb-4"
                  >
                    <List className="w-4 h-4 mr-2" />
                    Back to Conditions
                  </Button>
                  <div className="flex items-center gap-2 px-4 py-2 bg-gray-50 rounded-lg border">
                    <GitBranch className="w-4 h-4 text-gray-500" />
                    <span className="text-sm text-gray-600">
                      Viewing flow for: <span className="font-medium text-gray-900">{selectedCondition.condition}</span>
                    </span>
                  </div>
                </div>
              )}
              <ConditionFlowView condition={selectedCondition} />
            </div>
          )}
        </>
      ) : (
        <div className="flex items-center justify-center h-[400px] flex-col gap-3 text-gray-500">
          <List className="w-16 h-16 text-gray-300" />
          <p className="text-lg font-medium">No conditions available</p>
          <p className="text-sm text-gray-400 max-w-md text-center">
            Create nodes with users in the hierarchical view first to see conditions here
          </p>
        </div>
      )}
    </div>
  );
};

const TreeTab: React.FC<TreeTabProps> = ({
  onPrevious = () => {},
  onNext = () => {},
  isProcessing = false,
  treeData = null,
  setIsProcessing = () => {},
  setProcessingStage = () => {},
  setProcessingError = () => {},
  onFilePathsReceived = () => {},
  projectId = "",
}) => {
  const { toast } = useToast();
  const [activeView, setActiveView] = useState<string>("hierarchical");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [updatedTreeData, setUpdatedTreeData] = useState<any>(null);
  const [isValid, setIsValid] = useState(true);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Initialize with a default tree structure if none provided
  useEffect(() => {
    // Initialize with a default tree or use the provided treeData
    if (treeData) {
      // If treeData is provided externally, use it
      setUpdatedTreeData(treeData);
      validateTreeData(treeData);
    } else if (!updatedTreeData) {
      // If no tree data at all, initialize with a default structure
      const defaultTree = {
        id: "root",
        label: "Approval Workflow",
        expanded: true,
        children: []
      };
      
      setUpdatedTreeData(defaultTree);
      validateTreeData(defaultTree);
    }
  }, [treeData]);

  const handleNodeClick = (node: any) => {
    setSelectedNodeId(node.id);
  };

  const handleTreeChange = (data: any) => {
    console.log("Tree data updated:", data);
    setUpdatedTreeData(data);
    validateTreeData(data);
  };

  // Validate tree data
  const validateTreeData = (data: any = null) => {
    const treeToValidate = data || updatedTreeData || treeData;
    const errors: string[] = [];

    // Check if tree data exists
    if (!treeToValidate) {
      errors.push("No tree data available");
      setIsValid(false);
      setValidationErrors(errors);
      return false;
    }

    // Check if tree is empty (only root node)
    if (isTreeEmpty(treeToValidate)) {
      errors.push("Tree is empty.");
      setIsValid(false);
      setValidationErrors(errors);
      return false;
    }

    // Check if tree has at least one user assigned
    if (!hasUsers(treeToValidate)) {
      errors.push("Tree must have at least one node with assigned users");
      setIsValid(false);
      setValidationErrors(errors);
      return false;
    }

    setValidationErrors(errors);
    setIsValid(errors.length === 0);
    return errors.length === 0;
  };

  // Check if tree is empty (only root node)
  const isTreeEmpty = (node: any): boolean => {
    // For hierarchical tree format
    if (node.id && node.children) {
      // If it's the root node and has no children or only empty children
      if (node.id === 'root' && (!node.children || node.children.length === 0)) {
        return true;
      }
    }
    
    // For nested object format
    if (typeof node === 'object' && Object.keys(node).length === 0) {
      return true;
    }
    
    return false;
  };

  // Check if tree has any users assigned
  const hasUsers = (node: any): boolean => {
    // For hierarchical tree format
    if (node.id && node.children) {
      // Check if current node has users
      if (node.users && node.users.length > 0) {
        return true;
      }
      
      // Check children recursively
      if (node.children && node.children.length > 0) {
        return node.children.some((child: any) => hasUsers(child));
      }
      
      return false;
    }
    
    // For nested object format
    if (typeof node === 'object') {
      // Check if any leaf nodes have user arrays
      for (const key in node) {
        const value = node[key];
        
        // If value is an array, it might be a user array
        if (Array.isArray(value) && value.length > 0) {
          // Check if it's a user array (has objects with 'user' property)
          if (value.some((item: any) => item.user)) {
            return true;
          }
        }
        
        // If value is an object, recurse
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
          if (hasUsers(value)) {
            return true;
          }
        }
      }
    }
    
    return false;
  };

  // Effect to validate tree data when it changes
  useEffect(() => {
    if (treeData) {
      validateTreeData();
    }
  }, [treeData]);

  // Transform hierarchical tree data to nested object format
  const transformToNestedFormat = (treeData: any): any => {
    // If treeData is already in nested format or null, return as is
    if (!treeData || !treeData.id || !treeData.children) {
      return treeData;
    }

    // Recursive function to process nodes at any level
    const processNode = (node: any): any => {
      // If this is a leaf node with users, return the users array
      if (node.users && node.users.length > 0) {
        return node.users.map((user: any) => ({
          label: user.label,
          user: user.user
        }));
      }
      
      // If this is a leaf node without users or children, return an empty array
      if (!node.children || node.children.length === 0) {
        return [];
      }
      
      // For non-leaf nodes, process children and return an object
      const result: any = {};
      
      node.children.forEach((child: any) => {
        // If this is a leaf node with users, store the users array
        if (child.users && child.users.length > 0) {
          result[child.label] = child.users.map((user: any) => ({
            label: user.label,
            user: user.user
          }));
        } else if (!child.children || child.children.length === 0) {
          // If this is a leaf node without users, store an empty array
          result[child.label] = [];
        } else {
          // For non-leaf nodes, recursively process children
          result[child.label] = processNode(child);
        }
      });
      
      return result;
    };
    
    // Start with the root node's children
    const result: any = {};
    
    if (treeData.children && treeData.children.length > 0) {
      treeData.children.forEach((child: any) => {
        result[child.label] = processNode(child);
      });
    }
    
    return result;
  };

  const handleTransformClick = async () => {
    // Validate tree data before proceeding
    if (!validateTreeData()) {
      return;
    }

    try {
      setIsProcessing(true);
      setProcessingStage("generating");

      // Log the input tree data for debugging
      console.log("Input tree data:", JSON.stringify(updatedTreeData || treeData, null, 2));

      // Transform tree data to nested format if it's in hierarchical format
      const dataToSend = transformToNestedFormat(updatedTreeData || treeData);
      
      // Debug log to check the transformed data
      console.log("Transformed tree data:", JSON.stringify(dataToSend, null, 2));

      // Use the centralized API function
      const data = await transformTreeData(dataToSend, projectId);
      
      // Pass file paths to parent component
      if (data.file_paths) {
        // Let the parent component handle processing state and transitions
        onFilePathsReceived(data.file_paths);
      }
      
      // Let parent component handle the timing for animation and stage transitions
      // Don't manually set isProcessing to false or call onNext() here
      
    } catch (error) {
      console.error('Error transforming data:', error);
      
      // Extract error message
      const errorMessage = error instanceof Error ? error.message : "Failed to transform data";
      
      // Set processing to error stage with error message
      setProcessingStage("error");
      setProcessingError(errorMessage);
      
      // Show error message
      toast({
        title: "Error",
        description: errorMessage.split('\n').map((line, i) => (
          <span key={i}>
            {line}
            {i < errorMessage.split('\n').length - 1 && <br />}
          </span>
        )),
        variant: "destructive",
        duration: 5000,
      });
    }
  };

  return (
    <div className="w-full h-full p-6 bg-white rounded-lg shadow-sm flex flex-col">
      <Tabs value={activeView} onValueChange={setActiveView} className="w-full">
        <div className="flex justify-between items-center mb-4">
          <TabsList>
            <TabsTrigger value="hierarchical" className="flex items-center gap-1">
              <GitBranch className="h-4 w-4" />
              <span>Hierarchical</span>
            </TabsTrigger>
            <TabsTrigger value="graph" className="flex items-center gap-1">
              <Network className="h-4 w-4" />
              <span>Graph</span>
            </TabsTrigger>
            <TabsTrigger value="conditions" className="flex items-center gap-1">
              <List className="h-4 w-4" />
              <span>Conditions</span>
            </TabsTrigger>
          </TabsList>
          
          {/* Only show search for Hierarchical view */}
          {activeView === "hierarchical" && (
            <div className="relative">
              <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                <Search className="h-4 w-4 text-gray-400" />
              </div>
              <Input
                type="search"
                placeholder="Search nodes..."
                className="pl-10 w-64"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
          )}
        </div>

        <TabsContent value="hierarchical" className="mt-0">
          <div className="mb-4">
            <div className="flex-1 min-h-[600px]">
              <HierarchyTree 
                searchQuery={searchQuery} 
                treeData={updatedTreeData || treeData}
                onTreeChange={handleTreeChange}
              />
            </div>
          </div>
        </TabsContent>
        
        <TabsContent value="graph" className="mt-0">
          <div className="border-t pt-4 relative">
            {/* Add centered note inside the tab */}
            <div className="flex justify-center mb-4">
              <div className="inline-flex items-center px-3 py-1 rounded-full text-xs text-gray-500 border border-gray-100 bg-gray-50/80">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5 text-gray-400">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="16" x2="12" y2="12"></line>
                  <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                All edits must be made in the Hierarchical view
              </div>
            </div>
            
            <GraphView key="graph-view" treeData={updatedTreeData || treeData} />
          </div>
        </TabsContent>
        
        <TabsContent value="conditions" className="mt-0">
          <div className="border-t pt-4 relative">
            {/* Add centered note inside the tab */}
            <div className="flex justify-center mb-4">
              <div className="inline-flex items-center px-3 py-1 rounded-full text-xs text-gray-500 border border-gray-100 bg-gray-50/80">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="mr-1.5 text-gray-400">
                  <circle cx="12" cy="12" r="10"></circle>
                  <line x1="12" y1="16" x2="12" y2="12"></line>
                  <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                All edits must be made in the Hierarchical view
              </div>
            </div>
            
            <IndividualConditionView key="conditions-view" treeData={updatedTreeData || treeData} />
          </div>
        </TabsContent>
      </Tabs>

      <div className="mt-auto pt-6 border-t flex justify-between">
        {/* Back button removed as requested */}
        <div>
          <Button
            onClick={onPrevious}
            variant="outline"
            className="flex items-center gap-2"
            disabled={isProcessing}
          >
            Back to Validation
          </Button>
        </div> {/* Empty div to maintain flex spacing */}

        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <div>
                <Button
                  onClick={handleTransformClick}
                  className="flex items-center gap-2"
                  disabled={isProcessing || !isValid}
                >
                  {isProcessing ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      Processing...
                    </>
                  ) : (
                    <>
                      {!isValid && (
                        <AlertCircle className="mr-2 h-4 w-4 text-yellow-500" />
                      )}
                      <Shuffle className="h-4 w-4" />
                      Transform
                    </>
                  )}
                </Button>
              </div>
            </TooltipTrigger>
            {!isValid && !isProcessing && (
              <TooltipContent>
                <div className="max-w-xs">
                  <p className="font-semibold mb-1">Please fix the following issues:</p>
                  <ul className="list-disc pl-4 text-sm">
                    {validationErrors.map((error, index) => (
                      <li key={index}>{error}</li>
                    ))}
                  </ul>
                </div>
              </TooltipContent>
            )}
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  );
};

export default TreeTab;
