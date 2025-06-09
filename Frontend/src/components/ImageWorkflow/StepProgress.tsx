import React from "react";
import { CheckCircle, Circle } from "lucide-react";
import { useWorkflow } from "@/lib/WorkflowContext";

interface StepProgressProps {
  currentStep?: number;
}

const StepProgress: React.FC<StepProgressProps> = ({ currentStep: propCurrentStep }) => {
  // Use either the prop or context value (prop takes precedence if provided)
  const { currentStep: contextCurrentStep, completedSteps } = useWorkflow();
  const currentStep = propCurrentStep !== undefined ? propCurrentStep : contextCurrentStep;

  const steps = [
    { id: "upload", label: "Upload Image" },
    { id: "workflow", label: "Design Workflow" },
    { id: "generate", label: "Generate Files" },
  ];

  return (
    <div className="w-full py-4 px-6 border-b border-slate-200 bg-white">
      <div className="max-w-4xl mx-auto">
        <div className="relative">
          {/* Step connectors */}
          <div className="absolute top-5 left-0 right-0 flex justify-between items-center z-0">
            <div className="h-0.5 bg-slate-200 w-full absolute"></div>
            <div 
              className="h-0.5 bg-blue-500 absolute left-0 transition-all duration-300"
              style={{ 
                width: currentStep === 0 
                  ? '0%' 
                  : currentStep === 1 
                    ? '50%'
                    : completedSteps[2] ? '100%' : '50%'
              }}
            ></div>
          </div>

          {/* Steps */}
          <div className="flex justify-between relative z-10">
            {steps.map((step, index) => (
              <div key={step.id} className="flex flex-col items-center">
                <div className="flex items-center justify-center mb-2">
                  {completedSteps[index] ? (
                    <CheckCircle className="h-10 w-10 text-blue-500 bg-white rounded-full" />
                  ) : index === currentStep ? (
                    <div className="h-10 w-10 rounded-full bg-blue-500 text-white flex items-center justify-center">
                      <Circle className="h-5 w-5 fill-current" />
                    </div>
                  ) : (
                    <div className="h-10 w-10 rounded-full border-2 border-slate-200 bg-white flex items-center justify-center text-slate-400">
                      <span className="text-sm font-medium">{index + 1}</span>
                    </div>
                  )}
                </div>
                <span className={`text-sm font-medium ${
                  index === currentStep ? 'text-blue-600' : 
                  completedSteps[index] ? 'text-slate-700' : 'text-slate-400'
                }`}>
                  {step.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default StepProgress; 