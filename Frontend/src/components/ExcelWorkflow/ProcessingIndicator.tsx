import React, { useState, useEffect, useRef } from "react";
import { Progress } from "@/components/ui/progress";
import { Card } from "@/components/ui/card";
import { Loader2, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

type ProcessingStage =
  | "extracting"
  | "validating"
  | "generating"
  | "complete"
  | "error";

interface ProcessingIndicatorProps {
  stage?: ProcessingStage;
  progress?: number;
  message?: string;
  error?: string;
  onComplete?: () => void;
  onDismissError?: () => void;
}

const ProcessingIndicator = ({
  stage = "extracting",
  progress = 0,
  message = "Processing your data...",
  error = "",
  onComplete = () => {},
  onDismissError = () => {},
}: ProcessingIndicatorProps) => {
  const [currentProgress, setCurrentProgress] = useState(progress);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastUpdateTimeRef = useRef<number>(Date.now());
  const isCompletingRef = useRef<boolean>(false);
  const [milestoneStep, setMilestoneStep] = useState(0);
  const [milestones, setMilestones] = useState<number[]>([]);
  const originalStageRef = useRef<ProcessingStage>(stage);

  // Track the original stage for step indicators
  useEffect(() => {
    // Only update original stage if not completing and not in error state
    if (stage !== "complete" && stage !== "error") {
      originalStageRef.current = stage;
    }
  }, [stage]);

  // Generate a random number within a specific range
  const getRandomInRange = (min: number, max: number) => {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  };

  // Get next milestone based on current progress
  const getNextMilestone = (current: number): number => {
    if (current < 30) return getRandomInRange(31, 40);
    if (current < 50) return getRandomInRange(51, 60);
    if (current < 70) return getRandomInRange(71, 80);
    if (current < 85) return getRandomInRange(86, 90);
    return getRandomInRange(91, 98);
  };

  // Clear all timers
  const clearAllTimers = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  // Process the next milestone with a visible delay
  useEffect(() => {
    if (milestones.length > 0 && milestoneStep < milestones.length) {
      // Set the current progress to the current milestone
      setCurrentProgress(milestones[milestoneStep]);
      
      // Schedule the next milestone after a delay
      const delay = milestoneStep === milestones.length - 1 ? 2000 : 800;
      
      timeoutRef.current = setTimeout(() => {
        if (milestoneStep === milestones.length - 1) {
          // If this was the last milestone (100%), call onComplete
          onComplete();
        } else {
          // Otherwise, move to the next milestone
          setMilestoneStep(prev => prev + 1);
        }
      }, delay);
      
      return () => {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
      };
    }
  }, [milestones, milestoneStep, onComplete]);

  // Initialize or update the loading animation based on stage changes
  useEffect(() => {
    clearAllTimers();
    
    if (stage === "complete" && !isCompletingRef.current) {
      // When transitioning to complete, set up milestones to 100%
      isCompletingRef.current = true;
      
      // Generate milestone percentages
      const newMilestones: number[] = [];
      let currentValue = currentProgress;
      
      // If already at or above 87%, just add one milestone before 100%
      if (currentValue >= 87) {
        newMilestones.push(getRandomInRange(91, 98));
      } else {
        // Add 2-3 clear milestones between current progress and 100%
        const numMilestones = Math.min(3, Math.max(2, Math.floor((100 - currentValue) / 15)));
        
        for (let i = 0; i < numMilestones; i++) {
          currentValue = getNextMilestone(currentValue);
          newMilestones.push(currentValue);
        }
      }
      
      // Always end with 100%
      newMilestones.push(100);
      
      // Set the milestones and reset the step counter
      setMilestones(newMilestones);
      setMilestoneStep(0);
    } else if (stage !== "error" && stage !== "complete" && progress === 0 && !isCompletingRef.current) {
      // Start with a slower progression for normal loading
      lastUpdateTimeRef.current = Date.now();
      
      intervalRef.current = setInterval(() => {
        setCurrentProgress((prev) => {
          // Slower progression that stops at 87%
          const increment = 
            prev < 20 ? 0.8 : 
            prev < 40 ? 0.6 : 
            prev < 60 ? 0.4 : 
            prev < 75 ? 0.3 : 
            prev < 85 ? 0.2 : 0.1;
          
          // Cap at 87% during normal loading
          const newProgress = Math.min(prev + increment, 87);
          return newProgress;
        });
      }, 900); // Even slower interval
    } else if (!isCompletingRef.current) {
      setCurrentProgress(progress);
    }

    return () => {
      clearAllTimers();
    };
  }, [stage, progress]);

  // Helper function to determine display stage for labels
  const getDisplayStage = () => {
    // For the actual UI labels, always use original stage during completion
    if (stage === "complete" && originalStageRef.current) {
      return originalStageRef.current;
    }
    return stage;
  };

  const getStageLabel = () => {
    // Use the original stage when in completion state
    const displayStage = getDisplayStage();
    
    switch (displayStage) {
      case "extracting":
        return "Extracting Rules";
      case "validating":
        return "Generating Approval Hierarchy";
      case "generating":
        return "Transforming to MCW - WCM";
      case "complete":
        return "Processing Complete";
      case "error":
        return "Processing Error";
      default:
        return "Processing";
    }
  };

  const getStageIndex = () => {
    // Use the original stage for the step indicator
    const displayStage = getDisplayStage();
    
    switch (displayStage) {
      case "extracting":
        return 0;
      case "validating":
        return 1;
      case "generating":
        return 2;
      case "complete":
        return 2; // Keep at the last actual processing stage
      default:
        return 0;
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto p-6 bg-white shadow-lg rounded-lg flex flex-col items-center justify-center space-y-6">
      {stage === "error" ? (
        <div className="flex flex-col items-center text-center">
          <div className="rounded-full bg-red-100 p-3 mb-4">
            <AlertCircle className="h-10 w-10 text-red-600" />
          </div>
          <h3 className="text-xl font-semibold text-red-600 mb-2">
            Processing Error
          </h3>
          <p className="text-gray-600 mb-4 whitespace-pre-line">
            {error || "An error occurred during processing. Please try again."}
          </p>
          <Button 
            variant="outline" 
            className="mt-2" 
            onClick={onDismissError}
          >
            Dismiss Error
          </Button>
        </div>
      ) : stage === "complete" && currentProgress === 100 ? (
        <div className="flex flex-col items-center text-center">
          <div className="rounded-full bg-green-100 p-3 mb-4">
            <CheckCircle className="h-10 w-10 text-green-600" />
          </div>
          <h3 className="text-xl font-semibold text-green-600 mb-2">
            Processing Complete
          </h3>
          <p className="text-gray-600 mb-4">
            Your data has been successfully processed.
          </p>
        </div>
      ) : (
        <>
          <div className="rounded-full bg-blue-100 p-3 mb-2">
            <Loader2 className="h-10 w-10 text-blue-600 animate-spin" />
          </div>
          <h3 className="text-xl font-semibold text-gray-800">
            {getStageLabel()}
          </h3>
          <p className="text-gray-600 text-center mb-4">{message}</p>

          <div className="w-full space-y-6">
            <Progress value={currentProgress} className="h-2 w-full" />
            <div className="flex justify-between text-sm text-gray-500">
              <span>{Math.round(currentProgress)}%</span>
              <span>Step {getStageIndex() + 1} of 3</span>
            </div>
          </div>

          <div className="w-full pt-4">
            <div className="flex justify-between">
              <div
                className={`flex flex-col items-center w-24 text-center ${
                  getStageIndex() >= 0 ? "text-blue-600" : "text-gray-400"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    getStageIndex() >= 0 ? "bg-blue-600 text-white" : "bg-gray-200"
                  }`}
                >
                  1
                </div>
                <span className="text-xs mt-1 whitespace-normal">Rules Extraction</span>
              </div>
              <div
                className={`flex-1 h-0.5 self-center mx-1 ${
                  getStageIndex() >= 1 ? "bg-blue-600" : "bg-gray-200"
                }`}
              />
              <div
                className={`flex flex-col items-center w-24 text-center ${
                  getStageIndex() >= 1 ? "text-blue-600" : "text-gray-400"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    getStageIndex() >= 1 ? "bg-blue-600 text-white" : "bg-gray-200"
                  }`}
                >
                  2
                </div>
                <span className="text-xs mt-1 whitespace-normal">Hierarchy Generation</span>
              </div>
              <div
                className={`flex-1 h-0.5 self-center mx-1 ${
                  getStageIndex() >= 2 ? "bg-blue-600" : "bg-gray-200"
                }`}
              />
              <div
                className={`flex flex-col items-center w-24 text-center ${
                  getStageIndex() >= 2 ? "text-blue-600" : "text-gray-400"
                }`}
              >
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    getStageIndex() >= 2 ? "bg-blue-600 text-white" : "bg-gray-200"
                  }`}
                >
                  3
                </div>
                <span className="text-xs mt-1 whitespace-normal">MCW - WCM Generation</span>
              </div>
            </div>
          </div>
        </>
      )}
    </Card>
  );
};

export default ProcessingIndicator;
