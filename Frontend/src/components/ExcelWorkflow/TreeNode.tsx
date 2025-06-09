import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Edit,
  Trash2,
  Plus,
  UserPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

export interface TreeNodeData {
  id: string;
  label: string;
  children: TreeNodeData[];
  users?: { user: string; label: string }[];
  expanded?: boolean;
}

interface TreeNodeProps {
  node: TreeNodeData;
  onToggle: (nodeId: string) => void;
  onEdit: (
    nodeId: string,
    newLabel: string,
    users?: { user: string; label: string }[],
  ) => void;
  onDelete: (nodeId: string) => void;
  onAddChild: (parentId: string, label: string) => void;
  level: number;
}

const TreeNode: React.FC<TreeNodeProps> = ({
  node,
  onToggle,
  onEdit,
  onDelete,
  onAddChild,
  level,
}) => {
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isAddUserDialogOpen, setIsAddUserDialogOpen] = useState(false);
  const [isEditUserDialogOpen, setIsEditUserDialogOpen] = useState(false);
  const [newLabel, setNewLabel] = useState(node.label);
  const [newChildLabel, setNewChildLabel] = useState("");
  const [newUserName, setNewUserName] = useState("");
  const [newUserLabel, setNewUserLabel] = useState("");
  const [currentUserIndex, setCurrentUserIndex] = useState(-1);

  const hasChildren = node.children && node.children.length > 0;
  const hasUsers = node.users && node.users.length > 0;
  const isExpanded = node.expanded !== false; // Default to expanded if not specified

  const handleEdit = () => {
    setNewLabel(node.label);
    setIsEditDialogOpen(true);
  };

  const handleAddChild = () => {
    setNewChildLabel("");
    setIsAddDialogOpen(true);
  };

  const handleEditSubmit = () => {
    if (newLabel.trim()) {
      onEdit(node.id, newLabel);
    }
    setIsEditDialogOpen(false);
  };

  const handleAddChildSubmit = () => {
    if (newChildLabel.trim()) {
      onAddChild(node.id, newChildLabel);
    }
    setIsAddDialogOpen(false);
  };

  const handleAddUserSubmit = () => {
    if (newUserName.trim() && newUserLabel.trim()) {
      const newUser = {
        user: newUserName,
        label: newUserLabel,
      };
      const updatedUsers = [...(node.users || []), newUser];
      onEdit(node.id, node.label, updatedUsers);
      setIsAddUserDialogOpen(false);
    }
  };

  const handleEditUserSubmit = () => {
    if (newUserName.trim() && newUserLabel.trim() && currentUserIndex >= 0) {
      const updatedUsers = [...(node.users || [])];
      updatedUsers[currentUserIndex] = {
        user: newUserName,
        label: newUserLabel,
      };
      onEdit(node.id, node.label, updatedUsers);
      setIsEditUserDialogOpen(false);
    }
  };

  const handleDeleteUser = (index: number) => {
    const updatedUsers = [...(node.users || [])];
    updatedUsers.splice(index, 1);
    onEdit(node.id, node.label, updatedUsers);
  };

  // Calculate background color based on level
  const getBgColor = () => {
    const colors = [
      "bg-blue-50 border-blue-200 text-blue-800",
      "bg-purple-50 border-purple-200 text-purple-800",
      "bg-green-50 border-green-200 text-green-800",
      "bg-amber-50 border-amber-200 text-amber-800",
      "bg-red-50 border-red-200 text-red-800",
    ];
    return colors[level % colors.length];
  };

  return (
    <div className="relative">
      <div className="flex items-start mb-2">
        <div className="mt-2 mr-1">
          {hasChildren || hasUsers ? (
            <button
              onClick={() => onToggle(node.id)}
              className="p-1 rounded-full hover:bg-gray-200"
            >
              {isExpanded ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
            </button>
          ) : (
            <div className="w-6"></div>
          )}
        </div>

        <div
          className={`flex-1 p-3 rounded-md border ${getBgColor()} hover:shadow-md transition-shadow max-w-md`}
        >
          <div className="flex justify-between items-center">
            <div className="font-medium">{node.label}</div>
            <div className="flex space-x-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleEdit}
                title="Edit node"
              >
                <Edit size={14} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleAddChild}
                title="Add child node"
              >
                <Plus size={14} />
              </Button>
              {node.id !== "root" && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => onDelete(node.id)}
                  title="Delete node"
                >
                  <Trash2 size={14} />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => {
                  setNewUserName("");
                  setNewUserLabel("");
                  setIsAddUserDialogOpen(true);
                }}
                title="Add user"
              >
                <UserPlus size={14} />
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Render children with connecting lines */}
      {isExpanded && (
        <div className="pl-8 border-l-2 border-gray-300 ml-3">
          {hasChildren &&
            node.children.map((child) => (
              <TreeNode
                key={child.id}
                node={child}
                onToggle={onToggle}
                onEdit={onEdit}
                onDelete={onDelete}
                onAddChild={onAddChild}
                level={level + 1}
              />
            ))}

          {/* Render users as leaf nodes if present */}
          {hasUsers && (
            <div className="flex items-start mb-2">
              <div className="w-6 mr-1"></div>
              <div className="flex-1 p-2 rounded-md border bg-gray-50 border-gray-200">
                <div className="flex justify-between items-center mb-2">
                  <div className="font-medium">Users</div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    onClick={() => {
                      setNewUserName("");
                      setNewUserLabel("");
                      setIsAddUserDialogOpen(true);
                    }}
                  >
                    <Plus size={14} />
                  </Button>
                </div>
                <div className="space-y-2">
                  {node.users.map((user, index) => (
                    <div
                      key={index}
                      className="flex justify-between items-center p-1 hover:bg-gray-100 rounded"
                    >
                      <div>
                        <div className="font-medium">{user.label}</div>
                        <div className="text-xs text-gray-500">{user.user}</div>
                      </div>
                      <div className="flex space-x-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => {
                            setCurrentUserIndex(index);
                            setNewUserName(user.user);
                            setNewUserLabel(user.label);
                            setIsEditUserDialogOpen(true);
                          }}
                        >
                          <Edit size={12} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          onClick={() => handleDeleteUser(index)}
                        >
                          <Trash2 size={12} className="text-red-500" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Node</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <label className="block text-sm font-medium mb-2">Node Name</label>
            <Input
              value={newLabel}
              onChange={(e) => setNewLabel(e.target.value)}
              placeholder="Enter node name"
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleEditSubmit}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Child Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Child Node</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <label className="block text-sm font-medium mb-2">Node Name</label>
            <Input
              value={newChildLabel}
              onChange={(e) => setNewChildLabel(e.target.value)}
              placeholder="Enter node name"
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleAddChildSubmit}>Add</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add User Dialog */}
      <Dialog open={isAddUserDialogOpen} onOpenChange={setIsAddUserDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add User</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">User</label>
              <Input
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                placeholder="Enter user identifier"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Label</label>
              <Input
                value={newUserLabel}
                onChange={(e) => setNewUserLabel(e.target.value)}
                placeholder="Enter display label"
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleAddUserSubmit}>Add User</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit User Dialog */}
      <Dialog
        open={isEditUserDialogOpen}
        onOpenChange={setIsEditUserDialogOpen}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">User</label>
              <Input
                value={newUserName}
                onChange={(e) => setNewUserName(e.target.value)}
                placeholder="Enter user identifier"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Label</label>
              <Input
                value={newUserLabel}
                onChange={(e) => setNewUserLabel(e.target.value)}
                placeholder="Enter display label"
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleEditUserSubmit}>Update User</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default TreeNode;
