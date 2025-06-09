import React, { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Upload, Image as ImageIcon, X } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useWorkflow } from "@/lib/WorkflowContext";
import { Progress } from "@/components/ui/progress";
import { uploadImage, API_BASE_URL } from "@/services/api";

const ImageUpload: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedImageUrl, setUploadedImageUrl] = useState<string | null>(null);
  const [previewImage, setPreviewImage] = useState<string | null>(null);
  const [isFirstVisit, setIsFirstVisit] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { markStepCompleted, completedSteps } = useWorkflow();

  // Check if we already have a completed upload from before
  const hasCompletedUpload = completedSteps[0];

  // Load existing image from localStorage only if user is returning to change it
  useEffect(() => {
    // Check if user is coming back from upload-success page
    const referrer = document.referrer;
    const isReturningUser = 
      referrer.includes('/workflow/image/success') || 
      referrer.includes('/workflow/image/message') ||
      referrer.includes('/workflow/image/design') || 
      sessionStorage.getItem('returningUser') === 'true';
    
    if (isReturningUser) {
      setIsFirstVisit(false);
      sessionStorage.setItem('returningUser', 'true');
      
      // Get stored image metadata from localStorage
      const imageMetadata = localStorage.getItem("imageMetadata");
      if (imageMetadata) {
        const metadata = JSON.parse(imageMetadata);
        setUploadedImageUrl(metadata.imageUrl);
        // For the preview we'll use the server image URL
        setPreviewImage(metadata.imageUrl);
        // Only mark step as completed if there is an actual image
        markStepCompleted(0);
      }
    } else {
      // If it's a fresh visit, don't show the previous image
      setIsFirstVisit(true);
      sessionStorage.removeItem('returningUser');
      setUploadedImageUrl(null);
      setPreviewImage(null);
      
      // Check if there's image metadata from a previous session
      const imageMetadata = localStorage.getItem("imageMetadata");
      if (imageMetadata) {
        const metadata = JSON.parse(imageMetadata);
        setUploadedImageUrl(metadata.imageUrl);
        setPreviewImage(metadata.imageUrl);
      }
    }
  }, [markStepCompleted]);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Immediately set uploading state
      setIsUploading(true);
      setUploadProgress(0);
      
      // Create a local preview
      const objectUrl = URL.createObjectURL(file);
      setPreviewImage(objectUrl);
      
      // Simulate gradual upload progress
      let simulatedProgress = 0;
      const progressInterval = setInterval(() => {
        // Make the progress curve accelerate then decelerate for realism
        const increment = simulatedProgress < 30 ? 2 :
                        simulatedProgress < 60 ? 3 :
                        simulatedProgress < 80 ? 2 : 0.5;
        
        simulatedProgress += increment;
        
        if (simulatedProgress >= 95) {
          clearInterval(progressInterval);
          // Cap at 95% until actually processed
          setUploadProgress(95);
        } else {
          setUploadProgress(Math.min(95, simulatedProgress));
        }
      }, 40); // Update every 40ms for smooth animation
      
      // Upload the file to the server
      uploadImage(file)
        .then(response => {
          // When upload is complete, show 100%
          clearInterval(progressInterval);
          setUploadProgress(100);
          
          if (response.success) {
            // Store image metadata in localStorage
            const imageMetadata = {
              filename: response.filename,
              outputFile: response.outputFile,
              imageUrl: `${API_BASE_URL}${response.imageUrl}`,
              timestamp: new Date().toISOString(),
              processingComplete: false
            };
            
            localStorage.setItem("imageMetadata", JSON.stringify(imageMetadata));
            // Don't store filename in localStorage, it's now in backend config_dict
            setUploadedImageUrl(`${API_BASE_URL}${response.imageUrl}`);
            
            // Reset all progress when a new image is uploaded
            localStorage.removeItem("workflowCompleted");
            localStorage.removeItem("lastWorkflowState");
            localStorage.removeItem("savedWorkflows");
            localStorage.removeItem("hasGeneratedFiles");
            localStorage.removeItem("workflowData");
            
            // Reset completedSteps array to only have the first step completed
            const resetSteps = [true, false, false];
            localStorage.setItem("completedSteps", JSON.stringify(resetSteps));
            
            // Mark only the first step as completed
            markStepCompleted(0);
            
            // Navigate directly to upload-success
            navigate("/workflow/image/success");
          } else {
            console.error('Upload failed:', response.error);
            setIsUploading(false);
            // Clean up the preview
            URL.revokeObjectURL(objectUrl);
          }
        })
        .catch(error => {
          clearInterval(progressInterval);
          console.error('Upload failed:', error);
          setIsUploading(false);
          // Clean up the preview
          URL.revokeObjectURL(objectUrl);
        });
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemoveImage = (e: React.MouseEvent) => {
    e.stopPropagation();
    localStorage.removeItem("imageMetadata");
    setUploadedImageUrl(null);
    setPreviewImage(null);
  };

  const handleContinue = () => {
    navigate("/workflow/image/success");
  };

  // Determine which image URL to display
  const displayImage = uploadedImageUrl || previewImage;

  return (
    <div className="py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {/* Left side - Image upload */}
          <div className="md:col-span-2">
            <div className="text-left mb-6">
              <h2 className="text-3xl font-bold mb-2 text-slate-800">Upload Your Image</h2>
              <p className="text-slate-600">
                Upload an image to start the workflow process. This will be used as a reference for designing your workflow.
              </p>
            </div>
            
            <Card className="shadow-md border-slate-200">
              <CardContent className="p-8">
                <div 
                  className="border-2 border-dashed rounded-lg p-8 transition-all duration-200 border-slate-300 hover:border-slate-400 bg-white relative"
                  onClick={handleUploadClick}
                >
                  {!isFirstVisit && displayImage ? (
                    <div className="text-center space-y-6">
                      <div className="flex justify-center">
                        <div className="relative">
                          <img 
                            src={displayImage} 
                            alt="Current upload" 
                            className="h-64 max-w-full object-contain rounded-md"
                          />
                          <button 
                            className="absolute top-2 right-2 bg-black/70 text-white p-1 rounded-full hover:bg-black"
                            onClick={handleRemoveImage}
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                      <div className="space-y-4">
                        <p className="text-slate-700 font-medium">Current image selected</p>
                        <div className="flex flex-col sm:flex-row justify-center gap-4">
                          <Button 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleUploadClick();
                            }}
                            variant="outline"
                            className="border-slate-200"
                          >
                            <Upload className="h-4 w-4 mr-2" />
                            Replace Image
                          </Button>
                          <Button 
                            onClick={(e) => {
                              e.stopPropagation();
                              handleContinue();
                            }}
                            className="bg-black hover:bg-gray-800 text-white"
                          >
                            Continue with This Image
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center space-y-6">
                      <div className="flex justify-center">
                        <div className="p-6 bg-slate-100 rounded-full">
                          <ImageIcon className="h-16 w-16 text-slate-500" />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <p className="text-slate-700 font-medium">Drag and drop your image here, or click to browse</p>
                        <p className="text-sm text-slate-500">Supports JPG, PNG, GIF up to 10MB</p>
                      </div>
                      <Button 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleUploadClick();
                        }}
                        className="bg-black hover:bg-gray-800 text-white text-sm px-6 py-5 h-auto rounded-md"
                        disabled={isUploading}
                        size="lg"
                      >
                        {isUploading ? "Uploading..." : "Select Image"}
                      </Button>
                    </div>
                  )}
                  
                  {isUploading && (
                    <div className="absolute inset-x-0 bottom-0 px-8 pb-6 pt-4 bg-white/80 backdrop-blur-sm">
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm font-medium text-slate-700">Uploading...</span>
                          <span className="text-sm font-medium text-slate-700">{Math.round(uploadProgress)}%</span>
                        </div>
                        <Progress value={uploadProgress} className="h-2" />
                      </div>
                    </div>
                  )}
                </div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  accept="image/*"
                />
              </CardContent>
            </Card>
          </div>
          
          {/* Right side - Instructions */}
          <div className="space-y-6">
            <div className="rounded-lg bg-blue-50 p-6 border border-blue-100">
              <h3 className="text-lg font-semibold text-blue-800 mb-2">How It Works</h3>
              <ol className="space-y-3 text-sm text-blue-700">
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-blue-600">1.</span>
                  <span>Upload a clear image of your workflow diagram or process</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-blue-600">2.</span>
                  <span>Our system will detect elements and analyze the workflow</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-blue-600">3.</span>
                  <span>Design and edit your workflow with our visual editor</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-blue-600">4.</span>
                  <span>Generate usable workflow files for your systems</span>
                </li>
              </ol>
            </div>
            
            <div className="rounded-lg bg-amber-50 p-6 border border-amber-100">
              <h3 className="text-lg font-semibold text-amber-800 mb-2">Best Practices</h3>
              <ul className="space-y-3 text-sm text-amber-700">
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-amber-600">•</span>
                  <span>Use clear, high-contrast images with minimal noise</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-amber-600">•</span>
                  <span>Ensure all text is legible and elements are distinct</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-amber-600">•</span>
                  <span>Standard workflow notation will yield better results</span>
                </li>
                <li className="flex gap-2">
                  <span className="font-bold flex-shrink-0 text-amber-600">•</span>
                  <span>Images with up to 20 elements work best</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImageUpload; 