import React, { useState, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Info, Search, ArrowUpDown, ArrowUp, ArrowDown } from "lucide-react";
import { Input } from "@/components/ui/input";

interface MappingEditorProps {
  title?: string;
  mappingData?: Record<string, string[]>;
  levelsData?: Record<string, { name: string; description: string }>;
  conditionsData?: Record<
    string,
    { type: string; description: string; [key: string]: any }
  >;
  onDataChange?: (data: Record<string, string[]>) => void;
}

type SortDirection = "asc" | "desc" | null;

const MappingEditor = ({
  title = "Mapping Configuration",
  mappingData = {
    condition1: ["L0"],
    condition2: ["L1", "L2"],
    condition3: ["L2"],
  },
  levelsData = {
    L0: { name: "Level 1", description: "First level" },
    L1: { name: "Level 2", description: "Second level" },
    L2: { name: "Level 3", description: "Third level" },
  },
  conditionsData = {
    condition1: { type: "totalValue", description: "Total Value: <7M" },
    condition2: {
      type: "contractValueAndDuration",
      description: "All contracts >5M and >2Y",
    },
    condition3: { type: "contractDuration", description: "All contracts >5Y" },
  },
  onDataChange = () => {},
}: MappingEditorProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);

  // Handle sorting
  const handleSort = () => {
    if (sortDirection === "asc") {
      setSortDirection("desc");
    } else if (sortDirection === "desc") {
      setSortDirection(null);
    } else {
      setSortDirection("asc");
    }
  };

  const getSortIcon = () => {
    if (sortDirection === "asc") {
      return <ArrowUp className="h-4 w-4 ml-1" />;
    }
    if (sortDirection === "desc") {
      return <ArrowDown className="h-4 w-4 ml-1" />;
    }
    return <ArrowUpDown className="h-4 w-4 ml-1" />;
  };

  // Filter and sort the conditions
  const filteredAndSortedConditionKeys = useMemo(() => {
    // First filter by search query
    const filtered = Object.keys(conditionsData).filter((key) => {
      const searchLower = searchQuery.toLowerCase();
      return key.toLowerCase().includes(searchLower);
    });

    // Then sort
    return filtered.sort((keyA, keyB) => {
      // Extract numeric parts for proper sorting
      const numA = parseInt(keyA.replace(/\D/g, ""));
      const numB = parseInt(keyB.replace(/\D/g, ""));
      
      // Default numeric sort
      const defaultSort = isNaN(numA) || isNaN(numB) 
        ? keyA.localeCompare(keyB) 
        : numA - numB;
      
      // Apply sort direction if set
      if (sortDirection === "asc") {
        return defaultSort;
      } else if (sortDirection === "desc") {
        return -defaultSort;
      } else {
        return defaultSort;
      }
    });
  }, [conditionsData, searchQuery, sortDirection]);

  // Sort the level keys for consistent display with numeric sorting
  const sortedLevelKeys = useMemo(() => {
    return Object.keys(levelsData).sort((keyA, keyB) => {
      // Extract numeric parts for proper sorting
      const numA = parseInt(keyA.replace(/\D/g, ""));
      const numB = parseInt(keyB.replace(/\D/g, ""));
      return isNaN(numA) || isNaN(numB) ? keyA.localeCompare(keyB) : numA - numB;
    });
  }, [levelsData]);

  const handleCheckboxChange = (
    conditionKey: string,
    levelKey: string,
    checked: boolean,
  ) => {
    const updatedMapping = { ...mappingData };

    if (!updatedMapping[conditionKey]) {
      updatedMapping[conditionKey] = [];
    }

    if (checked) {
      // Add the level if it's not already in the array
      if (!updatedMapping[conditionKey].includes(levelKey)) {
        updatedMapping[conditionKey] = [
          ...updatedMapping[conditionKey],
          levelKey,
        ];
      }
    } else {
      // Remove the level from the array
      updatedMapping[conditionKey] = updatedMapping[conditionKey].filter(
        (level) => level !== levelKey,
      );
    }

    onDataChange(updatedMapping);
  };

  return (
    <div className="w-full p-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <div>
          <h3 className="text-lg font-medium">{title}</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Configure which levels apply to each condition by checking the
            corresponding boxes.
          </p>
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search conditions..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8 w-[250px]"
          />
        </div>
      </div>

      <div className="rounded-md border">
        <div className="max-h-[400px] overflow-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead 
                  className="w-[200px] cursor-pointer"
                  onClick={handleSort}
                >
                  <div className="flex items-center">
                    Condition
                    {getSortIcon()}
                  </div>
                </TableHead>
                {sortedLevelKeys.map((levelKey) => (
                  <TableHead key={levelKey} className="text-center">
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="flex flex-col items-center cursor-help">
                            <span>{levelKey}</span>
                            <span className="text-xs text-muted-foreground">
                              {levelsData[levelKey].name}
                            </span>
                            <Info className="h-3 w-3 mt-1 text-muted-foreground" />
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>
                            <strong>{levelsData[levelKey].name}</strong>
                          </p>
                          <p className="max-w-xs">
                            {levelsData[levelKey].description}
                          </p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredAndSortedConditionKeys.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={sortedLevelKeys.length + 1}
                    className="text-center py-6 text-muted-foreground"
                  >
                    {searchQuery 
                      ? "No matching conditions found." 
                      : "No conditions available. Add conditions first to configure mapping."}
                  </TableCell>
                </TableRow>
              ) : (
                filteredAndSortedConditionKeys.map((conditionKey) => (
                  <TableRow key={conditionKey}>
                    <TableCell>
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div className="flex items-center cursor-help">
                              <span className="font-medium">{conditionKey}</span>
                              <Info className="h-4 w-4 ml-1 text-muted-foreground" />
                            </div>
                          </TooltipTrigger>
                          <TooltipContent>
                            <p>
                              <strong>Type:</strong>{" "}
                              {conditionsData[conditionKey].type}
                            </p>
                            <p className="max-w-xs">
                              {conditionsData[conditionKey].description}
                            </p>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                    </TableCell>
                    {sortedLevelKeys.map((levelKey) => {
                      const isChecked =
                        mappingData[conditionKey]?.includes(levelKey) || false;
                      return (
                        <TableCell
                          key={`${conditionKey}-${levelKey}`}
                          className="text-center"
                        >
                          <div className="flex justify-center">
                            <Checkbox
                              checked={isChecked}
                              onCheckedChange={(checked) =>
                                handleCheckboxChange(
                                  conditionKey,
                                  levelKey,
                                  checked as boolean,
                                )
                              }
                            />
                          </div>
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
};

export default MappingEditor;
