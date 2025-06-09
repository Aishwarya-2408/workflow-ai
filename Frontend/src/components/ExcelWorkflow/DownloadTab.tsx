import React, { useState, useEffect } from "react";
import { Download, FileDown, FileUp, RefreshCw } from "lucide-react";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardFooter,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
import { useToast } from "@/components/ui/use-toast";
import { downloadFile, downloadAllFiles } from "@/services/api";

interface DownloadOption {
  id: string;
  name: string;
  description: string;
  format: string;
  icon: React.ReactNode;
}

interface DownloadTabProps {
  projectName?: string;
  downloadOptions?: DownloadOption[];
  onDownload?: (optionId: string) => void;
  onNewProject?: () => void;
  isProcessing?: boolean;
  onDownloadComplete?: () => void;
  onPrevious?: () => void;
  filePaths?: {
    mcw_file?: string;
    wcm_file?: string;
    metadata_file?: string;
  };
}

const DownloadTab: React.FC<DownloadTabProps> = ({
  downloadOptions = [
    {
      id: "mcw-file",
      name: "MCW File",
      description: "Download the Master Control Workflow mapping in Excel format",
      format: "XLSX",
      icon: <FileDown className="h-5 w-5" />,
    },
    {
      id: "wcm-file",
      name: "WCM File",
      description: "Download the Workflow Control Matrix mapping in Excel format",
      format: "XLSX",
      icon: <FileDown className="h-5 w-5" />,
    },
  ],
  onDownload = () => {},
  onNewProject = () => {},
  isProcessing = false,
  onDownloadComplete = () => {},
  onPrevious = () => {},
  filePaths = {},
}) => {
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [downloadComplete, setDownloadComplete] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const { toast } = useToast();

  // Log file paths when component mounts for debugging
  useEffect(() => {
    console.log("DownloadTab received file paths:", filePaths);
  }, [filePaths]);

  // Set downloadComplete to true when the component mounts
  useEffect(() => {
    // Only set to true if not processing
    if (!isProcessing) {
      setDownloadComplete(true);
    }
  }, [isProcessing]);

  const handleDownloadClick = async (optionId: string) => {
    setSelectedOption(optionId);
    
    // Determine which file to download based on the option ID
    let filePath = '';
    if (optionId === 'mcw-file' && filePaths.mcw_file) {
      filePath = filePaths.mcw_file;
    } else if (optionId === 'wcm-file' && filePaths.wcm_file) {
      filePath = filePaths.wcm_file;
    }
    
    // If we have a file path, trigger the download
    if (filePath) {
      // Extract the filename from the path for the download
      const filename = filePath.split('/').pop() || filePath.split('\\').pop() || `${optionId}.xlsx`;
      
      try {
        // Reset error state
        setDownloadError(null);
        
        // Call the centralized API function
        const result = await downloadFile(filePath, filename);
        
        if (result.status === 'error') {
          throw new Error(result.message);
        }
        
        // Show success toast
        toast({
          title: "Download Successful",
          description: `${filename} has been downloaded successfully.`,
          variant: "default",
        });
        
        setDownloadComplete(true);
        onDownload(optionId);
        onDownloadComplete();
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Download failed';
        console.error('Download error:', error);
        setDownloadError(errorMessage);
        
        // Show error toast
        toast({
          title: "Download Failed",
          description: errorMessage,
          variant: "destructive",
        });
      }
    }
  };

  const handleDownloadAll = async () => {
    // Check if we have any files to download
    if (filePaths.mcw_file || filePaths.wcm_file || filePaths.metadata_file) {
      try {
        // Reset error state
        setDownloadError(null);
        
        // Use the centralized downloadAllFiles function
        const result = await downloadAllFiles(filePaths);
        
        if (result.status === 'error') {
          throw new Error(result.message);
        }
        
        // Show success toast
        toast({
          title: "Download Successful",
          description: `All files have been downloaded successfully.`,
          variant: "default",
        });
        
        setDownloadComplete(true);
        onDownloadComplete();
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Download failed';
        console.error('Download error:', error);
        setDownloadError(errorMessage);
        
        // Show error toast
        toast({
          title: "Download Failed",
          description: errorMessage,
          variant: "destructive",
        });
      }
    }
  };

  const handleNewProject = () => {
    setShowConfirmDialog(true);
  };

  const confirmNewProject = () => {
    onNewProject();
    setShowConfirmDialog(false);
    setDownloadComplete(false);
  };

  return (
    <div className="w-full h-full p-6 bg-gray-50">
      <Card className="w-full max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle className="text-2xl">
            Download Standardized Workflow
          </CardTitle>
        </CardHeader>

        <CardContent>
          <div className="space-y-6">
            {downloadError ? (
              <div className="p-4 bg-red-50 border border-red-200 rounded-md">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-red-400"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">
                      Download Error
                    </h3>
                    <div className="mt-2 text-sm text-red-700">
                      <p>{downloadError}</p>
                      <p className="mt-1">Please try again or contact support if the issue persists.</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-4 bg-green-50 border border-green-200 rounded-md">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <svg
                      className="h-5 w-5 text-green-400"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 20 20"
                      fill="currentColor"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-green-800">
                      Transformation Complete
                    </h3>
                    <div className="mt-2 text-sm text-green-700">
                      <p>
                        Your file has been generated successfully. You can
                        download the files or start a new project.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}
            {isProcessing ? (
              <div className="flex flex-col items-center justify-center py-12">
                <RefreshCw className="h-12 w-12 text-primary animate-spin mb-4" />
                <h3 className="text-lg font-medium">
                  Preparing Files for Download
                </h3>
                <p className="text-muted-foreground">
                  This may take a few moments...
                </p>
              </div>
            ) : (
              <>
                <h3 className="text-lg font-medium">
                  Available Download Options
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {downloadOptions.map((option) => (
                    <Card
                      key={option.id}
                      className={`cursor-pointer transition-all hover:shadow-md ${selectedOption === option.id ? "ring-2 ring-primary" : ""}`}
                      onClick={() => handleDownloadClick(option.id)}
                    >
                      <CardContent className="p-6">
                        <div className="flex items-start space-x-4">
                          <div className="p-2 rounded-full bg-primary/10 text-primary">
                            {option.icon}
                          </div>
                          <div className="flex-1">
                            <h4 className="font-medium">{option.name}</h4>
                            <p className="text-sm text-muted-foreground">
                              {option.description}
                            </p>
                            <div className="mt-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-secondary text-secondary-foreground">
                              {option.format}
                            </div>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </>
            )}
          </div>
        </CardContent>

        <CardFooter className="flex justify-between border-t pt-6">
          <div className="space-x-3">
            <Button variant="outline" onClick={onPrevious} disabled={isProcessing}>
              Back to Tree
            </Button>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" onClick={handleNewProject}>
                    <FileUp className="mr-2 h-4 w-4" />
                    Start New Project
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Upload a new file and start a fresh workflow</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>

          {/* Temporarily removed the "Download All Files" button */}
          {/*\n\
          <TooltipProvider>\n\
            <Tooltip>\n\
              <TooltipTrigger asChild>\n\
                <Button \n\
                  disabled={!downloadComplete && !isProcessing}\n\
                  onClick={handleDownloadAll}\n\
                >\n\
                  <Download className="mr-2 h-4 w-4" />\n\
                  Download All Files\n\
                </Button>\n\
              </TooltipTrigger>\n\
              <TooltipContent>\n\
                <p>Download all available files in a single click</p>\n\
              </TooltipContent>\n\
            </Tooltip>\n\
          </TooltipProvider>\n\
          */}
        </CardFooter>
      </Card>

      <Dialog open={showConfirmDialog} onOpenChange={setShowConfirmDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Start a New Project?</DialogTitle>
          </DialogHeader>
          <p className="text-muted-foreground">
            Are you sure you want to start a new project? Any unsaved changes
            will be lost.
          </p>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={confirmNewProject}>Confirm</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DownloadTab;
