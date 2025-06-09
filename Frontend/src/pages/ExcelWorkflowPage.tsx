import React, { useState, useEffect, useCallback } from "react";
// import WorkflowHeader from "../components/workflow/WorkflowHeader"; // Removed import
import WorkflowTabs from "../components/ExcelWorkflow/WorkflowTabs"; // Adjusted path
import UploadTab from "../components/ExcelWorkflow/UploadTab"; // Adjusted path
import ValidationTab from "../components/ExcelWorkflow/ValidationTab"; // Adjusted path
import TreeTab from "../components/ExcelWorkflow/TreeTab"; // Adjusted path
import DownloadTab from "../components/ExcelWorkflow/DownloadTab"; // Adjusted path
import ProcessingIndicator from "../components/ExcelWorkflow/ProcessingIndicator"; // Adjusted path
import { useToast } from "@/components/ui/use-toast"; // Keep path if alias is configured
import { GlobalStyleFix } from "../components/layout/Layout"; // Import the GlobalStyleFix component

type WorkflowStage = "upload" | "validation" | "tree" | "download";
type ProcessingStage =
  | "extracting"
  | "validating"
  | "generating"
  | "complete"
  | "error";
type TabStatus = "current" | "upcoming" | "completed" | "error";

// Interface for validation data from backend
interface ValidationData {
  levels: Record<string, { name: string; description: string }>;
  conditions: Record<string, any>;
  mapping: Record<string, string[]>;
}

