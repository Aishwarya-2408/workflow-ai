import React, { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle, ArrowRight, RotateCw, AlertTriangle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useWorkflow } from "@/lib/WorkflowContext";
import { processImage } from "@/services/api";

const UploadSuccess: React.FC = () => {
  const navigate = useNavigate();
  const { markStepCompleted } = useWorkflow();
  const [isProcessing, setIsProcessing] = useState(false);
  const [processComplete, setProcessComplete] = useState(false);
  const [processError, setProcessError] = useState<string | null>(null);
  const [imageMetadata, setImageMetadata] = useState<any>(null);
  const [processingProgress, setProcessingProgress] = useState(0);

  useEffect(() => {
    // Check if image metadata exists in localStorage
    const storedMetadata = localStorage.getItem("imageMetadata");
    if (!storedMetadata) {
      // If no metadata, redirect back to upload
      navigate("/workflow/image");
      return;
    }

    try {
      const metadata = JSON.parse(storedMetadata);
      setImageMetadata(metadata);
      
      // If already processed, show as complete
      if (metadata.processingComplete) {
        setProcessComplete(true);
        setProcessingProgress(100);
      }
    } catch (e) {
      console.error("Failed to parse image metadata", e);
      navigate("/workflow/image");
    }
  }, [navigate]);

  // Auto-start processing if not already complete
  useEffect(() => {
    if (imageMetadata && !imageMetadata.processingComplete && !isProcessing && !processComplete && !processError) {
      handleStartProcessing();
    }
  }, [imageMetadata]);

  const handleStartProcessing = async () => {
    if (!imageMetadata?.filename) {
      setProcessError("No image file to process. Please upload an image first.");
      return;
    }

    setIsProcessing(true);
    setProcessError(null);
    
    // Create progress animation
    let progress = 0;
    const progressInterval = setInterval(() => {
      progress += 5;
      if (progress >= 95) {
        clearInterval(progressInterval);
        setProcessingProgress(95);
      } else {
        setProcessingProgress(progress);
      }
    }, 200);

    try {
      const response = await processImage(imageMetadata.filename);
      
      clearInterval(progressInterval);
      
      if (response.success) {
        // Update the metadata with processing info
        const updatedMetadata = {
          ...imageMetadata,
          processingComplete: true,
          outputData: response.data || {},
          processedAt: new Date().toISOString()
        };
        
        localStorage.setItem("imageMetadata", JSON.stringify(updatedMetadata));
        setImageMetadata(updatedMetadata);
        setProcessComplete(true);
        setProcessingProgress(100);
        
        // Mark upload step as completed in workflow context
        markStepCompleted(0);
      } else {
        setProcessError(response.error || "Processing failed. Please try again.");
        setProcessingProgress(0);
      }
    } catch (error) {
      clearInterval(progressInterval);
      console.error("Error processing image:", error);
      setProcessError(error instanceof Error ? error.message : "Unknown error occurred during processing");
      setProcessingProgress(0);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleContinue = () => {
    navigate("/workflow/image/design");
  };

  const handleTryAgain = () => {
    setProcessError(null);
    handleStartProcessing();
  };

  const handleUploadNew = () => {
    navigate("/workflow/image");
  };

  return (
    <div className="py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <Card className="shadow-md border-slate-200">
          <CardContent className="p-8">
            <div className="flex flex-col items-center justify-center text-center space-y-6">
              {/* Success State */}
              {processComplete && (
                <>
                  <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center">
                    <CheckCircle className="h-10 w-10 text-green-600" />
                  </div>
                  <div className="space-y-2">
                    <h2 className="text-2xl font-bold text-slate-800">Image Successfully Processed!</h2>
                    <p className="text-slate-600 max-w-md mx-auto">
                      Your image has been analyzed and is ready for workflow design.
                      Continue to the next step to start designing your workflow.
                    </p>
                  </div>
                  <Button 
                    onClick={handleContinue}
                    className="bg-black hover:bg-gray-800 text-white"
                    size="lg"
                  >
                    Continue to Workflow Design
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </>
              )}
              
              {/* Processing State */}
              {isProcessing && (
                <>
                  <div className="w-20 h-20 rounded-full flex items-center justify-center relative">
                    <div className="absolute inset-0 rounded-full border-4 border-slate-200"></div>
                    <div 
                      className="absolute inset-0 rounded-full border-4 border-blue-500 border-t-transparent animate-spin"
                      style={{ 
                        clipPath: `polygon(0% 0%, 100% 0%, 100% ${processingProgress}%, 0% ${processingProgress}%)` 
                      }}
                    ></div>
                    <RotateCw className="h-8 w-8 text-blue-600 animate-spin" />
                  </div>
                  <div className="space-y-2">
                    <h2 className="text-2xl font-bold text-slate-800">Processing Your Image</h2>
                    <p className="text-slate-600 max-w-md mx-auto">
                      We're analyzing your image to identify workflow elements.
                      This may take a few moments...
                    </p>
                  </div>
                  <div className="w-full max-w-md h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 transition-all duration-300"
                      style={{ width: `${processingProgress}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-slate-500">Please don't close this window</p>
                </>
              )}
              
              {/* Error State */}
              {processError && (
                <>
                  <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center">
                    <AlertTriangle className="h-10 w-10 text-red-600" />
                  </div>
                  <div className="space-y-2">
                    <h2 className="text-2xl font-bold text-slate-800">Processing Error</h2>
                    <p className="text-red-600 max-w-md mx-auto">
                      {processError}
                    </p>
                    <p className="text-slate-600 max-w-md mx-auto">
                      There was a problem processing your image. You can try again or upload a different image.
                    </p>
                  </div>
                  <div className="flex flex-col sm:flex-row gap-4">
                    <Button 
                      onClick={handleTryAgain}
                      variant="outline"
                      className="border-slate-200"
                    >
                      <RotateCw className="mr-2 h-4 w-4" />
                      Try Again
                    </Button>
                    <Button 
                      onClick={handleUploadNew}
                      className="bg-black hover:bg-gray-800 text-white"
                    >
                      Upload New Image
                    </Button>
                  </div>
                </>
              )}

              {/* Initial empty state */}
              {!isProcessing && !processComplete && !processError && (
                <>
                  <div className="w-20 h-20 bg-blue-100 rounded-full flex items-center justify-center">
                    <RotateCw className="h-10 w-10 text-blue-600" />
                  </div>
                  <div className="space-y-2">
                    <h2 className="text-2xl font-bold text-slate-800">Preparing Image Analysis</h2>
                    <p className="text-slate-600 max-w-md mx-auto">
                      Your image upload was successful. We'll begin processing it shortly.
                    </p>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Preview of uploaded image */}
        {imageMetadata?.imageUrl && (
          <div className="mt-8">
            <h3 className="text-xl font-semibold text-slate-700 mb-4">Your Uploaded Image</h3>
            <div className="border rounded-lg overflow-hidden">
              <img 
                src={imageMetadata.imageUrl} 
                alt="Uploaded Image" 
                className="w-full h-auto object-contain max-h-[500px]"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default UploadSuccess; 