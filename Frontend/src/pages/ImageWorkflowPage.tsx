import React, { useState, useEffect } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";

// Import the image workflow components
import ImageUpload from "../components/ImageWorkflow/ImageUpload";
import UploadSuccess from "../components/ImageWorkflow/UploadSuccess";
import WorkflowDesign from "../components/ImageWorkflow/WorkflowDesign";
import GenerateOptions from "../components/ImageWorkflow/GenerateOptions";
import StepProgress from "../components/ImageWorkflow/StepProgress";

// Import WorkflowContext provider
import { WorkflowProvider } from "@/lib/WorkflowContext";

const ImageWorkflowPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [currentStep, setCurrentStep] = useState(0);

  // Update current step based on the URL path
  useEffect(() => {
    const path = location.pathname;
    
    if (path === "/workflow/image" || path === "/workflow/image/") {
      setCurrentStep(0);
    } else if (path === "/workflow/image/success" || path === "/workflow/image/message") {
      setCurrentStep(0);
    } else if (path === "/workflow/image/design") {
      setCurrentStep(1);
    } else if (path === "/workflow/image/generate") {
      setCurrentStep(2);
    }
  }, [location.pathname]);

  return (
    <WorkflowProvider>
      <div className="flex flex-col min-h-screen bg-slate-50">
        {/* Hide StepProgress on legacy URL path (for backward compatibility) */}
        {location.pathname !== "/workflow/image/uploadtab" && (
          <StepProgress currentStep={currentStep} />
        )}
        
        <div className="flex-1">
          <Routes>
            <Route index element={<ImageUpload />} />
            <Route path="success" element={<UploadSuccess />} />
            <Route path="design" element={<WorkflowDesign />} />
            <Route path="generate" element={<GenerateOptions />} />
            
            {/* Legacy routes for backward compatibility */}
            <Route 
              path="uploadtab" 
              element={
                <div className="p-4">
                  <div className="max-w-4xl mx-auto">
                    <h2 className="text-xl font-semibold mb-4">Legacy Upload Tab</h2>
                    <p>This is a legacy route. Please use the new image workflow UI at <a href="/workflow/image" className="text-blue-500 hover:underline">this link</a>.</p>
                    <button 
                      onClick={() => navigate("/workflow/image")}
                      className="mt-4 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                    >
                      Go to New UI
                    </button>
                  </div>
                </div>
              } 
            />
            
            {/* Fallback route to catch any unmatched paths */}
            <Route path="*" element={<ImageUpload />} />
          </Routes>
        </div>
      </div>
    </WorkflowProvider>
  );
};

export default ImageWorkflowPage; 