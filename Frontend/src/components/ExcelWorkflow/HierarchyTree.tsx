import React, { useState, useEffect, useRef } from "react";
import { Plus, Minus, RefreshCw, Download, Maximize } from "lucide-react";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import TreeNode, { TreeNodeData } from "./TreeNode";
import html2canvas from "html2canvas";

interface HierarchyTreeProps {
  treeData?: any;
  onTreeChange?: (data: any) => void;
  searchQuery?: string;
}

// Function to convert the backend JSON format to our tree structure
const convertJsonToTree = (json: any, parentId = "root"): TreeNodeData[] => {
  if (!json) return [];

  return Object.entries(json).map(([key, value], index) => {
    const nodeId = `${parentId}-${index}`;

    if (Array.isArray(value)) {
      // This is a leaf node with users
      return {
        id: nodeId,
        label: key,
        children: [],
        users: value,
        expanded: true,
      };
    } else if (typeof value === "object") {
      // This is a parent node with children
      return {
        id: nodeId,
        label: key,
        children: convertJsonToTree(value, nodeId),
        expanded: true,
      };
    } else {
      // Fallback for unexpected data
      return {
        id: nodeId,
        label: key,
        children: [],
        expanded: true,
      };
    }
  });
};

// Sample tree data based on the provided JSON structure
const sampleTreeData: TreeNodeData = {
  id: "root",
  label: "Approval Workflow",
  expanded: true,
  children: []
};

// Function to search nodes recursively
const searchNodes = (node: TreeNodeData, query: string): boolean => {
  if (!query) return true;
  
  const lowerQuery = query.toLowerCase();
  
  // Check if the current node matches
  if (node.label.toLowerCase().includes(lowerQuery)) {
    return true;
  }
  
  // Check if any users match
  if (node.users && node.users.length > 0) {
    const userMatches = node.users.some(
      user => 
        user.label.toLowerCase().includes(lowerQuery) || 
        user.user.toLowerCase().includes(lowerQuery)
    );
    if (userMatches) return true;
  }
  
  // Check if any children match
  if (node.children && node.children.length > 0) {
    return node.children.some(child => searchNodes(child, query));
  }
  
  return false;
};

// Function to filter tree based on search query
const filterTree = (node: TreeNodeData, query: string): TreeNodeData | null => {
  if (!query) return node;
  
  // Clone the node to avoid mutating the original
  const newNode = { ...node };
  
  // If this node matches, keep it and all its children
  if (node.label.toLowerCase().includes(query.toLowerCase())) {
    return {
      ...newNode,
      expanded: true,
    };
  }
  
  // Check if any users match
  if (node.users && node.users.length > 0) {
    const userMatches = node.users.some(
      user => 
        user.label.toLowerCase().includes(query.toLowerCase()) || 
        user.user.toLowerCase().includes(query.toLowerCase())
    );
    if (userMatches) {
      return {
        ...newNode,
        expanded: true,
      };
    }
  }
  
  // If this node doesn't match, check its children
  if (node.children && node.children.length > 0) {
    const filteredChildren = node.children
      .map(child => filterTree(child, query))
      .filter(Boolean) as TreeNodeData[];
    
    // If any children match, keep this node with only the matching children
    if (filteredChildren.length > 0) {
      return {
        ...newNode,
        children: filteredChildren,
        expanded: true,
      };
    }
  }
  
  // If nothing matches, return null to filter out this node
  return null;
};

