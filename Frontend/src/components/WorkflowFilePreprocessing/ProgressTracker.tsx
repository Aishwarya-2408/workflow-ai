import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Download, CheckCircle, Clock, Play } from "lucide-react";

interface ProgressTrackerProps {
  isProcessing: boolean;
  progress: number;
  isCompleted: boolean;
}

export function ProgressTracker({ isProcessing, progress, isCompleted }: ProgressTrackerProps) {
  const handleDownload = () => {
    // Simulate file download
    const link = document.createElement('a');
    link.href = '#';
    link.download = 'processed_results.xlsx';
    link.click();
    
    // You could also create a blob with actual processed data:
    // const blob = new Blob([processedData], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    // const url = URL.createObjectURL(blob);
    // link.href = url;
    // link.download = 'processed_results.xlsx';
    // link.click();
    // URL.revokeObjectURL(url);
  };

  return (
    <Card className="p-6">
      <h3 className="text-sm font-medium mb-3">Progress of Execution</h3>
      <p className="text-xs text-muted-foreground mb-4">
        Once processing is completed successfully, download file option will be available.
      </p>
      
      {!isProcessing && !isCompleted && (
        <div className="flex items-center gap-2 text-gray-500">
          <Clock className="w-4 h-4" />
          <span className="text-sm">Waiting to start processing...</span>
        </div>
      )}
      
      {isProcessing && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-8 h-8 bg-blue-500 rounded-full">
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
              Download Processed Results
            </Button>
          </div>
        </div>
      )}
    </Card>
  );
} 