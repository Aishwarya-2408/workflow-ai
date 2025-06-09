import React from 'react';
import { Button } from "@/components/ui/button";
// import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"; // Removed as not used
import { PlusCircle, Zap, UserCheck, Edit3, Trash2, Info } from 'lucide-react';
import { Node } from 'reactflow'; // Import Node type

// Assuming AppNode is defined elsewhere, but for ElementPanel, Node from reactflow is sufficient for selectedNode prop typing
interface CustomNodeData {
  label: string;
  nodeType: "start" | "end" | "task" | "condition" | "approver" | "input";
  // Add other properties from your AppNode data structure if needed for display
}

type AppNode = Node<CustomNodeData>; // Use this if selectedNode is specifically your AppNode type

interface ElementItemType {
  id: string;
  name: string;
  type: 'condition' | 'approver';
  description: string;
}

interface ElementPanelProps {
  onAddElement: (type: 'condition' | 'approver') => void;
  elements?: {
    conditions: ElementItemType[];
    approvers: ElementItemType[];
  };
  referenceImageUrl?: string;
  selectedNode: AppNode | null; // Prop for the currently selected node from canvas
  onEditNode: (node: AppNode) => void; // Handler to initiate editing of the selected node
  onDeleteNode: (nodeId: string) => void; // Handler to delete the selected node
  onEditItem: (item: ElementItemType) => void;
  onDeleteItem: (id: string, name: string) => void;
}

const addElements = [
  { id: 'add-condition', name: 'Add Condition', type: 'condition' as 'condition' | 'approver', icon: <Zap className="h-4 w-4 mr-2 text-blue-500" /> }, // Cast type here
  { id: 'add-approver', name: 'Add Approver', type: 'approver' as 'condition' | 'approver', icon: <UserCheck className="h-4 w-4 mr-2 text-blue-500" /> }, // Cast type here
];

// Draw Connections section will be removed
// const drawConnections = [
//   { id: 'one-way', name: 'One-Way', type: 'one-way', icon: <ArrowRightLeft className="h-4 w-4 mr-2 transform rotate-90" /> },
//   { id: 'two-way', name: 'Two-Way', type: 'two-way', icon: <Maximize className="h-4 w-4 mr-2" /> },
// ];

