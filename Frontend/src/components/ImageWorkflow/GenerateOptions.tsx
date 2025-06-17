import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { FileDown, ChevronLeft, CheckCircle, ArrowRight } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useWorkflow } from "@/lib/WorkflowContext";
import { generateWorkflowFiles, getCurrentFile, downloadFile, API_BASE_URL } from "@/services/api";
import { toast } from "@/components/ui/use-toast";
import { Progress } from "@/components/ui/progress";

const GenerateOptions: React.FC = () => {
  const navigate = useNavigate();
  const { markStepCompleted } = useWorkflow();
  const [generating, setGenerating] = useState(false);
  const [generated, setGenerated] = useState(false);
  const [selectedOptions, setSelectedOptions] = useState({
    mcw: true,
    wcm: true,
    metadata: true
  });
  const [generatedFiles, setGeneratedFiles] = useState({});
  const [processingStatus, setProcessingStatus] = useState("Idle");
  const [processingProgress, setProcessingProgress] = useState(0);

  // Handler for option selection
  const handleOptionToggle = (option: 'mcw' | 'wcm' | 'metadata') => {
    setSelectedOptions(prev => ({
      ...prev,
      [option]: !prev[option]
    }));
  };

  // Handler for starting generation
  const handleGenerate = async () => {
    if (!selectedOptions.mcw && !selectedOptions.wcm && !selectedOptions.metadata) {
      alert("Please select at least one output format to generate.");
      return;
    }

    setGenerating(true);
    setGeneratedFiles({});
    setProcessingStatus("Initializing...");
    setProcessingProgress(0);

    try {
      const fileInfo = await getCurrentFile();
      if (!fileInfo || !fileInfo.filename) {
        toast({ title: "Generation Failed", description: "Could not retrieve current image filename.", variant: "destructive" });
        setGenerating(false);
        return;
      }

      const taskId = `task-${Date.now()}`;
      const eventSource = new EventSource(`${API_BASE_URL}/file-preprocessing/tasks/sendSubscribe?id=${taskId}`);

      eventSource.onmessage = (event) => {
        console.log("SSE Message:", event);
      };

      eventSource.addEventListener('task_status_update', (event) => {
        const data = JSON.parse(event.data);
        console.log("Task Status Update:", data);
        setProcessingStatus(data.status.message.parts[0].text);
        if (data.final) {
          eventSource.close();
          setGenerating(false);
          if (data.status.state === "completed") {
            setGenerated(true);
            setGeneratedFiles(data.metadata || {});
            markStepCompleted(2);
            localStorage.setItem('hasGeneratedFiles', 'true');
            toast({ title: "Generation Complete", description: "Workflow files generated successfully.", variant: "default" });
          } else {
            toast({ title: "Generation Failed", description: data.status.message.parts[0].text, variant: "destructive" });
          }
        }
      });

      eventSource.addEventListener('task_progress_update', (event) => {
        const data = JSON.parse(event.data);
        console.log("Task Progress Update:", data);
        setProcessingProgress(data.progress);
        setProcessingStatus(data.message);
      });

      eventSource.onerror = (error) => {
        console.error("SSE Error:", error);
        eventSource.close();
        setGenerating(false);
        toast({ title: "Generation Failed", description: "Connection error or stream ended unexpectedly.", variant: "destructive" });
      };

      await fetch(`${API_BASE_URL}/file-preprocessing/tasks/sendSubscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: taskId,
          message: {
            parts: [{ type: "text", text: "Generate workflow files." }],
          },
          metadata: {
            filename: fileInfo.filename,
            options: selectedOptions
          }
        }),
      });

    } catch (error) {
      console.error("Error during file generation setup:", error);
      toast({ title: "Generation Failed", description: error instanceof Error ? error.message : "An unexpected error occurred during generation setup.", variant: "destructive" });
      setGenerating(false);
    }
  };

  // Handler for back button
  const handleBack = () => {
    navigate("/workflow/image/design");
  };

  // Handler for downloading generated files
  const handleDownload = async () => {
    if (Object.keys(generatedFiles).length === 0) {
       toast({ title: "Download Failed", description: "No files to download.", variant: "default" });
       return;
    }
    
    setGenerating(true);
    
    const downloadUrl = `${API_BASE_URL}/image/download-generated-files?${new URLSearchParams(generatedFiles).toString()}`;

    const zipFilename = `workflow_outputs_${new Date().toISOString().slice(0, 10)}.zip`;

    try {
        console.log("Attempting to download files from:", downloadUrl);
        const response = await fetch(downloadUrl);

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Download failed');
        }

        const blob = await response.blob();
        console.log("Received blob for download:", blob.type, blob.size, "bytes");

        const blobUrl = window.URL.createObjectURL(blob);

        const link = document.createElement('a');
        link.href = blobUrl;
        link.download = zipFilename;

        document.body.appendChild(link);

        link.click();

        document.body.removeChild(link);
        window.URL.revokeObjectURL(blobUrl);

        toast({ title: "Download Started", description: `Downloading ${zipFilename}...`, variant: "default" });

    } catch (error) {
         console.error("Error during download:", error);
         toast({ title: "Download Failed", description: error instanceof Error ? error.message : "An unexpected error occurred during download.", variant: "destructive" });
    } finally {
        setGenerating(false);
    }
  };

  // Handler for finishing the workflow
  const handleFinish = () => {
    navigate("/dashboard");
  };

  return (
    <div className="py-8 px-4">
      <div className="max-w-4xl mx-auto">
        <div className="text-left mb-6">
          <h2 className="text-3xl font-bold mb-2 text-slate-800">Generate Workflow Files</h2>
          <p className="text-slate-600">
            Select which files you want to generate from your workflow design.
          </p>
        </div>
        
        {generating ? (
            <Card className="mb-8 bg-blue-50 border-blue-200">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg text-blue-800">Progress of Execution</CardTitle>
                <CardDescription className="text-blue-700">Once processing is completed successfully, download file option will be available.</CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-blue-600 font-medium w-32">Status:</span>
                  <p className="text-blue-800 flex-1">{processingStatus}</p>
                </div>
                <Progress value={processingProgress} className="w-full mt-4 bg-blue-100" key={processingProgress} />
                <p className="text-sm text-blue-600 text-right mt-2">{processingProgress}% complete</p>
              </CardContent>
            </Card>
        ) : generated ? (
          <Card className="mb-8 bg-green-50 border-green-200">
            <CardContent className="p-6">
              <div className="flex flex-col items-center text-center space-y-4">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle className="h-6 w-6 text-green-600" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-green-800">Files Generated Successfully!</h3>
                  <p className="text-green-700 mt-1">Your workflow files are ready to download.</p>
                </div>
                <Button 
                  className="mt-2 bg-green-600 hover:bg-green-700 text-white"
                  onClick={handleDownload}
                >
                  <FileDown className="h-4 w-4 mr-2" />
                  Download Generated Files
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
            <>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                  {/* MCW Option */}
                  <Card 
                    className={`cursor-pointer transition-all border-2 ${
                      selectedOptions.mcw 
                        ? 'border-blue-500 shadow-md bg-blue-50' 
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    onClick={() => handleOptionToggle('mcw')}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg text-slate-800">MCW File</CardTitle>
                        <div className={`w-5 h-5 rounded-full ${
                          selectedOptions.mcw 
                            ? 'bg-blue-500 flex items-center justify-center' 
                            : 'border-2 border-slate-300'
                        }`}>
                          {selectedOptions.mcw && <CheckCircle className="h-4 w-4 text-white" />}
                        </div>
                      </div>
                      <CardDescription className="text-slate-500">
                        Master Condition Workflow
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-sm text-slate-600">
                        Contains the complete workflow with all conditions and transitions.
                      </p>
                    </CardContent>
                  </Card>
                  
                  {/* WCM Option */}
                  <Card 
                    className={`cursor-pointer transition-all border-2 ${
                      selectedOptions.wcm 
                        ? 'border-blue-500 shadow-md bg-blue-50' 
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    onClick={() => handleOptionToggle('wcm')}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg text-slate-800">WCM File</CardTitle>
                        <div className={`w-5 h-5 rounded-full ${
                          selectedOptions.wcm 
                            ? 'bg-blue-500 flex items-center justify-center' 
                            : 'border-2 border-slate-300'
                        }`}>
                          {selectedOptions.wcm && <CheckCircle className="h-4 w-4 text-white" />}
                        </div>
                      </div>
                      <CardDescription className="text-slate-500">
                        Workflow Condition Matrix
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-sm text-slate-600">
                        Defines relationships between conditions in a matrix format.
                      </p>
                    </CardContent>
                  </Card>
                  
                  {/* Metadata Option */}
                  <Card 
                    className={`cursor-pointer transition-all border-2 ${
                      selectedOptions.metadata 
                        ? 'border-blue-500 shadow-md bg-blue-50' 
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                    onClick={() => handleOptionToggle('metadata')}
                  >
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between">
                        <CardTitle className="text-lg text-slate-800">Metadata</CardTitle>
                        <div className={`w-5 h-5 rounded-full ${
                          selectedOptions.metadata 
                            ? 'bg-blue-500 flex items-center justify-center' 
                            : 'border-2 border-slate-300'
                        }`}>
                          {selectedOptions.metadata && <CheckCircle className="h-4 w-4 text-white" />}
                        </div>
                      </div>
                      <CardDescription className="text-slate-500">
                        Workflow Metadata
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <p className="text-sm text-slate-600">
                        Additional information about workflow nodes, edges, and configurations.
                      </p>
                    </CardContent>
                  </Card>
                </div>

                <div className="flex justify-between items-center">
                  <Button 
                    variant="outline"
                    onClick={handleBack}
                    className="text-slate-600 border-slate-300 hover:text-blue-600 hover:border-blue-600"
                  >
                    <ChevronLeft className="h-4 w-4 mr-2" />
                    Back to Design
                  </Button>

                  <Button 
                    onClick={handleGenerate}
                    disabled={generating}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    {generating ? "Processing..." : "Generate Files"}
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
            </>
        )}
      </div>
    </div>
  );
};

export default GenerateOptions; 