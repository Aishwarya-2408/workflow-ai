import React, { useState, useEffect } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CheckCircle, Circle, AlertCircle } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

type TabStatus = "completed" | "current" | "upcoming" | "error";

interface WorkflowTab {
  id: string;
  label: string;
  status: TabStatus;
  description?: string; 
}

interface WorkflowTabsProps {
  tabs?: WorkflowTab[];
  activeTab?: string;
  onTabChange?: (tabId: string) => void;
}

const WorkflowTabs: React.FC<WorkflowTabsProps> = ({
  tabs = [
    { 
      id: "upload", 
      label: "Upload", 
      status: "completed",
      description: "Upload your workflow files here" 
    },
    { 
      id: "validation", 
      label: "Validation", 
      status: "current",
      description: "Validate your workflow data" 
    },
    { 
      id: "tree", 
      label: "Tree", 
      status: "upcoming",
      description: "View and edit your workflow structure" 
    },
    { 
      id: "download", 
      label: "Download", 
      status: "upcoming",
      description: "Download your completed workflow files" 
    },
  ],
  activeTab = "validation",
  onTabChange = () => {},
}) => {
  const [currentTab, setCurrentTab] = useState(activeTab);

  useEffect(() => {
    setCurrentTab(activeTab);
  }, [activeTab]);

  // This is now a no-op function - tabs can't be changed by clicking
  const handleTabChange = (tabId: string) => {
    // Do nothing - disabled direct tab navigation
    // We'll keep the function for compatibility but it won't do anything
  };

  const getStatusIcon = (status: TabStatus) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 mr-2 text-green-500" />;
      case "current":
        return <Circle className="h-4 w-4 mr-2 text-blue-500 fill-blue-500" />;
      case "error":
        return <AlertCircle className="h-4 w-4 mr-2 text-red-500" />;
      default:
        return <Circle className="h-4 w-4 mr-2 text-gray-300" />;
    }
  };

  const getTabClasses = (status: TabStatus, isActive: boolean) => {
    let baseClasses = "flex items-center px-4 py-2 rounded-md transition-all";

    if (isActive) {
      return `${baseClasses} bg-primary/10 text-primary font-medium`;
    }

    switch (status) {
      case "completed":
        return `${baseClasses} hover:bg-green-50 text-green-700 cursor-pointer`;
      case "current":
        return `${baseClasses} hover:bg-blue-50 text-blue-700 cursor-pointer`;
      case "error":
        return `${baseClasses} hover:bg-red-50 text-red-700 cursor-pointer`;
      default:
        return `${baseClasses} text-gray-400 cursor-not-allowed`;
    }
  };

  return (
    <div className="w-full bg-white border-b border-gray-200 px-4 py-2">
      <Tabs
        value={currentTab}
        onValueChange={handleTabChange}
        className="w-full"
      >
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-800">
            Excel Workflow
          </h2>
          <TabsList className="bg-gray-100 p-1 rounded-lg">
            {tabs.map((tab) => (
              <TooltipProvider key={tab.id}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <TabsTrigger
                      value={tab.id}
                      disabled={tab.status === "upcoming"}
                      className={getTabClasses(tab.status, currentTab === tab.id)}
                      onClick={(e) => {
                      // Prevent default behavior and stop propagation
                        e.preventDefault();
                        e.stopPropagation();
                        return false;
                      }}
                    >
                      {getStatusIcon(tab.status)}
                      {tab.label}
                    </TabsTrigger>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{tab.description || `${tab.label} stage of the workflow`}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            ))}
          </TabsList>
        </div>
      </Tabs>

      <div className="mt-4 relative h-2 bg-gray-200 rounded-full overflow-hidden">
        {tabs.map((tab, index) => {
          const segmentWidth = 100 / tabs.length;
          const left = `${index * segmentWidth}%`;
          const width = `${segmentWidth}%`;
          
          let bgColor = "";
          switch (tab.status) {
            case "completed":
              bgColor = "bg-blue-500"; 
              break;
            case "current":
              bgColor = "bg-blue-500 opacity-30"; 
              break;
            case "error":
              bgColor = "bg-red-500";
              break;
            default: 
              bgColor = "bg-gray-200 opacity-30";
          }
          
          return (
            <div
              key={tab.id}
              className={`absolute h-full ${bgColor} transition-all duration-300`}
              style={{ left, width }}
            />
          );
        })}
      </div>
    </div>
  );
};

export default WorkflowTabs;
