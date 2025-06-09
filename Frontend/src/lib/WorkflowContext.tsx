import React, { createContext, useState, useContext, useEffect } from "react";

// Create a context for tracking workflow steps
interface WorkflowContextType {
  currentStep: number;
  setCurrentStep: (step: number) => void;
  completedSteps: boolean[];
  markStepCompleted: (step: number) => void;
}

const WorkflowContext = createContext<WorkflowContextType>({
  currentStep: 0,
  setCurrentStep: () => {},
  completedSteps: [false, false, false],
  markStepCompleted: () => {},
});

export const useWorkflow = () => useContext(WorkflowContext);

export const WorkflowProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState([false, false, false]);

  // Load completed steps from localStorage when the component mounts
  useEffect(() => {
    // Initialize based on actual progress indicators
    const uploadedImage = localStorage.getItem("uploadedImage");
    const workflowCompleted = localStorage.getItem("workflowCompleted");
    const hasGeneratedFiles = localStorage.getItem("hasGeneratedFiles");
    
    // Initialize the completed steps based on explicit completion markers
    const initialCompletedSteps = [
      !!uploadedImage, // Step 0 (Upload Image) is complete only if there's an uploaded image
      workflowCompleted === "true", // Step 1 (Design Workflow) is only complete if explicitly marked
      hasGeneratedFiles === "true" // Step 2 (Generate Files) is complete only if files were generated
    ];
    
    setCompletedSteps(initialCompletedSteps);
    
    // Update localStorage with correct values
    localStorage.setItem("completedSteps", JSON.stringify(initialCompletedSteps));
  }, []);

  const markStepCompleted = (step: number) => {
    setCompletedSteps(prev => {
      const updated = [...prev];
      updated[step] = true;
      
      // Save completed steps to localStorage for persistence
      localStorage.setItem("completedSteps", JSON.stringify(updated));
      
      return updated;
    });
  };

  return (
    <WorkflowContext.Provider 
      value={{ 
        currentStep, 
        setCurrentStep, 
        completedSteps, 
        markStepCompleted 
      }}
    >
      {children}
    </WorkflowContext.Provider>
  );
};

export default WorkflowContext; 