const ElementPanel: React.FC<ElementPanelProps> = ({ 
    onAddElement, 
    // onDrawConnection, // No longer needed as prop if section is removed
    elements = { conditions: [], approvers: [] },
    referenceImageUrl,
    selectedNode,
    onEditNode,
    onDeleteNode,
    onEditItem,
    onDeleteItem
}) => {
  const [activeTab, setActiveTab] = React.useState('all');

  const handleDragStart = (event: React.DragEvent<HTMLDivElement>, item: ElementItemType) => {
    // Set specific required data for reactflow
    event.dataTransfer.setData('application/reactflow-nodetype', item.type);
    event.dataTransfer.setData('application/reactflow-label', item.name);
    event.dataTransfer.setData('text/plain', item.name);
    
    // Create a custom drag preview for better visual feedback
    const dragPreview = document.createElement('div');
    dragPreview.style.padding = '10px 15px';
    dragPreview.style.background = item.type === 'condition' ? '#90CDF4' : '#EBF8FF';
    dragPreview.style.border = '1px solid #4299E1';
    dragPreview.style.borderRadius = '4px';
    dragPreview.style.width = '150px';
    dragPreview.style.textAlign = 'center';
    dragPreview.style.color = '#2C5282';
    dragPreview.style.fontWeight = 'bold';
    dragPreview.style.fontSize = '13px';
    dragPreview.style.boxShadow = '0 2px 10px rgba(0,0,0,0.1)';
    dragPreview.style.pointerEvents = 'none';
    dragPreview.textContent = item.name;
    
    // Append to body temporarily
    document.body.appendChild(dragPreview);
    
    // Set the custom drag image with proper offsets
    event.dataTransfer.setDragImage(dragPreview, 75, 20);
    
    // Remove the preview element after a short delay
    setTimeout(() => {
      document.body.removeChild(dragPreview);
    }, 0);
    
    // Set drag effect
    event.dataTransfer.effectAllowed = 'move';
  };

  const getVisibleElements = () => {
    switch(activeTab) {
        case 'conditions': return elements.conditions;
        case 'approvers': return elements.approvers;
        case 'all': 
        default: return [...elements.conditions, ...elements.approvers].sort((a,b) => a.name.localeCompare(b.name));
    }
  };

  const canEditOrDelete = selectedNode && selectedNode.data.nodeType !== 'start' && selectedNode.data.nodeType !== 'end';

  return (
    <div className="h-full flex flex-col bg-white border-r p-3 space-y-4 shadow-sm">
      {/* Selected Element Section */}
      {selectedNode && (
        <div className="p-3.5 border border-blue-200 bg-blue-50/60 rounded-lg shadow-sm transition-all animate-in fade-in">
          <h4 className="text-xs font-semibold text-blue-700 mb-2 flex items-center">
            <div className="w-2 h-2 bg-blue-500 rounded-full mr-1.5"></div>
            Selected Element
          </h4>
          <div className="mb-3 bg-white p-2 rounded border border-blue-100">
            <p className="text-sm font-medium text-slate-800 truncate" title={selectedNode.data.label}>{selectedNode.data.label}</p>
            <p className="text-xs text-slate-500 capitalize mt-0.5 flex items-center">
              <span className="inline-block w-2 h-2 bg-slate-300 rounded-full mr-1"></span>
              {selectedNode.data.nodeType}
            </p>
          </div>
          {canEditOrDelete ? (
            <div className="flex space-x-2">
              <Button 
                variant="outline"
                size="sm"
                className="flex-1 text-xs h-8 bg-white border-slate-300 hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 shadow-sm transition-colors"
                onClick={() => onEditNode(selectedNode!)}
              >
                <Edit3 className="h-3.5 w-3.5 mr-1.5" /> Edit
              </Button>
              <Button 
                variant="outline"
                size="sm" 
                className="flex-1 text-xs h-8 border-red-200 text-red-500 hover:bg-red-50 hover:text-red-600 hover:border-red-300 shadow-sm transition-colors"
                onClick={() => onDeleteNode(selectedNode!.id)}
              >
                <Trash2 className="h-3.5 w-3.5 mr-1.5" /> Delete
              </Button>
            </div>
          ) : (
            <div className="flex items-center text-xs text-slate-500 p-2 bg-slate-100/80 rounded-md border border-slate-200">
              <Info className="h-4 w-4 mr-2 text-slate-400"/>
              <span>Start/End nodes cannot be edited</span>
            </div>
          )}
        </div>
      )}

      {/* Reference Image Preview */}
      <div className="mb-1">
        <h3 className="text-xs font-semibold text-slate-600 mb-1.5 flex items-center">
          <div className="w-2 h-2 bg-slate-400 rounded-full mr-1.5"></div>
          Reference Image
        </h3>
        <div className="h-28 bg-white rounded-md border border-slate-200 overflow-hidden flex items-center justify-center shadow-sm hover:shadow-md transition-shadow group">
          {referenceImageUrl ? (
            <img src={referenceImageUrl} alt="Reference" className="max-h-full max-w-full object-contain group-hover:scale-[1.02] transition-transform" />
          ) : (
            <span className="text-xs text-slate-400">No Image Available</span>
          )}
        </div>
      </div>

      {/* Add Elements Section */}
      <div>
        <h3 className="text-xs font-semibold text-slate-600 mb-1.5 flex items-center">
          <div className="w-2 h-2 bg-blue-400 rounded-full mr-1.5"></div>
          Create New Element
        </h3>
        <div className="grid grid-cols-2 gap-1.5">
          {addElements.map((el) => (
            <Button 
              key={el.id}
              variant="outline"
              size="sm"
              className="text-xs justify-start h-9 px-3 border-slate-200 hover:bg-blue-50 hover:border-blue-400 hover:text-blue-600 bg-white shadow-sm transition-all"
              onClick={() => onAddElement(el.type)}
            >
              {el.icon}{el.name}
            </Button>
          ))}
        </div>
      </div>

      {/* Workflow Elements List/Tabs (Draggable items from API) */}
      <div className="flex flex-col flex-1 overflow-hidden pt-1">
        <h3 className="text-xs font-semibold text-slate-600 mb-1.5 flex items-center">
          <div className="w-2 h-2 bg-green-400 rounded-full mr-1.5"></div>
          Workflow Library
        </h3>
        <div className="flex border-b border-slate-200 mb-2">
          {['all', 'conditions', 'approvers'].map(tab => (
            <button 
              key={tab}
              className={`px-3 py-1.5 text-xs font-medium capitalize focus:outline-none transition-colors 
                ${activeTab === tab ? 'border-b-2 border-blue-500 text-blue-600' : 'text-slate-500 hover:text-slate-700 hover:border-slate-400'}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 scrollbar-thin scrollbar-thumb-slate-300 hover:scrollbar-thumb-slate-400">
          {getVisibleElements().length === 0 && (
             <div className="flex flex-col items-center justify-center h-32 border border-dashed border-slate-300 rounded-lg p-4">
               <p className="text-xs text-slate-400 text-center">No {activeTab !== 'all' ? activeTab : 'elements'} available.</p>
             </div>
          )}
          {getVisibleElements().map((item) => (
            <div
              key={item.id}
              className="p-2.5 border rounded-md bg-white hover:bg-blue-50 cursor-grab active:cursor-grabbing transition-all flex items-start text-xs group shadow-sm hover:shadow-md border-slate-200 hover:border-blue-300"
              draggable={true}
              onDragStart={(event) => handleDragStart(event, item)}
              data-type={item.type}
              data-label={item.name}
            >
              <div className="flex items-center justify-center p-1.5 mr-2 rounded-md bg-slate-100 group-hover:bg-white transition-colors">
                {item.type === 'condition' ? 
                  <Zap className="h-3.5 w-3.5 text-amber-500" /> : 
                  <UserCheck className="h-3.5 w-3.5 text-purple-500" />
                }
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-slate-700 leading-tight truncate">{item.name}</p>
                <p className="text-slate-500 text-xxs leading-tight mt-0.5 truncate">{item.description || item.type}</p>
              </div>
              <div className="flex items-center ml-2 opacity-0 group-hover:opacity-100 transition-opacity space-x-1">
                 <button 
                    onClick={(e) => { e.stopPropagation(); onEditItem(item); }}
                    className="p-0.5 rounded hover:bg-slate-200 text-slate-500 hover:text-blue-600 transition-colors"
                    aria-label="Edit element"
                 >
                    <Edit3 className="h-3.5 w-3.5" />
                 </button>
                 <button 
                    onClick={(e) => { e.stopPropagation(); onDeleteItem(item.id, item.name); }}
                    className="p-0.5 rounded hover:bg-slate-200 text-slate-500 hover:text-red-600 transition-colors"
                    aria-label="Delete element"
                 >
                    <Trash2 className="h-3.5 w-3.5" />
                 </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default ElementPanel; 