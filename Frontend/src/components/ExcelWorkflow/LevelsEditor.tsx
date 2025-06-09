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
import { Alert, AlertDescription } from "@/components/ui/alert";

interface LevelData {
  name: string;
  description: string;
}

interface LevelsEditorProps {
  title?: string;
  data?: Record<string, LevelData>;
  onDataChange?: (data: Record<string, LevelData>) => void;
}

type SortDirection = "asc" | "desc" | null;
type SortableColumn = "levelKey" | "name" | "description";

const LevelsEditor = ({
  title = "Approval Levels",
  data = {
    L0: {
      name: "Level 1",
      description: "The first approval level in the workflow",
    },
    L1: {
      name: "Level 2",
      description: "The second approval level in the workflow",
    },
  },
  onDataChange = () => {},
}: LevelsEditorProps) => {
  const [levelsData, setLevelsData] = useState<Record<string, LevelData>>(data);
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [currentLevelKey, setCurrentLevelKey] = useState<string>("");
  const [formValues, setFormValues] = useState<{
    levelKey: string;
    name: string;
    description: string;
  }>({
    levelKey: "",
    name: "",
    description: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortColumn, setSortColumn] = useState<SortableColumn | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Function to generate the next level key
  const generateNextLevelKey = () => {
    // Extract numeric parts from existing keys (assuming format "LX" where X is a number)
    const numericKeys = Object.keys(levelsData)
      .filter(key => key.startsWith("L"))
      .map(key => {
        const numericPart = key.replace("L", "");
        return isNaN(parseInt(numericPart)) ? 0 : parseInt(numericPart);
      });
    
    // Find the maximum numeric key or default to 0 if no keys exist
    const maxKey = numericKeys.length > 0 ? Math.max(...numericKeys) : 0;
    
    // Return the next key
    return `L${maxKey + 1}`;
  };

  const handleAdd = () => {
    const nextKey = generateNextLevelKey();
    setFormValues({
      levelKey: nextKey,
      name: "",
      description: "",
    });
    setError(null);
    setIsAddDialogOpen(true);
  };

  const handleEdit = (levelKey: string) => {
    setCurrentLevelKey(levelKey);
    setFormValues({
      levelKey,
      name: levelsData[levelKey].name,
      description: levelsData[levelKey].description,
    });
    setError(null);
    setIsEditDialogOpen(true);
  };

  const handleDelete = (levelKey: string) => {
    const newData = { ...levelsData };
    delete newData[levelKey];
    setLevelsData(newData);
    onDataChange(newData);
  };

  const handleInputChange = (key: string, value: string) => {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const validateForm = () => {
    if (!formValues.levelKey.trim()) {
      setError("Level Key is required.");
      return false;
    }
    
    if (!formValues.name.trim()) {
      setError("Level Name is required.");
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

    // Check if the level key already exists
    if (levelsData[formValues.levelKey]) {
      setError(`Level key '${formValues.levelKey}' already exists. Please use a different key.`);
      return;
    }

    const newData = {
      ...levelsData,
      [formValues.levelKey]: {
        name: formValues.name,
        description: formValues.description,
      },
    };
    setLevelsData(newData);
    onDataChange(newData);
    setIsAddDialogOpen(false);
  };

  const handleEditSubmit = () => {
    if (!validateForm()) return;

    if (!currentLevelKey) return;

    const newData = { ...levelsData };

    // Update the existing level (key is read-only in edit mode)
    newData[currentLevelKey] = {
      name: formValues.name,
      description: formValues.description,
    };

    setLevelsData(newData);
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

  // Filter and sort the levels
  const filteredAndSortedLevels = useMemo(() => {
    // First filter by search query
    const filtered = Object.entries(levelsData).filter(([key, level]) => {
      const searchLower = searchQuery.toLowerCase();
      return (
        key.toLowerCase().includes(searchLower) ||
        level.name.toLowerCase().includes(searchLower)
      );
    });

    // Then sort
    if (sortColumn && sortDirection) {
      return filtered.sort(([keyA, levelA], [keyB, levelB]) => {
        let valueA, valueB;
        
        if (sortColumn === "levelKey") {
          valueA = keyA;
          valueB = keyB;
        } else {
          valueA = levelA[sortColumn];
          valueB = levelB[sortColumn];
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
  }, [levelsData, searchQuery, sortColumn, sortDirection]);

  return (
    <div className="w-full p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium">{title}</h3>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search levels..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 w-[250px]"
            />
          </div>
          <Button onClick={handleAdd} className="flex items-center gap-1">
            <PlusCircle className="h-4 w-4" />
            Add Level
          </Button>
        </div>
      </div>

      <div className="rounded-md border">
        <div className="max-h-[400px] overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead onClick={() => handleSort("levelKey")} className="cursor-pointer">
                  <div className="flex items-center">
                    Level Key
                    {getSortIcon("levelKey")}
                  </div>
                </TableHead>
                <TableHead onClick={() => handleSort("name")} className="cursor-pointer">
                  <div className="flex items-center">
                    Name
                    {getSortIcon("name")}
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
              {filteredAndSortedLevels.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={4}
                    className="text-center py-6 text-muted-foreground"
                  >
                    {searchQuery ? "No matching levels found." : "No levels available. Click \"Add Level\" to create a new entry."}
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSortedLevels.map(([levelKey, level]) => (
                  <TableRow key={levelKey}>
                    <TableCell>{levelKey}</TableCell>
                    <TableCell>{level.name}</TableCell>
                    <TableCell>{level.description}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEdit(levelKey)}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(levelKey)}
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
            <DialogTitle>Add New Level</DialogTitle>
          </DialogHeader>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="levelKey" className="text-right font-medium">
                Level Key
              </label>
              <Input
                id="levelKey"
                value={formValues.levelKey}
                className="col-span-3 bg-gray-100"
                readOnly
                disabled
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="name" className="text-right font-medium">
                Level Name
              </label>
              <Input
                id="name"
                value={formValues.name}
                onChange={(e) => handleInputChange("name", e.target.value)}
                className="col-span-3"
                placeholder="Enter level name"
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
                onChange={(e) => handleInputChange("description", e.target.value)}
                className="col-span-3 min-h-[100px] p-2 border rounded-md"
                placeholder="Brief description of this level"
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
            <DialogTitle>Edit Level</DialogTitle>
          </DialogHeader>
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="edit-levelKey" className="text-right font-medium">
                Level Key
              </label>
              <Input
                id="edit-levelKey"
                value={formValues.levelKey}
                className="col-span-3 bg-gray-100"
                readOnly
                disabled
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="edit-name" className="text-right font-medium">
                Level Name
              </label>
              <Input
                id="edit-name"
                value={formValues.name}
                onChange={(e) => handleInputChange("name", e.target.value)}
                className="col-span-3"
                required
              />
            </div>
            <div className="grid grid-cols-4 items-center gap-4">
              <label htmlFor="edit-description" className="text-right font-medium">
                Description
              </label>
              <textarea
                id="edit-description"
                value={formValues.description}
                onChange={(e) => handleInputChange("description", e.target.value)}
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

export default LevelsEditor;
