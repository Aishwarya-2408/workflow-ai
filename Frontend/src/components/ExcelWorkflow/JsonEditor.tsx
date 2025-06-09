import React, { useState } from "react";
import { PlusCircle, Edit, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog";

interface JsonData {
  id: string;
  [key: string]: any;
}

interface JsonEditorProps {
  title?: string;
  data?: JsonData[];
  onDataChange?: (data: JsonData[]) => void;
  columns?: { key: string; label: string }[];
}

const JsonEditor = ({
  title = "JSON Editor",
  data = [
    { id: "1", name: "Level 1", value: "100", description: "First level" },
    { id: "2", name: "Level 2", value: "200", description: "Second level" },
    { id: "3", name: "Level 3", value: "300", description: "Third level" },
  ],
  onDataChange = () => {},
  columns = [
    { key: "name", label: "Name" },
    { key: "value", label: "Value" },
    { key: "description", label: "Description" },
  ],
}: JsonEditorProps) => {
  const [jsonData, setJsonData] = useState<JsonData[]>(data);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [currentItem, setCurrentItem] = useState<JsonData | null>(null);
  const [formValues, setFormValues] = useState<Record<string, any>>({});

  const handleAdd = () => {
    setFormValues({});
    setIsAddDialogOpen(true);
  };

  const handleEdit = (item: JsonData) => {
    setCurrentItem(item);
    setFormValues({ ...item });
    setIsEditDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    const newData = jsonData.filter((item) => item.id !== id);
    setJsonData(newData);
    onDataChange(newData);
  };

  const handleInputChange = (key: string, value: string) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleAddSubmit = () => {
    const newItem = {
      id: Date.now().toString(),
      ...formValues,
    };
    const newData = [...jsonData, newItem];
    setJsonData(newData);
    onDataChange(newData);
    setIsAddDialogOpen(false);
  };

  const handleEditSubmit = () => {
    if (!currentItem) return;

    const newData = jsonData.map((item) =>
      item.id === currentItem.id ? { ...item, ...formValues } : item,
    );
    setJsonData(newData);
    onDataChange(newData);
    setIsEditDialogOpen(false);
  };

  return (
    <div className="w-full p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium">{title}</h3>
        <Button onClick={handleAdd} className="flex items-center gap-1">
          <PlusCircle className="h-4 w-4" />
          Add Item
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((column) => (
                <TableHead key={column.key}>{column.label}</TableHead>
              ))}
              <TableHead className="w-[100px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jsonData.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length + 1}
                  className="text-center py-6 text-muted-foreground"
                >
                  No data available. Click "Add Item" to create a new entry.
                </TableCell>
              </TableRow>
            ) : (
              jsonData.map((item) => (
                <TableRow key={item.id}>
                  {columns.map((column) => (
                    <TableCell key={`${item.id}-${column.key}`}>
                      {item[column.key]}
                    </TableCell>
                  ))}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleEdit(item)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(item.id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Add Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Item</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {columns.map((column) => (
              <div
                key={column.key}
                className="grid grid-cols-4 items-center gap-4"
              >
                <label htmlFor={column.key} className="text-right font-medium">
                  {column.label}
                </label>
                <Input
                  id={column.key}
                  value={formValues[column.key] || ""}
                  onChange={(e) =>
                    handleInputChange(column.key, e.target.value)
                  }
                  className="col-span-3"
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleAddSubmit}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Item</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            {columns.map((column) => (
              <div
                key={column.key}
                className="grid grid-cols-4 items-center gap-4"
              >
                <label
                  htmlFor={`edit-${column.key}`}
                  className="text-right font-medium"
                >
                  {column.label}
                </label>
                <Input
                  id={`edit-${column.key}`}
                  value={formValues[column.key] || ""}
                  onChange={(e) =>
                    handleInputChange(column.key, e.target.value)
                  }
                  className="col-span-3"
                />
              </div>
            ))}
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleEditSubmit}>Update</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default JsonEditor;
