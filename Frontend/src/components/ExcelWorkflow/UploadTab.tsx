import React, { useState, useCallback } from "react";
import { Upload, FileUp, Settings, Info, FileQuestion, AlertCircle, RefreshCw, Database, CreditCard, FileText, Plus, X, MoveUp, MoveDown, List } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useToast } from "@/components/ui/use-toast";
import { uploadFile } from "@/services/api";

interface UploadTabProps {
  onFileUpload?: (file: File) => void;
  onConfigChange?: (config: UploadConfig) => void;
  isLoading?: boolean;
  onProceed?: () => void;
  onValidationDataReceived?: (data: any) => void;
  setIsProcessing?: (isProcessing: boolean) => void;
  setProcessingStage?: (stage: "extracting" | "validating" | "generating" | "complete" | "error") => void;
  setProcessingError?: (error: string) => void;
  setProjectId?: (projectId: string) => void;
}

interface UploadConfig {
  projectName: string;
  projectDescription: string;
  headerRow: number;
  dataStartRow: number;
  selectedSheet: string;
  enableChaining: boolean;
  mcwId: string;
  mcwTitle: string;
  mcwProcess: string;
  wcmCurrency: string;
  wcmDocument: string;
  wcmConditionKeys: string[];
  wcmStartConditionId: string;
}

// API response interface
interface UploadResponse {
  message: string;
  validation_data?: {
    levels: Record<string, { name: string; description: string }>;
    conditions: Record<string, any>;
    mapping: Record<string, string[]>;
  };
  project_id?: string;
  error?: string;
  details?: string[] | string;
}

