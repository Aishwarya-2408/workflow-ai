import React, { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ArrowRight, Save, RefreshCw, AlertCircle } from "lucide-react";
import LevelsEditor from "./LevelsEditor";
import ConditionsEditor from "./ConditionsEditor";
import MappingEditor from "./MappingEditor";
import { useToast } from "@/components/ui/use-toast";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { processValidationData } from "@/services/api";

// Import the ProcessingStage type from Home component
type ProcessingStage =
  | "extracting"
  | "validating"
  | "generating"
  | "complete"
  | "error";

interface ValidationTabProps {
  onProceed?: () => void;
  onBack?: () => void;
  isProcessing?: boolean;
  setIsProcessing?: (isProcessing: boolean) => void;
  setProcessingStage?: (stage: ProcessingStage) => void;
  setProcessingError?: (error: string) => void;
  onTreeDataReceived?: (data: any) => void;
  extractedData?: {
    levels?: Record<string, { name: string; description: string }>;
    conditions?: Record<
      string,
      { type: string; description: string; [key: string]: any }
    >;
    mapping?: Record<string, string[]>;
  };
  onDataChange?: (type: string, data: any) => void;
  projectId?: string;
}

const ValidationTab: React.FC<ValidationTabProps> = ({
  onProceed = () => {},
  onBack = () => {},
  isProcessing = false,
  setIsProcessing = () => {},
  setProcessingStage = () => {},
  setProcessingError = () => {},
  onTreeDataReceived = () => {},
  extractedData = {
    levels: {
      L0: {
        name: "Level 1",
        description: "The first approval level in the workflow",
      },
      L1: {
        name: "Level 2",
        description: "The second approval level in the workflow",
      },
      L2: {
        name: "Level 3",
        description: "The final approval level in the workflow",
      },
    },
    conditions: {
      condition1: {
        type: "totalValue",
        value: "<7M",
        description: "Total Value: <7M",
      },
      condition2: {
        type: "contractValueAndDuration",
        value: ">5M",
        duration: ">2Y",
        description: "All contracts >5M and >2Y",
      },
      condition3: {
        type: "contractDuration",
        duration: "> 5Y",
        description: "All contracts >5Y",
      },
    },
    mapping: {
      condition1: ["L0"],
      condition2: ["L1", "L2"],
      condition3: ["L2"],
    },
  },
  onDataChange = () => {},
  projectId,
}) => {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState("levels");
  const [levelsData, setLevelsData] = useState(extractedData.levels || {});
  const [conditionsData, setConditionsData] = useState(
    extractedData.conditions || {},
  );
  const [mappingData, setMappingData] = useState(extractedData.mapping || {});
  const [isSaving, setIsSaving] = useState(false);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isValid, setIsValid] = useState(true);

  // Run validation whenever data changes
  useEffect(() => {
    const errors = validateData();
    setValidationErrors(errors);
    setIsValid(errors.length === 0);
  }, [levelsData, conditionsData, mappingData]);

  const handleLevelsChange = (data: any) => {
    setLevelsData(data);
    onDataChange("levels", data);

    // Update mapping when levels change
    updateMappingOnLevelsChange(data);
  };

  const handleConditionsChange = (data: any) => {
    setConditionsData(data);
    onDataChange("conditions", data);

    // Update mapping when conditions change
    updateMappingOnConditionsChange(data);
  };

  const handleMappingChange = (data: any) => {
    setMappingData(data);
    onDataChange("mapping", data);
  };

  // Helper functions to update mapping when levels or conditions change
  const updateMappingOnLevelsChange = (newLevels: any) => {
    const updatedMapping = { ...mappingData };

    // Remove any level from mapping that no longer exists
    Object.keys(updatedMapping).forEach((conditionKey) => {
      updatedMapping[conditionKey] = updatedMapping[conditionKey].filter(
        (levelKey: string) => newLevels[levelKey] !== undefined,
      );
    });

    setMappingData(updatedMapping);
    onDataChange("mapping", updatedMapping);
  };

  const updateMappingOnConditionsChange = (newConditions: any) => {
    const updatedMapping = { ...mappingData };

    // Remove any condition from mapping that no longer exists
    Object.keys(updatedMapping).forEach((conditionKey) => {
      if (!newConditions[conditionKey]) {
        delete updatedMapping[conditionKey];
      }
    });

    // Add any new condition to mapping
    Object.keys(newConditions).forEach((conditionKey) => {
      if (!updatedMapping[conditionKey]) {
        updatedMapping[conditionKey] = [];
      }
    });

    setMappingData(updatedMapping);
    onDataChange("mapping", updatedMapping);
  };

  const handleSave = () => {
    setIsSaving(true);
    // Simulate saving data
    setTimeout(() => {
      setIsSaving(false);
    }, 1000);
  };

  const handleProceedClick = async () => {
    // Set processing state
    setIsProcessing(true);
    setProcessingStage("validating");

    try {
      // Prepare data for backend
      const validationData = {
        levels: levelsData,
        conditions: conditionsData,
        mapping: mappingData,
      };

      // Use the centralized API function
      const response = await processValidationData(validationData, projectId);

      // Process successful response
      if (response && response.tree_data) {
        // Pass tree data to parent component - parent will handle transitions
        onTreeDataReceived(response.tree_data);
        
        // Let parent component handle processing stage transition
        // Don't set local toast or transition - parent component will handle it
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (error) {
      // Handle error
      console.error("Error processing validation data:", error);
      
      // Extract error message
      const errorMessage = error instanceof Error ? error.message : "Failed to process validation data";
      
      setProcessingError(errorMessage);
      setProcessingStage("error");
      
      toast({
        title: "Error",
        description: "Failed to process validation data. Please check the details and try again.",
        variant: "destructive",
        duration: 5000,
      });
    }
  };

  const validateData = (): string[] => {
    const errors: string[] = [];

    // Validate levels
    if (Object.keys(levelsData).length === 0) {
      errors.push("At least one approval level is required");
    } else {
      // Check each level has name and description
      Object.entries(levelsData).forEach(([id, level]) => {
        if (!level.name || !level.name.trim()) {
          errors.push(`Level ${id} is missing a name`);
        }
      });
    }

    // Validate conditions
    if (Object.keys(conditionsData).length === 0) {
      errors.push("At least one condition is required");
    } else {
      // Check each condition has description and type
      Object.entries(conditionsData).forEach(([id, condition]) => {
        if (!condition.description || !condition.description.trim()) {
          errors.push(`Condition ${id} is missing a description`);
        }
        if (!condition.type || !condition.type.trim()) {
          errors.push(`Condition ${id} is missing a type`);
        }
      });
    }

    // Validate mapping
    if (Object.keys(mappingData).length === 0) {
      errors.push("At least one mapping is required");
    } else {
      // Check each condition has at least one level mapped
      Object.entries(mappingData).forEach(([conditionId, levelIds]) => {
        if (!Array.isArray(levelIds) || levelIds.length === 0) {
          errors.push(`Condition ${conditionId} must be mapped to at least one level`);
        }
      });
    }

    return errors;
  };

  return (
    <div className="w-full h-full p-6 bg-gray-50">
      <Card className="w-full shadow-sm">
        <CardHeader>
          <CardTitle>Validate Extracted Data</CardTitle>
          <CardDescription>
            Review and edit the extracted workflow data before proceeding to
            visualization.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="levels">Levels</TabsTrigger>
              <TabsTrigger value="conditions">Conditions</TabsTrigger>
              <TabsTrigger value="mapping">Mapping</TabsTrigger>
            </TabsList>
            <TabsContent value="levels" className="mt-4">
              <LevelsEditor
                title="Approval Levels"
                data={levelsData}
                onDataChange={handleLevelsChange}
              />
            </TabsContent>
            <TabsContent value="conditions" className="mt-4">
              <ConditionsEditor
                title="Workflow Conditions"
                data={conditionsData}
                onDataChange={handleConditionsChange}
              />
            </TabsContent>
            <TabsContent value="mapping" className="mt-4">
              <MappingEditor
                title="Field Mapping"
                mappingData={mappingData}
                levelsData={levelsData}
                conditionsData={conditionsData}
                onDataChange={handleMappingChange}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
        <CardFooter className="flex justify-between">
          <Button variant="outline" onClick={onBack}>
            Back to Upload
          </Button>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div>
                  <Button 
                    onClick={handleProceedClick} 
                    disabled={isProcessing || !isValid}
                    className="relative"
                  >
                    {isProcessing ? (
                      <>
                        <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        {!isValid && (
                          <AlertCircle className="mr-2 h-4 w-4 text-yellow-500" />
                        )}
                        Proceed
                        <ArrowRight className="ml-2 h-4 w-4" />
                      </>
                    )}
                  </Button>
                </div>
              </TooltipTrigger>
              {!isValid && (
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
        </CardFooter>
      </Card>
    </div>
  );
};

export default ValidationTab;
