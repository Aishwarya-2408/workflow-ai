import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Download, CheckCircle, Clock, Play, XCircle } from "lucide-react";

interface ProgressTrackerProps {
  isProcessing: boolean;
  progress: number;
  isCompleted: boolean;
  downloadUrl: string | null;
  downloadFilename: string | null;
  errorMessage: string | null;
}

export function ProgressTracker({ isProcessing, progress, isCompleted, downloadUrl, downloadFilename, errorMessage }: ProgressTrackerProps) {
  console.log("ProgressTracker received progress:", progress);

  const handleDownload = async () => {
    if (!downloadUrl || !downloadFilename) {
      console.error("Download URL or filename not available.");
      return;
    }

    try {
      const response = await fetch(downloadUrl);
      if (!response.ok) {
        console.error("Failed to download file:", response.status, response.statusText);
        return;
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = downloadFilename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      console.log("File downloaded successfully.");
    } catch (error) {
      console.error("Error during download:", error);
    }
  };

  return (
    <Card className="p-6">
      <h3 className="text-sm font-medium mb-3">Progress of Execution</h3>
      <p className="text-xs text-muted-foreground mb-4">
        Once processing is completed successfully, download file option will be available.
      </p>
      
      {!isProcessing && !isCompleted && !errorMessage && (
        <div className="flex items-center gap-2 text-gray-500">
          <Clock className="w-4 h-4" />
          <span className="text-sm">Waiting to start processing...</span>
        </div>
      )}
      
      {errorMessage && !isProcessing && !isCompleted && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-red-600">
            <XCircle className="w-5 h-5 fill-red-600" />
            <span className="text-sm font-medium">Error Occurred:</span>
          </div>
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <p className="text-sm text-red-800 mb-3">
              {errorMessage}
            </p>
          </div>
        </div>
      )}
      
      {isProcessing && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-600 rounded-full">
              <Play className="w-4 h-4 text-white fill-white" />
            </div>
            <span className="text-sm font-medium">Processing request...</span>
          </div>
          
          <div className="space-y-2">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${progress}%` }}
              ></div>
            </div>
            <p className="text-xs text-blue-600 font-medium">
              {progress}% complete
            </p>
          </div>
        </div>
      )}
      
      {isCompleted && (
        <div className="space-y-4">
          {downloadUrl && downloadFilename ? (
            <>
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Processing completed successfully!</span>
              </div>
              <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                <p className="text-sm text-green-800 mb-3">
                  Your files have been processed and results are ready for download.
                </p>
                <Button onClick={handleDownload} className="w-full bg-green-600 hover:bg-green-700">
                  <Download className="w-4 h-4 mr-2" />
                  Download Processed Results ({downloadFilename})
                </Button>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 text-yellow-600">
                <CheckCircle className="w-5 h-5" />
                <span className="text-sm font-medium">Processing completed.</span>
              </div>
              <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                <p className="text-sm text-yellow-800">
                  The task finished, but no output files were generated for download.
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  );
} 