const UploadTab: React.FC<UploadTabProps> = ({
  onFileUpload = () => {},
  onConfigChange = () => {},
  isLoading: externalIsLoading = false,
  onProceed = () => {},
  onValidationDataReceived = () => {},
  setIsProcessing = () => {},
  setProcessingStage = () => {},
  setProcessingError = () => {},
  setProjectId = () => {},
}) => {
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [config, setConfig] = useState<UploadConfig>({
    projectName: "",
    projectDescription: "",
    headerRow: 1,
    dataStartRow: 2,
    selectedSheet: "Sheet1",
    enableChaining: false,
    mcwId: "",
    mcwTitle: "",
    mcwProcess: "",
    wcmCurrency: "",
    wcmDocument: "",
    wcmConditionKeys: [""],
    wcmStartConditionId: "",
  });

  // Available sheets (would normally come from the uploaded file)
  const availableSheets = ["Sheet1", "Sheet2", "Sheet3"];

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  // Check if file type is valid (Excel or CSV)
  const isValidFileType = (file: File): boolean => {
    const validExtensions = ['.xlsx', '.xls', '.csv'];
    const fileName = file.name.toLowerCase();
    return validExtensions.some(ext => fileName.endsWith(ext));
  };

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const uploadedFile = e.dataTransfer.files[0];
        
        if (!isValidFileType(uploadedFile)) {
          setFileError("Invalid file type. Only Excel (.xlsx, .xls) or CSV (.csv) files are allowed.");
          return;
        }
        
        setFileError(null);
        setFile(uploadedFile);
        onFileUpload(uploadedFile);
      }
    },
    [onFileUpload],
  );

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        const uploadedFile = e.target.files[0];
        
        if (!isValidFileType(uploadedFile)) {
          setFileError("Invalid file type. Only Excel (.xlsx, .xls) or CSV (.csv) files are allowed.");
          return;
        }
        
        setFileError(null);
        setFile(uploadedFile);
        onFileUpload(uploadedFile);
      }
    },
    [onFileUpload],
  );

  const handleConfigChange = useCallback(
    (key: keyof UploadConfig, value: any) => {
      const newConfig = { ...config, [key]: value };
      setConfig(newConfig);
      onConfigChange(newConfig);
    },
    [config, onConfigChange],
  );

  // Check if all required fields are filled
  const isFormValid = () => {
    if (!file) return false;
    if (!config.projectName.trim()) return false;
    if (!config.projectDescription.trim()) return false;
    if (config.headerRow <= 0) return false;
    if (config.dataStartRow <= 0) return false;
    if (config.dataStartRow <= config.headerRow) return false;
    
    // Check if sheet selection is required (for Excel files only)
    const isExcelFile = file && (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls'));
    if (isExcelFile && !config.selectedSheet.trim()) return false;
    
    // Validate new required fields
    if (!config.mcwId.trim()) return false;
    if (!/^ALT\d+$/.test(config.mcwId.trim())) return false;
    if (!config.mcwTitle.trim()) return false;
    if (!config.mcwProcess.trim()) return false;
    if (!config.wcmCurrency.trim()) return false;
    if (!config.wcmDocument.trim()) return false;
    
    // Validate start condition ID
    if (!config.wcmStartConditionId.trim()) return false;
    // Basic format validation (starts with WC, followed by digits)
    if (!/^WC\d+$/.test(config.wcmStartConditionId.trim())) return false;
    
    // Require at least one condition key
    if (config.wcmConditionKeys.length === 0) return false;
    
    // Ensure all condition keys are filled
    if (config.wcmConditionKeys.some(key => !key.trim())) return false;
    
    return true;
  };

  // Add a new condition key
  const addConditionKey = useCallback(() => {
    const newConfig = { 
      ...config, 
      wcmConditionKeys: [...config.wcmConditionKeys, ""] 
    };
    setConfig(newConfig);
    onConfigChange(newConfig);
  }, [config, onConfigChange]);

  // Update a condition key at a specific index
  const updateConditionKey = useCallback((index: number, value: string) => {
    const newConditionKeys = [...config.wcmConditionKeys];
    newConditionKeys[index] = value;
    
    const newConfig = { 
      ...config, 
      wcmConditionKeys: newConditionKeys 
    };
    setConfig(newConfig);
    onConfigChange(newConfig);
  }, [config, onConfigChange]);

  // Remove a condition key at a specific index
  const removeConditionKey = useCallback((index: number) => {
    const newConditionKeys = [...config.wcmConditionKeys];
    newConditionKeys.splice(index, 1);
    
    const newConfig = { 
      ...config, 
      wcmConditionKeys: newConditionKeys 
    };
    setConfig(newConfig);
    onConfigChange(newConfig);
  }, [config, onConfigChange]);

  // Move a condition key up (decrease index)
  const moveConditionKeyUp = useCallback((index: number) => {
    if (index <= 0) return; // Can't move the first item up
    
    const newConditionKeys = [...config.wcmConditionKeys];
    const temp = newConditionKeys[index];
    newConditionKeys[index] = newConditionKeys[index - 1];
    newConditionKeys[index - 1] = temp;
    
    const newConfig = { 
      ...config, 
      wcmConditionKeys: newConditionKeys 
    };
    setConfig(newConfig);
    onConfigChange(newConfig);
  }, [config, onConfigChange]);

  // Move a condition key down (increase index)
  const moveConditionKeyDown = useCallback((index: number) => {
    if (index >= config.wcmConditionKeys.length - 1) return; // Can't move the last item down
    
    const newConditionKeys = [...config.wcmConditionKeys];
    const temp = newConditionKeys[index];
    newConditionKeys[index] = newConditionKeys[index + 1];
    newConditionKeys[index + 1] = temp;
    
    const newConfig = { 
      ...config, 
      wcmConditionKeys: newConditionKeys 
    };
    setConfig(newConfig);
    onConfigChange(newConfig);
  }, [config, onConfigChange]);

  // Function to upload file to backend
  const uploadFileToBackend = async () => {
    if (!file || !isFormValid()) return;

    setIsLoading(true);
    setIsProcessing(true);
    setProcessingStage("extracting");
    
    try {
      // Use the centralized API function
      const data = await uploadFile(file, config);
      
      // Pass validation data to parent component
      if (data.validation_data) {
        onValidationDataReceived(data.validation_data);
      }
      
      // Set project id
      if (data.project_id) {
        setProjectId(data.project_id);
      }
      
      // Set processing to complete stage before proceeding to next step
      // The ProcessingIndicator will handle the transition to 100% and the delay
      setProcessingStage("complete");
      
      // Don't add any additional delays here as the ProcessingIndicator
      // will handle the completion and call onProceed via onComplete
    } catch (error) {
      console.error('Error uploading file:', error);
      
      // Extract error message
      const errorMessage = error instanceof Error ? error.message : "Failed to upload file";
      
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
      
      // Set processing to error stage with error message
      setProcessingStage("error");
      setProcessingError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full h-full flex flex-col justify-center items-center bg-white">
      <div className="max-w-5xl w-full px-6 py-12">
        {/* File Upload Area */}
        <Card className={`border-2 border-dashed ${fileError ? "border-red-500" : ""}`}>
          <CardContent className="p-6">
            <div
              className={`flex flex-col items-center justify-center p-12 rounded-lg transition-colors ${
                isDragging
                  ? "bg-primary/10 border-primary"
                  : "bg-muted/50 hover:bg-muted/80"
              } ${file ? "border-green-500" : ""} ${fileError ? "border-red-500 bg-red-50" : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="flex flex-col items-center text-center space-y-4">
                <div className={`p-4 ${fileError ? "bg-red-100" : "bg-primary/10"} rounded-full`}>
                  {fileError ? (
                    <AlertCircle className="h-10 w-10 text-red-500" strokeWidth={1.5} />
                  ) : (
                    <Upload className="h-10 w-10 text-primary" strokeWidth={1.5} />
                  )}
                </div>
                <div className="space-y-2">
                  <h3 className="font-medium text-lg">
                    {fileError 
                      ? "File Upload Error" 
                      : file 
                        ? "File Ready for Upload" 
                        : "Drag & Drop Your File"}
                  </h3>
                  <p className={`text-sm max-w-xs ${fileError ? "text-red-500" : "text-muted-foreground"}`}>
                    {fileError
                      ? fileError
                      : file
                        ? `Selected: ${file.name}`
                        : "Upload your Excel or CSV file with workflow data"}
                  </p>
                </div>
                <div className="flex gap-2">
                  <label htmlFor="file-upload">
                    <Button
                      variant="outline"
                      className="cursor-pointer"
                      onClick={() =>
                        document.getElementById("file-upload")?.click()
                      }
                    >
                      <FileUp className="mr-2 h-4 w-4" />
                      {file ? "Change File" : "Select File"}
                    </Button>
                  </label>
                  {file && (
                    <Button variant="default" onClick={() => {
                      setFile(null);
                      setFileError(null);
                    }}>
                      Remove
                    </Button>
                  )}
                  {fileError && (
                    <Button variant="outline" onClick={() => setFileError(null)}>
                      Dismiss Error
                    </Button>
                  )}
                </div>
                <input
                  id="file-upload"
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  className="hidden"
                  onChange={handleFileChange}
                />
              </div>
            </div>
          </CardContent>
          
        </Card>

        {/* Configuration Options */}
        {file && !fileError && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Configuration Options
            </CardTitle>
            <CardDescription>
              Set parameters for processing your workflow data
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-8">
            {/* Project Information */}
            <div className="space-y-4 p-4 rounded-lg border bg-card shadow-sm">
              <h3 className="text-md font-medium flex items-center gap-2 pb-2 border-b">
                <Info className="h-4 w-4" />
                Project Information
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="project-name">Project Name</Label>
                  <Input
                    id="project-name"
                    placeholder="Enter project name"
                    value={config.projectName}
                    onChange={(e) =>
                      handleConfigChange("projectName", e.target.value)
                    }
                    required
                  />
                </div>
                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="project-description">Description</Label>
                  <Textarea
                    id="project-description"
                    placeholder="Enter a brief description of this workflow"
                    value={config.projectDescription}
                    onChange={(e) =>
                      handleConfigChange("projectDescription", e.target.value)
                    }
                    className="min-h-[80px]"
                    required
                  />
                </div>
              </div>
            </div>

            {/* MCW Configuration */}
            <div className="space-y-4 p-4 rounded-lg border bg-card shadow-sm">
              <h3 className="text-md font-medium flex items-center gap-2 pb-2 border-b">
                <Database className="h-4 w-4" />
                MCW Configuration (Basic Info)
              </h3>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="mcw-id">ID</Label>
                  <Input
                    id="mcw-id"
                    placeholder="Enter MCW ID (e.g., ALT0001)"
                    value={config.mcwId}
                    onChange={(e) =>
                      handleConfigChange("mcwId", e.target.value)
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mcw-title">Title</Label>
                  <Input
                    id="mcw-title"
                    placeholder="Enter MCW Title (e.g., Full Source Award Workflow)"
                    value={config.mcwTitle}
                    onChange={(e) =>
                      handleConfigChange("mcwTitle", e.target.value)
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="mcw-process">Process</Label>
                  <Input
                    id="mcw-process"
                    placeholder="Enter MCW Process (e.g., Award)"
                    value={config.mcwProcess}
                    onChange={(e) =>
                      handleConfigChange("mcwProcess", e.target.value)
                    }
                    required
                  />
                </div>
              </div>
            </div>

            {/* WCM Configuration */}
            <div className="space-y-4 p-4 rounded-lg border bg-card shadow-sm">
              <h3 className="text-md font-medium flex items-center gap-2 pb-2 border-b">
                <CreditCard className="h-4 w-4" />
                WCM Configuration
              </h3>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="wcm-start-condition-id">Start Condition ID</Label>
                  <Input
                    id="wcm-start-condition-id"
                    placeholder="e.g., WC00001"
                    value={config.wcmStartConditionId}
                    onChange={(e) =>
                      handleConfigChange("wcmStartConditionId", e.target.value)
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="wcm-currency">Currency</Label>
                  <Input
                    id="wcm-currency"
                    placeholder="Enter Currency (e.g., USD)"
                    value={config.wcmCurrency}
                    onChange={(e) =>
                      handleConfigChange("wcmCurrency", e.target.value)
                    }
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="wcm-document">Document</Label>
                  <Input
                    id="wcm-document"
                    placeholder="Enter Document Type (e.g., Award)"
                    value={config.wcmDocument}
                    onChange={(e) =>
                      handleConfigChange("wcmDocument", e.target.value)
                    }
                    required
                  />
                </div>
              </div>
              
              {/* WCM Condition Keys */}
              <div className="space-y-4 mt-4 border-t pt-4">
                <div className="flex items-center justify-between">
                  <Label className="flex items-center gap-2">
                    <List className="h-4 w-4" />
                    Condition Keys
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Info className="h-4 w-4 text-muted-foreground cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent className="max-w-xs">
                          <p>Define the keys used in condition expressions (e.g., Contract_Sub_Type, Procurement_Type).</p>
                          <p className="mt-1">These will be used as field names in the WCM file.</p>
                          <p className="mt-1 font-medium">The order of keys is important and will be preserved in the output.</p>
                          <p className="mt-1 text-xs">At least one condition key is required.</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  </Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addConditionKey}
                    className="flex items-center gap-1"
                  >
                    <Plus className="h-3.5 w-3.5" />
                    Add Another Key
                  </Button>
                </div>
                
                <div className="space-y-2 max-h-80 overflow-y-auto pr-1">
                  {config.wcmConditionKeys.map((key, index) => (
                    <div
                      key={`condition-key-${index}`}
                      className="flex items-center gap-2 group bg-muted/20 rounded-md p-2 hover:bg-muted/40 transition-colors"
                    >
                      <div className="flex-shrink-0 w-6 flex justify-center">
                        <span className="text-sm font-medium text-muted-foreground">{index + 1}.</span>
                      </div>
                      <Input
                        value={key}
                        onChange={(e) => updateConditionKey(index, e.target.value)}
                        placeholder={`Enter condition key ${index + 1} (e.g., Contract_Sub_Type)`}
                        className="flex-grow"
                      />
                      <div className="flex-shrink-0 flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-slate-700 hover:bg-slate-200"
                          onClick={() => moveConditionKeyUp(index)}
                          disabled={index === 0}
                        >
                          <MoveUp className="h-4 w-4" />
                          <span className="sr-only">Move up</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-slate-700 hover:bg-slate-200"
                          onClick={() => moveConditionKeyDown(index)}
                          disabled={index === config.wcmConditionKeys.length - 1}
                        >
                          <MoveDown className="h-4 w-4" />
                          <span className="sr-only">Move down</span>
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-red-700 hover:bg-red-100"
                          onClick={() => removeConditionKey(index)}
                          disabled={config.wcmConditionKeys.length === 1}
                        >
                          <X className="h-4 w-4" />
                          <span className="sr-only">Remove</span>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* File Structure Settings */}
            <div className="space-y-4 p-4 rounded-lg border bg-card shadow-sm">
              <h3 className="text-md font-medium flex items-center gap-2 pb-2 border-b">
                <FileQuestion className="h-4 w-4" />
                File Structure
              </h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="header-row">Header Row</Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="relative">
                          <Input
                            id="header-row"
                            type="number"
                            min="1"
                            value={config.headerRow}
                            onChange={(e) =>
                              handleConfigChange(
                                "headerRow",
                                parseInt(e.target.value) || 0,
                              )
                            }
                            required
                          />
                          <Info className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground" />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Row number upto which column headers are present</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="data-start-row">Data Start Row</Label>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="relative">
                          <Input
                            id="data-start-row"
                            type="number"
                            min="1"
                            value={config.dataStartRow}
                            onChange={(e) =>
                              handleConfigChange(
                                "dataStartRow",
                                parseInt(e.target.value) || 0,
                              )
                            }
                            required
                          />
                          <Info className="absolute right-3 top-2.5 h-4 w-4 text-muted-foreground" />
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Row number where actual data begins</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>
                {file && (file.name.toLowerCase().endsWith(".xlsx") || file.name.toLowerCase().endsWith(".xls")) && (
                  <div className="space-y-2">
                    <Label htmlFor="sheet-selection">Select Sheet</Label>
                    <Input
                      id="sheet-selection"
                      value={config.selectedSheet}
                      onChange={(e) =>
                        handleConfigChange("selectedSheet", e.target.value)
                      }
                      placeholder="Enter sheet name"
                      required
                    />
                  </div>
                )}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="enable-chaining">Enable Chaining</Label>
                    <Switch
                      id="enable-chaining"
                      checked={config.enableChaining}
                      onCheckedChange={(checked) =>
                        handleConfigChange("enableChaining", checked)
                      }
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Allow multi-level approval chains in the workflow
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
          
          <CardFooter className="flex justify-end space-x-2 pt-6">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div>
                    <Button
                      variant="default"
                      disabled={!isFormValid() || isLoading || externalIsLoading}
                      onClick={uploadFileToBackend}
                      className="min-w-[120px]"
                    >
                      {isLoading || externalIsLoading ? (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          {!isFormValid() && (
                            <AlertCircle className="mr-2 h-4 w-4 text-yellow-500" />
                          )}
                          Process File
                        </>
                      )}
                    </Button>
                  </div>
                </TooltipTrigger>
                {!isFormValid() && !isLoading && !externalIsLoading && (
                  <TooltipContent>
                    <div className="max-w-xs">
                      <p className="font-semibold mb-1">Please fix the following issues:</p>
                      <ul className="list-disc pl-4 text-sm">
                        {!file && <li>Please select a file to upload</li>}
                        {!config.projectName.trim() && <li>Project name is required</li>}
                        {!config.projectDescription.trim() && <li>Project description is required</li>}
                        {config.headerRow <= 0 && <li>Header row must be greater than 0</li>}
                        {config.dataStartRow <= 0 && <li>Data start row must be greater than 0</li>}
                        {config.dataStartRow <= config.headerRow && <li>Data start row must be greater than header row</li>}
                        {file && (file.name.toLowerCase().endsWith('.xlsx') || file.name.toLowerCase().endsWith('.xls')) && 
                          !config.selectedSheet.trim() && <li>Sheet name is required for Excel files</li>}
                        {!config.mcwId.trim() && <li>MCW ID is required</li>}
                        {config.mcwId.trim() && !/^ALT\d+$/.test(config.mcwId.trim()) && <li>MCW ID must start with 'ALT' followed by numbers (e.g., ALT0001)</li>}
                        {!config.mcwTitle.trim() && <li>MCW Title is required</li>}
                        {!config.mcwProcess.trim() && <li>MCW Process is required</li>}
                        {!config.wcmCurrency.trim() && <li>WCM Currency is required</li>}
                        {!config.wcmDocument.trim() && <li>WCM Document is required</li>}
                        {!config.wcmStartConditionId.trim() && <li>WCM Start Condition ID is required</li>}
                        {config.wcmStartConditionId.trim() && !/^WC\d+$/.test(config.wcmStartConditionId.trim()) && <li>WCM Start Condition ID must start with 'WC' followed by numbers (e.g., WC00001)</li>}
                        {config.wcmConditionKeys.length === 0 && <li>At least one condition key is required</li>}
                        {config.wcmConditionKeys.some(key => !key.trim()) && <li>All condition keys must be filled</li>}
                      </ul>
                    </div>
                  </TooltipContent>
                )}
              </Tooltip>
            </TooltipProvider>
          </CardFooter>
        </Card>
        )}
      </div>
    </div>
  );
};

export default UploadTab;