const HierarchyTree: React.FC<HierarchyTreeProps> = ({
  treeData = null,
  onTreeChange = () => {},
  searchQuery = "",
}) => {
  const [tree, setTree] = useState<TreeNodeData>(sampleTreeData);
  const [originalTree, setOriginalTree] = useState<TreeNodeData>(sampleTreeData);
  const [zoomLevel, setZoomLevel] = useState<number>(100);
  const [filteredTree, setFilteredTree] = useState<TreeNodeData | null>(tree);
  const treeContainerRef = useRef<HTMLDivElement>(null);

  // Update tree when treeData prop changes
  useEffect(() => {
    console.log("HierarchyTree receiving treeData:", treeData);
    if (treeData) {
      try {
        // Check if treeData is already in our format (has id, label, etc.)
        if (treeData.id && typeof treeData.label === 'string') {
          console.log("Tree data is already in the right format");
          setTree(treeData);
          setOriginalTree(JSON.parse(JSON.stringify(treeData))); // Deep copy for reset
        } else {
          // Convert from JSON format
          console.log("Converting tree data to hierarchical format");
          const convertedTree = {
            id: "root",
            label: "Approval Workflow",
            expanded: true,
            children: convertJsonToTree(treeData),
          };
          console.log("Converted tree structure:", convertedTree);
          setTree(convertedTree);
          setOriginalTree(JSON.parse(JSON.stringify(convertedTree))); // Deep copy
        }
      } catch (error) {
        console.error("Error processing tree data:", error);
        // Fallback to empty tree
        setTree(sampleTreeData);
        setOriginalTree(JSON.parse(JSON.stringify(sampleTreeData)));
      }
    } else {
      // If no tree data is provided, use sample tree
      setTree(sampleTreeData);
      setOriginalTree(JSON.parse(JSON.stringify(sampleTreeData)));
    }
  }, [treeData]);

  // Update filtered tree when search query changes
  useEffect(() => {
    if (!searchQuery) {
      setFilteredTree(tree);
    } else {
      const filtered = filterTree(tree, searchQuery);
      setFilteredTree(filtered || tree);
    }
  }, [searchQuery, tree]);

  const handleNodeToggle = (nodeId: string) => {
    const updateNodeExpanded = (node: TreeNodeData): TreeNodeData => {
      if (node.id === nodeId) {
        return { ...node, expanded: !node.expanded };
      }

      if (node.children && node.children.length > 0) {
        return {
          ...node,
          children: node.children.map(updateNodeExpanded),
        };
      }

      return node;
    };

    const updatedTree = updateNodeExpanded(tree);
    setTree(updatedTree);
    onTreeChange(updatedTree);
  };

  const handleNodeEdit = (
    nodeId: string, 
    newLabel: string, 
    users?: { user: string; label: string }[]
  ) => {
    const updateNode = (node: TreeNodeData): TreeNodeData => {
      if (node.id === nodeId) {
        const updatedNode = { ...node, label: newLabel };
        if (users !== undefined) {
          updatedNode.users = users;
        }
        return updatedNode;
      }

      if (node.children && node.children.length > 0) {
        return {
          ...node,
          children: node.children.map(updateNode),
        };
      }

      return node;
    };

    const updatedTree = updateNode(tree);
    setTree(updatedTree);
    onTreeChange(updatedTree);
  };

  const handleNodeDelete = (nodeId: string) => {
    // Don't allow deleting the root node
    if (nodeId === "root") return;
    
    const deleteNode = (node: TreeNodeData): TreeNodeData | null => {
      // If this is the node to delete, return null
      if (node.id === nodeId) {
        return null;
      }
      
      // If this node has children, recursively check them
      if (node.children && node.children.length > 0) {
        const updatedChildren = node.children
          .map(child => {
            // If this child is the one to delete, return null
            if (child.id === nodeId) {
              return null;
            }
            // Otherwise, recursively process this child
            return deleteNode(child);
          })
          .filter(Boolean) as TreeNodeData[]; // Remove null values
        
        return {
          ...node,
          children: updatedChildren,
        };
      }
      
      return node;
    };

    const updatedTree = deleteNode(tree);
    if (updatedTree) {
      setTree(updatedTree);
      onTreeChange(updatedTree);
    }
  };

  const handleAddChild = (parentId: string, label: string) => {
    const addChildNode = (node: TreeNodeData): TreeNodeData => {
      if (node.id === parentId) {
        const children = node.children || [];
        const newChildId = `${parentId}-${children.length}`;
        return {
          ...node,
          children: [
            ...children,
            {
              id: newChildId,
              label,
              children: [],
              expanded: true,
            },
          ],
        };
      }

      if (node.children && node.children.length > 0) {
        return {
          ...node,
          children: node.children.map(addChildNode),
        };
      }

      return node;
    };

    const updatedTree = addChildNode(tree);
    setTree(updatedTree);
    onTreeChange(updatedTree);
  };

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev + 10, 150));
  };

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev - 10, 50));
  };

  const handleResetTree = () => {
    // Reset tree to original state
    const resetTree = JSON.parse(JSON.stringify(originalTree)); // Deep copy
    setTree(resetTree);
    onTreeChange(resetTree);
  };

  const handleExpandAll = () => {
    // Recursively expand all nodes
    const expandAllNodes = (node: TreeNodeData): TreeNodeData => {
      return {
        ...node,
        expanded: true,
        children: node.children.map(expandAllNodes),
      };
    };
    
    const expandedTree = expandAllNodes(tree);
    setTree(expandedTree);
    onTreeChange(expandedTree);
  };

  const handleDownloadPNG = async () => {
    if (treeContainerRef.current) {
      try {
        // Set a temporary background color for the export
        const originalBackground = treeContainerRef.current.style.background;
        treeContainerRef.current.style.background = "white";
        
        const canvas = await html2canvas(treeContainerRef.current, {
          backgroundColor: "#ffffff",
          scale: 2, // Higher quality
          logging: false,
          useCORS: true,
        });
        
        // Reset background
        treeContainerRef.current.style.background = originalBackground;
        
        // Create download link
        const link = document.createElement("a");
        link.download = "approval-hierarchy-tree.png";
        link.href = canvas.toDataURL("image/png");
        link.click();
      } catch (error) {
        console.error("Error generating PNG:", error);
      }
    }
  };

  return (
    <Card className="p-4 bg-white w-full h-full overflow-auto">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Approval Hierarchy Tree</h3>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={handleExpandAll} title="Expand All Nodes">
            <Maximize size={16} className="mr-1" />
            <span className="hidden sm:inline">Expand All</span>
          </Button>
          <Button variant="outline" size="sm" onClick={handleDownloadPNG} title="Download as PNG">
            <Download size={16} className="mr-1" />
            <span className="hidden sm:inline">PNG</span>
          </Button>
          <Button variant="outline" size="sm" onClick={handleResetTree} title="Reset Tree">
            <RefreshCw size={16} className="mr-1" />
            <span className="hidden sm:inline">Reset</span>
          </Button>
          <Button variant="outline" size="sm" onClick={handleZoomOut}>
            <Minus size={16} />
          </Button>
          <span className="text-sm">{zoomLevel}%</span>
          <Button variant="outline" size="sm" onClick={handleZoomIn}>
            <Plus size={16} />
          </Button>
        </div>
      </div>

      <div
        ref={treeContainerRef}
        className="p-4 border rounded-md bg-gray-50 overflow-auto"
        style={{
          transform: `scale(${zoomLevel / 100})`,
          transformOrigin: "top left",
          minHeight: "500px",
        }}
      >
        {filteredTree && (
          <TreeNode
            node={filteredTree}
            onToggle={handleNodeToggle}
            onEdit={handleNodeEdit}
            onDelete={handleNodeDelete}
            onAddChild={handleAddChild}
            level={0}
          />
        )}
      </div>
    </Card>
  );
};

export default HierarchyTree;