const ExcelWorkflowPage = () => { // Renamed component
  const { toast } = useToast();
  const [currentStage, setCurrentStage] = useState<WorkflowStage>("upload");
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] =
    useState<ProcessingStage>("extracting");
  const [processingError, setProcessingError] = useState<string>("");
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [treeData, setTreeData] = useState<any>(null);
  const [filePaths, setFilePaths] = useState<{
    mcw_file?: string;
    wcm_file?: string;
  }>({});
  const [projectId, setProjectId] = useState<string>("");

  // State for validation data from backend
  const [extractedData, setExtractedData] = useState<ValidationData>({
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
  });

  // Workflow tabs configuration
  const getTabStatus = useCallback((tabId: WorkflowStage): TabStatus => {
    const stageOrder = ["upload", "validation", "tree", "download"];
    const currentIndex = stageOrder.indexOf(currentStage);
    const tabIndex = stageOrder.indexOf(tabId);

    // Special case: if files are ready for download and we are on the download tab
    if (tabId === "download" && (filePaths.mcw_file || filePaths.wcm_file) && currentStage === "download") {
       return "completed"; // Mark as completed if files are available
     }

    // If this is the current tab
    if (tabId === currentStage) {
      return "current";
    }

    // If this tab comes before the current tab
    if (tabIndex < currentIndex) {
      return "completed";
    }

    // If this tab comes after the current tab
    return "upcoming";
  }, [currentStage, filePaths]);

  const [workflowTabs, setWorkflowTabs] = useState([
    {
      id: "upload",
      label: "Upload",
      status: getTabStatus("upload"),
      description: "Upload your workflow files here",
    },
    {
      id: "validation",
      label: "Validation",
      status: getTabStatus("validation"),
      description: "Validate your workflow data",
    },
    {
      id: "tree",
      label: "Tree",
      status: getTabStatus("tree"),
          description: "View and edit your workflow structure",
    },
    {
      id: "download",
      label: "Download",
      status: getTabStatus("download"),
      description: "Download your completed workflow files",
    },
  ]);

  // Update workflow tabs when current stage or file paths change
  useEffect(() => {
    const updatedTabs = [
      {
        id: "upload",
        label: "Upload",
        status: getTabStatus("upload"),
        description: "Upload your workflow files here",
      },
      {
        id: "validation",
        label: "Validation",
        status: getTabStatus("validation"),
        description: "Validate your workflow data",
      },
      {
        id: "tree",
        label: "Tree",
        status: getTabStatus("tree"),
          description: "View and edit your workflow structure",
      },
      {
        id: "download",
        label: "Download",
        status: getTabStatus("download"),
        description: "Download your completed workflow files",
      },
    ];

    setWorkflowTabs(updatedTabs);
  }, [currentStage, filePaths, getTabStatus]);

  // Handle file upload
  const handleFileUpload = (file: File) => {
    setUploadedFile(file);
  };

  // Handle validation data received from backend (from UploadTab initially)
  const handleInitialValidationDataReceived = (data: ValidationData) => {
    setExtractedData(data);
    toast({
      title: "Data Extracted",
      description: "Initial validation data has been extracted from the file.",
      duration: 3000,
    });
    // Proceed to validation stage after successful extraction
    setCurrentStage("validation");
  };

  // Handle tree data received from backend (from ValidationTab)
  const handleTreeDataReceived = (data: any) => {
    // First set the data
    setTreeData(data);
    
    // Set processing to "complete" to show success animation
    setProcessingStage("complete");
    
    // Wait for the animation to fully complete before proceeding
    setTimeout(() => {
      // Hide the loader
      setIsProcessing(false);
      
      // Change the stage
      setCurrentStage("tree");
      
      // Show toast after tab transition is visually complete
      setTimeout(() => {
        toast({
          title: "Tree Data Ready",
          description: "Workflow tree structure has been generated.",
          duration: 3000,
        });
      }, 100);
    }, 2000);
  };

  // Handle file paths received from backend (from TreeTab)
  const handleFilePathsReceived = (paths: { mcw_file?: string; wcm_file?: string }) => {
    // First set the data
    setFilePaths(paths);
    
    // Set processing to "complete" to show success animation
    setProcessingStage("complete");
    
    // Wait for the animation to fully complete before proceeding
    setTimeout(() => {
      // Hide the loader
      setIsProcessing(false);
      
      // Change the stage
      setCurrentStage("download");
      
      // Show toast after tab transition is visually complete
      setTimeout(() => {
        toast({
          title: "Files Generated",
          description: "MCW and WCM files have been generated successfully.",
          duration: 3000,
        });
      }, 100);
    }, 2000);
  };

  // Handle tab change - THIS IS NOW DISABLED in WorkflowTabs component visually
  // Kept for potential future use or internal state management if needed
  const handleTabChange = (tabId: WorkflowStage) => {
     console.log(`Attempted to change tab to ${tabId}, but direct navigation is disabled.`);
    // setCurrentStage(tabId); // Don't change stage directly on tab click
  };

  // Handle data changes in validation tab
  const handleDataChange = (type: string, data: any) => {
    setExtractedData((prev) => ({
      ...prev,
      [type]: data,
    }));
  };

  // Handle download completion callback from DownloadTab (used to update UI if needed)
  const handleDownloadComplete = () => {
    console.log("Download process initiated by DownloadTab.");
    // No need to set downloadCompleted state here anymore
    // The getTabStatus function now checks filePaths to determine completion status
  };

  // Set Project ID
  const handleSetProjectId = (id: string) => {
    setProjectId(id);
    toast({
      title: "Project ID Set",
      description: `Project ID set to: ${id}`,
      duration: 3000,
    });
  };

  // Handle back navigation
  const handleBackNavigation = (previousStage: WorkflowStage) => {
    setCurrentStage(previousStage);
  };

  // Handle new project
  const handleStartNewProject = () => {
    // Reset all state to start a new project
    setUploadedFile(null);
    setTreeData(null);
    setFilePaths({});
    setProjectId("");
    setExtractedData({
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
    });
    
    // Navigate back to upload stage
    setCurrentStage("upload");
    
    toast({
      title: "New Project",
      description: "Started a new workflow project",
      duration: 3000,
    });
  };

  // Handle processing errors
  const handleProcessingError = (error: string, stage: ProcessingStage) => {
    setIsProcessing(false);
    setProcessingError(error);
    setProcessingStage(stage); // Keep track of where the error occurred
    toast({
      title: `Error during ${stage}`,
      description: error || "An unknown error occurred.",
      variant: "destructive",
      duration: 5000,
    });
    // Optionally update tab status to 'error'
    setWorkflowTabs(prevTabs => prevTabs.map(tab =>
      tab.id === currentStage ? { ...tab, status: 'error' } : tab
    ));
  };

  // Handle setting the processing stage (for UI indicator)
  const handleSetProcessingStage = (stage: ProcessingStage) => {
    setProcessingStage(stage);
    setProcessingError(""); // Clear previous errors when starting a new stage
    if (stage !== 'complete' && stage !== 'error') {
      setIsProcessing(true); // Set processing to true when a stage starts
    } else if (stage === 'error') {
      setIsProcessing(true); // Keep processing true for error state so it's visible
    } else {
      // For 'complete' state, keep processing true initially 
      // (will be set to false after transition animation by onComplete callback)
      setIsProcessing(true);
    }
  };

  // Render the content based on the current stage
  const renderStageContent = () => {
    switch (currentStage) {
      case "upload":
        return (
          <UploadTab
            // Removed onProceed - stage transition handled by handleInitialValidationDataReceived
            setProjectId={handleSetProjectId} // Corrected prop name
            onFileUpload={handleFileUpload} // Changed from onFileSelect
            setIsProcessing={setIsProcessing} // Pass down setIsProcessing
            onValidationDataReceived={handleInitialValidationDataReceived} // Use this to get data and move stage
            setProcessingError={(err) => handleProcessingError(err, 'extracting')} // Pass error handler specific to this stage
            setProcessingStage={handleSetProcessingStage} // Pass down the handler
          />
        );
      case "validation":
        return (
          <ValidationTab
            extractedData={extractedData}
            onDataChange={handleDataChange}
            // Removed onProceed - stage transition handled by handleTreeDataReceived
            onBack={() => handleBackNavigation("upload")} // Add back navigation
            setIsProcessing={setIsProcessing} // Pass down setIsProcessing
            onTreeDataReceived={handleTreeDataReceived} // Use this to get data and move stage
            setProcessingError={(err) => handleProcessingError(err, 'validating')} // Pass error handler specific to this stage
            setProcessingStage={handleSetProcessingStage} // Pass down the handler
            projectId={projectId} // Pass projectId
          />
        );
      case "tree":
        return (
          <TreeTab
            treeData={treeData} // Pass tree data if available
            // Removed onProceed - stage transition handled by handleFilePathsReceived
            onPrevious={() => handleBackNavigation("validation")} // Add back navigation
            onNext={() => {
                setCurrentStage('download');
            }}
            // Removed onTreeUpdate - using onNext for stage progression
            setIsProcessing={setIsProcessing} // Pass down setIsProcessing
            setProcessingError={(err) => handleProcessingError(err, 'generating')} // Pass error handler specific to this stage
            setProcessingStage={handleSetProcessingStage} // Pass down the handler
            projectId={projectId} // Pass projectId
            onFilePathsReceived={handleFilePathsReceived} // Keep this for the actual data transfer
          />
        );
      case "download":
        return (
          <DownloadTab
            filePaths={filePaths} // Pass file paths if available
            onDownloadComplete={handleDownloadComplete} // Pass the handler
            onNewProject={handleStartNewProject} // Add new project handler
            onPrevious={() => handleBackNavigation("tree")} // Add back navigation to the tree tab
            // Removed isCompleted prop
            // Removed processing handlers, DownloadTab handles its own download state
            // isProcessing={isProcessing} // Can optionally pass this if DownloadTab needs general processing state
          />
        );
      default:
        return <div>Unknown stage</div>;
    }
  };

  return (
    // Removed wrapping div and WorkflowHeader
    <>
      <GlobalStyleFix />
      <WorkflowTabs
        tabs={workflowTabs}
        activeTab={currentStage} // Corrected prop name
        // onTabChange={handleTabChange} // Tab change is disabled in component
      />
      <div className="mt-6 relative">
        {isProcessing && (
          <div className="absolute inset-0 flex items-center justify-center z-50 bg-white">
            <ProcessingIndicator
              stage={processingStage}
              error={processingError}
              onComplete={() => {
                // Only auto-transition if we've completed successfully
                if (processingStage === 'complete') {
                  // The timeout gives user time to see the completion state
                  setTimeout(() => {
                    setIsProcessing(false);
                  }, 1500);
                }
              }}
              onDismissError={() => {
                setIsProcessing(false);
                setProcessingError("");
              }}
            />
          </div>
        )}
        {/* Apply overlay only when actively processing, not just on complete/error states */}
        <div className={isProcessing && processingStage !== 'complete' && processingStage !== 'error' ? "opacity-50 pointer-events-none" : ""}>
          {renderStageContent()}
        </div>
      </div>
    </>
  );
};

export default ExcelWorkflowPage; // Export the renamed component 