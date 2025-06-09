import React, { useState, useEffect } from 'react';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { XYPosition } from 'reactflow';

interface ElementCreatorProps {
  open: boolean;
  onClose: () => void;
  onSave: (elementData: {
    id?: string; // Optional: for editing existing elements
    label: string;
    type: 'start' | 'end' | 'task' | 'condition' | 'approver' | 'input';
    position?: XYPosition; // Added for drag and drop
    // Add other properties as needed, e.g., description, assignee, script
  }) => void;
  initialType?: 'start' | 'end' | 'task' | 'condition' | 'approver' | 'input';
  initialData?: Partial<{
    id?: string;
    label: string;
    type: 'start' | 'end' | 'task' | 'condition' | 'approver' | 'input';
    position?: XYPosition; // Added for drag and drop
  }>;
}

const ElementCreator: React.FC<ElementCreatorProps> = ({
  open,
  onClose,
  onSave,
  initialType = 'task',
  initialData = {},
}) => {
  const [label, setLabel] = useState(initialData.label || '');
  const [type, setType] = useState(initialData.type || initialType);

  useEffect(() => {
    setLabel(initialData.label || '');
    setType(initialData.type || initialType);
  }, [initialData, initialType, open]); // Reset when dialog opens or initial data changes

  const handleSubmit = () => {
    if (!label.trim()) {
      alert("Element label cannot be empty.");
      return;
    }
    onSave({
      id: initialData.id,
      label,
      type,
      position: initialData.position,
    });
    onClose(); // Close dialog after save
  };

  const typeOptions = [
    { value: 'start', label: 'Start Event' },
    { value: 'end', label: 'End Event' },
    { value: 'task', label: 'Task' },
    { value: 'condition', label: 'Decision' },
    { value: 'approver', label: 'Approver' },
    { value: 'input', label: 'Data Input' },
  ];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md bg-white rounded-lg shadow-xl">
        <DialogHeader className="px-6 py-4 border-b">
          <DialogTitle className="text-lg font-medium text-slate-800">
            {initialData.id ? 'Edit' : 'Create New'} Workflow Element
          </DialogTitle>
          {initialData.id && initialData.label && (
             <DialogDescription className="text-sm text-slate-500 mt-1">
                Editing: <span className='font-semibold text-slate-600'>{initialData.label}</span>
             </DialogDescription>
          )}
          {!initialData.id && (
            <DialogDescription className="text-sm text-slate-500 mt-1">
              Configure the details for your new workflow element.
            </DialogDescription>
          )}
        </DialogHeader>
        <div className="grid gap-6 p-6">
          <div className="space-y-2">
            <Label htmlFor="element-label" className="text-sm font-medium text-slate-700">
              Label
            </Label>
            <Input
              id="element-label"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="e.g., Review Purchase Requisition"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="element-type" className="text-sm font-medium text-slate-700">
              Type
            </Label>
            <Select value={type} onValueChange={(value) => setType(value as any)} disabled={!!initialData.id}>
              <SelectTrigger className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 text-sm">
                <SelectValue placeholder="Select element type" />
              </SelectTrigger>
              <SelectContent>
                {typeOptions.map(opt => (
                  <SelectItem key={opt.value} value={opt.value} className="text-sm">
                    {opt.label}
                  </SelectItem>
                ))} 
              </SelectContent>
            </Select>
            {initialData.id && <p className='text-xs text-slate-500 mt-1'>Node type cannot be changed after creation.</p>}
          </div>
        </div>
        <DialogFooter className="px-6 py-4 border-t bg-slate-50 rounded-b-lg">
          <Button variant="outline" onClick={onClose} className="px-4 py-2 text-sm border-slate-300 hover:bg-slate-100">
            Cancel
          </Button>
          <Button onClick={handleSubmit} className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white">
            {initialData.id ? 'Save Changes' : 'Create Element'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ElementCreator; 