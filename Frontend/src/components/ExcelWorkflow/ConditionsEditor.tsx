import React, { useState, useMemo } from "react";
import { PlusCircle, Edit, Trash2, Info, Search, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface ConditionData {
  type: string;
  description: string;
  [key: string]: any;
}

interface ConditionsEditorProps {
  title?: string;
  data?: Record<string, ConditionData>;
  onDataChange?: (data: Record<string, ConditionData>) => void;
}

type SortDirection = "asc" | "desc" | null;
type SortableColumn = "conditionKey" | "type" | "description";

const ConditionsEditor = ({
  title = "Workflow Conditions",
  data = {
    condition1: {
      type: "totalValue",
      description: "Total Value: <7M",
    },
    condition2: {
      type: "contractValueAndDuration",
      description: "All contracts >5M and >2Y",
    },
  },
  onDataChange = () => {},
}: ConditionsEditorProps) => {
  const [conditionsData, setConditionsData] =
    useState<Record<string, ConditionData>>(data);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [currentConditionKey, setCurrentConditionKey] = useState<string>("");
  const [formValues, setFormValues] = useState<{
    conditionKey: string;
    type: string;
    description: string;
  }>({
    conditionKey: "",
    type: "totalValue",
    description: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortColumn, setSortColumn] = useState<SortableColumn | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Function to generate the next condition key
  const generateNextConditionKey = () => {
    // Extract numeric parts from existing keys (assuming format "conditionX" where X is a number)
    const numericKeys = Object.keys(conditionsData)
      .filter(key => key.startsWith("condition"))
      .map(key => {
        const numericPart = key.replace("condition", "");
        return isNaN(parseInt(numericPart)) ? 0 : parseInt(numericPart);
      });
    
    // Find the maximum numeric key or default to 0 if no keys exist
    const maxKey = numericKeys.length > 0 ? Math.max(...numericKeys) : 0;
    
    // Return the next key
    return `condition${maxKey + 1}`;
  };

  const handleAdd = () => {
    const nextKey = generateNextConditionKey();
    setFormValues({
      conditionKey: nextKey,
      type: "totalValue",
      description: "",
    });
    setError(null);
    setIsAddDialogOpen(true);
  };

  const handleEdit = (conditionKey: string) => {
    setCurrentConditionKey(conditionKey);
    const condition = conditionsData[conditionKey];
    setFormValues({
      conditionKey,
      type: condition.type,
      description: condition.description,
    });
    setError(null);
    setIsEditDialogOpen(true);
  };

  const handleDelete = (conditionKey: string) => {
    const newData = { ...conditionsData };
    delete newData[conditionKey];
    setConditionsData(newData);
    onDataChange(newData);
  };

  const handleInputChange = (key: string, value: string) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const validateForm = () => {
    if (!formValues.conditionKey.trim()) {
      setError("Condition Key is required.");
      return false;
    }
    
    if (!formValues.type.trim()) {
      setError("Type is required.");
      return false;
    }
    
    if (!formValues.description.trim()) {
      setError("Description is required.");
      return false;
    }
    
    return true;
  };

  const handleAddSubmit = () => {
    if (!validateForm()) return;

    // Check if the condition key already exists
    if (conditionsData[formValues.conditionKey]) {
      setError(`Condition key '${formValues.conditionKey}' already exists. Cannot add duplicate keys.`);
      return;
    }

    const conditionData: ConditionData = {
      type: formValues.type,
      description: formValues.description,
    };

    const newData = {
      ...conditionsData,
      [formValues.conditionKey]: conditionData,
    };

    setConditionsData(newData);
    onDataChange(newData);
    setIsAddDialogOpen(false);
  };

  const handleEditSubmit = () => {
    if (!currentConditionKey || !validateForm()) return;

    const conditionData: ConditionData = {
      type: formValues.type,
      description: formValues.description,
    };

    const newData = { ...conditionsData };

    // Update the existing condition (key is read-only, so no need to check for changes)
    newData[currentConditionKey] = conditionData;

    setConditionsData(newData);
    onDataChange(newData);
    setIsEditDialogOpen(false);
  };

  const handleSort = (column: SortableColumn) => {
    if (sortColumn === column) {
      // Toggle direction if same column is clicked
      if (sortDirection === "asc") {
        setSortDirection("desc");
      } else if (sortDirection === "desc") {
        setSortDirection(null);
        setSortColumn(null);
      } else {
        setSortDirection("asc");
      }
    } else {
      // Set new column and direction
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const getSortIcon = (column: SortableColumn) => {
    if (sortColumn !== column) {
      return <ArrowUpDown className="h-4 w-4 ml-1" />;
    }
    if (sortDirection === "asc") {
      return <ArrowUp className="h-4 w-4 ml-1" />;
    }
    if (sortDirection === "desc") {
      return <ArrowDown className="h-4 w-4 ml-1" />;
    }
    return <ArrowUpDown className="h-4 w-4 ml-1" />;
  };

  // Filter and sort the conditions
  const filteredAndSortedConditions = useMemo(() => {
    // First filter by search query
    const filtered = Object.entries(conditionsData).filter(([key, condition]) => {
      const searchLower = searchQuery.toLowerCase();
      return (
        key.toLowerCase().includes(searchLower) ||
        condition.type.toLowerCase().includes(searchLower)
      );
    });

    // Then sort
    if (sortColumn && sortDirection) {
      return filtered.sort(([keyA, conditionA], [keyB, conditionB]) => {
        let valueA, valueB;
        
        if (sortColumn === "conditionKey") {
          valueA = keyA;
          valueB = keyB;
        } else {
          valueA = conditionA[sortColumn];
          valueB = conditionB[sortColumn];
        }

        // Extract numeric parts for proper sorting if they are numeric
        if (typeof valueA === 'string' && typeof valueB === 'string') {
          const numA = parseInt(valueA.replace(/\D/g, ""));
          const numB = parseInt(valueB.replace(/\D/g, ""));
          
          if (!isNaN(numA) && !isNaN(numB)) {
            return sortDirection === "asc" ? numA - numB : numB - numA;
          }
        }

        // Default string comparison
        if (sortDirection === "asc") {
          return String(valueA).localeCompare(String(valueB));
        } else {
          return String(valueB).localeCompare(String(valueA));
        }
      });
    }

    // Default sort by key with numeric awareness
    return filtered.sort(([keyA], [keyB]) => {
      const numA = parseInt(keyA.replace(/\D/g, ""));
      const numB = parseInt(keyB.replace(/\D/g, ""));
      return isNaN(numA) || isNaN(numB) ? keyA.localeCompare(keyB) : numA - numB;
    });
  }, [conditionsData, searchQuery, sortColumn, sortDirection]);

  return (
    <div className="w-full p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium">{title}</h3>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search conditions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 w-[250px]"
            />
          </div>
          <Button onClick={handleAdd} className="flex items-center gap-1">
            <PlusCircle className="h-4 w-4" />
            Add Condition
          </Button>
        </div>
      </div>

      <div className="rounded-md border">
        <div className="max-h-[400px] overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead onClick={() => handleSort("conditionKey")} className="cursor-pointer">
                  <div className="flex items-center">
                    Condition Key
                    {getSortIcon("conditionKey")}
                  </div>
                </TableHead>
                <TableHead onClick={() => handleSort("type")} className="cursor-pointer">
                  <div className="flex items-center">
                    Type
                    {getSortIcon("type")}
                  </div>
                </TableHead>
                <TableHead onClick={() => handleSort("description")} className="cursor-pointer">
                  <div className="flex items-center">
                    Description
                    {getSortIcon("description")}
                  </div>
                </TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAndSortedConditions.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={4}
                    className="text-center py-6 text-muted-foreground"
                  >
                    {searchQuery ? "No matching conditions found." : "No conditions available. Click \"Add Condition\" to create a new entry."}
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSortedConditions.map(([conditionKey, condition]) => (
                  <TableRow key={conditionKey}>
                    <TableCell>{conditionKey}</TableCell>
                    <TableCell>{condition.type}</TableCell>
                    <TableCell>{condition.description}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(conditionKey)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(conditionKey)}
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
      </div>

      {/* Add Dialog */}
      <Dialog open={isAddDialogOpen} onOpenChange={setIsAddDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add New Condition</DialogTitle>
          </DialogHeader>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="conditionKey" className="text-right font-medium">
                Condition Key
              </label>
              <Input
                id="conditionKey"
                value={formValues.conditionKey}
                className="col-span-3 bg-gray-100"
                readOnly
                disabled
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="type" className="text-right font-medium">
                Type
              </label>
              <Input
                id="type"
                value={formValues.type}
                onChange={(e) => handleInputChange("type", e.target.value)}
                className="col-span-3"
                placeholder="Enter condition type"
                required
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="description" className="text-right font-medium">
                Description
              </label>
              <textarea
                id="description"
                value={formValues.description}
                onChange={(e) =>
                  handleInputChange("description", e.target.value)
                }
                className="col-span-3 min-h-[100px] p-2 border rounded-md"
                placeholder="Brief description of this condition"
                required
              />
            </div>
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
            <DialogTitle>Edit Condition</DialogTitle>
          </DialogHeader>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <label
                htmlFor="edit-conditionKey"
                className="text-right font-medium"
              >
                Condition Key
              </label>
              <Input
                id="edit-conditionKey"
                value={formValues.conditionKey}
                className="col-span-3 bg-gray-100"
                readOnly
                disabled
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="edit-type" className="text-right font-medium">
                Type
              </label>
              <Input
                id="edit-type"
                value={formValues.type}
                onChange={(e) => handleInputChange("type", e.target.value)}
                className="col-span-3"
                placeholder="Enter condition type"
                required
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <label
                htmlFor="edit-description"
                className="text-right font-medium"
              >
                Description
              </label>
              <textarea
                id="edit-description"
                value={formValues.description}
                onChange={(e) =>
                  handleInputChange("description", e.target.value)
                }
                className="col-span-3 min-h-[100px] p-2 border rounded-md"
                required
              />
            </div>
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

export default ConditionsEditor;
