import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FileUploadZone } from "./FileUploadZone";
import { ProgressTracker } from "./ProgressTracker";
import { useToast } from "@/hooks/use-toast";
import { downloadPrompt } from "@/utils/promptUtils";
import { Save, Lock, Unlock, Download, RotateCcw } from "lucide-react";
import { API_BASE_URL, sendFileProcessingTask, downloadFile } from "@/services/api";

export function WorkflowInterface() {

  
  const [defaultPrompt, setDefaultPrompt] = useState("");
  const [savedDefaultPrompt, setSavedDefaultPrompt] = useState("");
  const [isDefaultPromptLocked, setIsDefaultPromptLocked] = useState(false);
  const [newPrompt, setNewPrompt] = useState("");
  const [savedNewPrompt, setSavedNewPrompt] = useState("");
  const [isNewPromptLocked, setIsNewPromptLocked] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  const [activeTab, setActiveTab] = useState("default");
  const [noInputFiles, setNoInputFiles] = useState(false);
  const { toast, dismiss } = useToast();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch('/default_prompt.txt')
      .then(response => response.text())
      .then(text => {
        setDefaultPrompt(text);
        setSavedDefaultPrompt(text);
      })
      .catch(error => {
        console.error('Error fetching default prompt:', error);
        // Fallback to a default message if fetching fails
        const fallbackPrompt = "Failed to load default prompt.";
        setDefaultPrompt(fallbackPrompt);
        setSavedDefaultPrompt(fallbackPrompt);
        toast({
          title: "Error loading prompt",
          description: "Could not load the default prompt from file.",
          variant: "destructive",
        });
        setErrorMessage("Error loading default prompt from file.");
      });
  }, []); // Empty dependency array ensures this runs only once on mount

  const handleFilesUpload = (files: File[]) => {
    setUploadedFiles(files);
    setIsCompleted(false);
    setErrorMessage(null);
    // Toast is handled in the FileUploadZone component in the visual-ui-creator-gen project,
    // but we can keep a simple confirmation here if needed.
    // toast({
    //   title: "Files selected",
    //   description: `${files.length} file(s) are ready for processing.`,
    // });
  };

  const handleSaveDefaultPrompt = () => {
    setSavedDefaultPrompt(defaultPrompt);
    setIsDefaultPromptLocked(true);
    toast({
      title: "Default prompt saved",
      description: "The default prompt has been saved and locked for editing.",
    });
  };

  const handleSaveNewPrompt = () => {
    setSavedNewPrompt(newPrompt);
    setIsNewPromptLocked(true);
    toast({
      title: "New prompt saved",
      description: "The new prompt has been saved and locked for editing.",
    });
  };

  const handleUnlockDefaultPrompt = () => {
    setIsDefaultPromptLocked(false);
    toast({
      title: "Default prompt unlocked",
      description: "You can now edit the default prompt.",
    });
  };

  const handleUnlockNewPrompt = () => {
    setIsNewPromptLocked(false);
    toast({
      title: "New prompt unlocked",
      description: "You can now edit the new prompt.",
    });
  };

  const handleResetDefaultPrompt = () => {
    // Fetch the default prompt again to ensure it's the original content from the file
    fetch('/default_prompt.txt')
      .then(response => response.text())
      .then(text => {
        setDefaultPrompt(text);
        setSavedDefaultPrompt(text);
        setIsDefaultPromptLocked(false);
        toast({
          title: "Default prompt reset",
          description: "The default prompt has been reset from the file.",
        });
      })
      .catch(error => {
        console.error('Error fetching default prompt for reset:', error);
        toast({
          title: "Error resetting prompt",
          description: "Could not reset the default prompt from file.",
          variant: "destructive",
        });
      });
  };

  const handleDownloadDefaultPrompt = () => {
    const promptToDownload = isDefaultPromptLocked ? savedDefaultPrompt : defaultPrompt;
    downloadPrompt(promptToDownload, "default-prompt.txt");
    toast({
      title: "Download started",
      description: "Default prompt file is being downloaded.",
    });
  };

  const handleDownloadNewPrompt = () => {
    const promptToDownload = isNewPromptLocked ? savedNewPrompt : newPrompt;
    if (!promptToDownload.trim()) {
      toast({
        title: "No content to download",
        description: "Please enter some content in the new prompt before downloading.",
        variant: "destructive",
      });
      return;
    }
    downloadPrompt(promptToDownload, "new-prompt.txt");
    toast({
      title: "Download started",
      description: "New prompt file is being downloaded.",
    });
  };

  const handleSubmit = async () => {
    if (!noInputFiles && uploadedFiles.length === 0) {
      toast({
        title: "No files uploaded",
        description: "Please upload at least one Excel file or check 'No input files'.",
        variant: "destructive",
      });
      setErrorMessage("Please upload at least one Excel file or check 'No input files'.");
      return;
    }

    let promptToUse = "";
    if (activeTab === "default") {
      promptToUse = isDefaultPromptLocked ? savedDefaultPrompt : defaultPrompt;
    } else {
      promptToUse = isNewPromptLocked ? savedNewPrompt : newPrompt;
    }

    if (!promptToUse.trim()) {
      toast({
        title: "No prompt selected",
        description: "Please enter a prompt before submitting.",
        variant: "destructive",
      });
      setErrorMessage("Please enter a prompt before submitting.");
      return;
    }

    setIsProcessing(true);
    setProgress(0);
    setIsCompleted(false);
    setErrorMessage(null);

    const initialToast = toast({
        title: "Submitting task...",
        description: "Preparing files and instructions.",
        duration: Infinity,
    });

    let parts: any[] = [{ type: 'text', text: promptToUse }];
    let uploadedFileParts: any[] = [];

    if (!noInputFiles && uploadedFiles.length > 0) {
        initialToast.update({
            id: initialToast.id,
            title: "Uploading files...",
            description: `Uploading ${uploadedFiles.length} file(s).`,
        });

        for (let i = 0; i < uploadedFiles.length; i++) {
            const file = uploadedFiles[i];
            const formData = new FormData();
            formData.append('file', file);

            try {
                const uploadResponse = await fetch(`${API_BASE_URL}/file-preprocessing/upload`, {
                    method: 'POST',
                    body: formData,
                });

                if (!uploadResponse.ok) {
                    const errorText = await uploadResponse.text();
                    throw new Error(`Upload failed for ${file.name}: ${uploadResponse.status} ${errorText}`);
                }

                const uploadResult = await uploadResponse.json();
                uploadedFileParts.push({
                    type: 'file',
                    file: {
                        name: file.name,
                        mimeType: file.type || 'application/octet-stream',
                        uri: uploadResult.uri,
                    },
                });
                initialToast.update({
                    id: initialToast.id,
                    description: `Uploaded ${i + 1} of ${uploadedFiles.length} files.`,
                });

            } catch (error: any) {
                console.error("Error uploading file:", file.name, error);
                initialToast.update({
                    id: initialToast.id,
                    title: "Upload Error",
                    description: `Failed to upload file ${file.name}: ${error.message || String(error)}`,
                    variant: "destructive",
                    duration: 5000,
                });
                setIsProcessing(false);
                setErrorMessage(error.message || String(error));
                return;
            }
        }
         initialToast.update({
            id: initialToast.id,
            title: "File uploads complete.",
            description: "Submitting task to agent.",
            duration: 3000,
        });
    }

    parts = parts.concat(uploadedFileParts);

    const payload = {
        message: {
            role: 'user',
            parts: parts,
        },
    };

    try {
        initialToast.update({
            id: initialToast.id,
            title: "Task submitted.",
            description: "Waiting for agent response.",
            duration: Infinity,
        });
        setIsProcessing(true);

        const response = await sendFileProcessingTask(payload);

        if (!response.ok || !response.body) {
            const errorDetail = await response.text();
            console.error("/sendSubscribe fetch failed:", response.status, errorDetail);
            initialToast.update({
                id: initialToast.id,
                title: "Task Submission Failed",
                description: `Error submitting task: ${response.status} ${errorDetail}`,
                variant: "destructive",
                duration: 5000,
            });
            setIsProcessing(false);
            setErrorMessage(errorDetail);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let accumulatedArtifactText = '';
        let currentStatusMessage = "";
        let streamDownloadUrl = null;
        let streamDownloadFilename = null;
        let taskFailedDuringStream = false;
        let taskIsCompleted = false;

        const processStream = async () => {
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log("Stream finished.");
                    break;
                }

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';

                for (const eventString of events) {
                    if (!eventString) continue;

                    try {
                        let data = null;
                        let eventType = 'message';
                        const lines = eventString.split('\n');
                        for (const line of lines) {
                            if (line.startsWith('data: ')) {
                                data = (data || '') + line.substring('data: '.length);
                            } else if (line.startsWith('event: ')) {
                                eventType = line.substring('event: '.length);
                            }
                        }

                        if (data) {
                            const update = JSON.parse(data);
                            console.log(`Received ${eventType}:`, update);

                            if (eventType === 'task_status_update') {
                                currentStatusMessage = update.status.message?.parts?.[0]?.text || '';
                                // Log the full update object to diagnose premature stream closure
                                console.log(`FULL RECEIVED task_status_update: ${JSON.stringify(update, null, 2)}`);
                                initialToast.update({
                                    id: initialToast.id,
                                    title: `Task Status: ${update.status.state}`,
                                    description: currentStatusMessage,
                                    variant: update.status.state === 'failed' ? 'destructive' : 'default',
                                    duration: update.final ? 5000 : Infinity,
                                });

                                if (update.status.state === 'completed') {
                                    taskIsCompleted = true;
                                }
                                if (update.status.state === 'failed' || update.status.state === 'canceled') {
                                    setErrorMessage(currentStatusMessage);
                                    taskFailedDuringStream = true;
                                }

                                if (update.status.state === 'working') {
                                    setProgress(50);
                                } else if (update.status.state === 'completed' || update.status.state === 'failed' || update.status.state === 'canceled') {
                                    setProgress(100);
                                }

                                if (update.final) {
                                    setIsProcessing(false);
                                    if (update.status.state === 'completed' && update.metadata && update.metadata.downloadUrl) {
                                        const backendDownloadPath = update.metadata.downloadUrl;
                                        if (backendDownloadPath && backendDownloadPath.startsWith('/api/tasks/')) {
                                            streamDownloadUrl = `${API_BASE_URL}/file-preprocessing${backendDownloadPath.substring('/api'.length)}`;
                                        } else {
                                            streamDownloadUrl = backendDownloadPath;
                                            console.warn("Unexpected downloadUrl format received from backend:", backendDownloadPath);
                                        }
                                        streamDownloadFilename = update.metadata.downloadFilename || 'download';
                                        console.log("Download URL constructed on frontend:", streamDownloadUrl);
                                    } else {
                                        streamDownloadUrl = null;
                                        streamDownloadFilename = null;
                                    }
                                }

                            } else if (eventType === 'task_artifact_update') {
                                // Log the full artifact update object
                                console.log(`FULL RECEIVED task_artifact_update: ${JSON.stringify(update, null, 2)}`);
                                update.artifact.parts.forEach((part: any) => {
                                    if (part.type === 'text' && part.text) {
                                        accumulatedArtifactText += part.text + '\n';
                                    }
                                    if (part.type === 'file' && part.file) {
                                         const filename = part.file.name || 'artifact_file';
                                         const fileUrl = `${API_BASE_URL}/file-preprocessing/tasks/${update.id}/artifacts/${encodeURIComponent(filename)}`;
                                         console.log(`Received file artifact: ${filename}, URL: ${fileUrl}`);
                                    }
                                });
                                initialToast.update({
                                    id: initialToast.id,
                                    description: `${currentStatusMessage}\n\n${accumulatedArtifactText.trim()}`,
                                });
                            } else if (eventType === 'task_progress_update') {
                                setProgress(update.progress);
                                currentStatusMessage = update.message;
                                initialToast.update({
                                    id: initialToast.id,
                                    title: `Processing: ${update.progress}%`,
                                    description: update.message,
                                    duration: Infinity,
                                });
                            }
                        }
                    } catch (parseError) {
                        console.error("Error parsing SSE data:", parseError, eventString);
                        initialToast.update({
                           id: initialToast.id,
                           title: "Streaming Error",
                           description: `Failed to process update from server.`,
                           variant: "destructive",
                           duration: 5000,
                        });
                        taskFailedDuringStream = true;
                        setErrorMessage(`Streaming error: ${parseError instanceof Error ? parseError.message : String(parseError)}`);
                        reader.cancel();
                        break;
                    }
                }
            }

            // Final state updates after stream processing
            setIsProcessing(false);
            dismiss(initialToast.id);

            let finalTitle: string;
            let finalVariant: "default" | "destructive";
            let finalDescription = currentStatusMessage || "See console for details.";

            if (accumulatedArtifactText) {
                finalDescription += `\n\n${accumulatedArtifactText.trim()}`;
            }

            // Set final completion state based on the local variable
            setIsCompleted(taskIsCompleted);

            // This part is for the toast notification, keep its logic separate if needed
            if (taskIsCompleted) {
                finalTitle = "Task Completed";
                finalVariant = "default";
                setErrorMessage(null);
            } else if (taskFailedDuringStream) {
                finalTitle = "Task Failed";
                finalVariant = "destructive";
                setErrorMessage(finalDescription);
            } else {
                // Fallback for unexpected stream end or cancellation not explicitly marked failed
                if (currentStatusMessage.toLowerCase().includes("canceled")) {
                    finalTitle = "Task Canceled";
                    finalVariant = "destructive";
                    setErrorMessage("Task was canceled.");
                } else {
                    finalTitle = "Unknown Status";
                    finalVariant = "destructive";
                    setErrorMessage(finalDescription);
                }
            }

            toast({
               title: finalTitle,
               description: finalDescription,
               variant: finalVariant,
               duration: streamDownloadUrl ? Infinity : 5000,
            });

            if (streamDownloadUrl && streamDownloadFilename) {
                setDownloadUrl(streamDownloadUrl);
                setDownloadFilename(streamDownloadFilename);
            } else {
                setDownloadUrl(null);
                setDownloadFilename(null);
            }
        };

        processStream().catch(error => {
            console.error("Error processing stream:", error);
             initialToast.update({
                id: initialToast.id,
                title: "Streaming Error",
                description: `An error occurred while processing the agent's response stream.`,
                variant: "destructive",
                duration: 5000,
             });
            setIsProcessing(false);
        });

    } catch (error: any) {
        console.error("Error during task submission or streaming setup:", error);
        initialToast.update({
            id: initialToast.id,
            title: "Submission Error",
            description: `An error occurred: ${error.message || String(error)}`,
            variant: "destructive",
            duration: 5000,
        });
        setIsProcessing(false);
        setErrorMessage(error.message || String(error));
    } finally {
    }
  };

  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);
  const [downloadFilename, setDownloadFilename] = useState<string | null>(null);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-bold">Workflow File Pre-processing</h1>
      
      <Card className="p-6">
        <Tabs defaultValue="default" value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="default">Default Prompt</TabsTrigger>
            <TabsTrigger value="new">New prompt</TabsTrigger>
          </TabsList>
          
          <TabsContent value="default" className="mt-4">
            <div className="space-y-4">
              <label className="text-sm font-medium">Default Prompt</label>
              <Textarea
                value={defaultPrompt}
                onChange={(e) => setDefaultPrompt(e.target.value)}
                placeholder="Enter your default prompt here..."
                className="min-h-[200px]"
                disabled={isDefaultPromptLocked}
              />
              <div className="flex flex-wrap gap-2">
                {!isDefaultPromptLocked ? (
                  <Button onClick={handleSaveDefaultPrompt} size="sm">
                    <Save className="w-4 h-4 mr-2" />
                    Save Prompt
                  </Button>
                ) : (
                  <Button onClick={handleUnlockDefaultPrompt} size="sm" variant="outline">
                    <Unlock className="w-4 h-4 mr-2" />
                    Unlock Prompt
                  </Button>
                )}
                <Button onClick={handleResetDefaultPrompt} size="sm" variant="outline">
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Reset Prompt
                </Button>
                <Button onClick={handleDownloadDefaultPrompt} size="sm" variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  Download Prompt
                </Button>
              </div>
              {isDefaultPromptLocked && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Lock className="w-4 h-4" />
                  <span>Prompt is saved and locked for editing</span>
                </div>
              )}
            </div>
          </TabsContent>
          
          <TabsContent value="new" className="mt-4">
            <div className="space-y-4">
              <label className="text-sm font-medium">New Prompt</label>
              <Textarea
                value={newPrompt}
                onChange={(e) => setNewPrompt(e.target.value)}
                placeholder="Enter your new prompt here..."
                className="min-h-[120px]"
                disabled={isNewPromptLocked}
              />
              <div className="flex flex-wrap gap-2">
                {!isNewPromptLocked ? (
                  <Button onClick={handleSaveNewPrompt} size="sm" disabled={!newPrompt.trim()}>
                    <Save className="w-4 h-4 mr-2" />
                    Save Prompt
                  </Button>
                ) : (
                  <Button onClick={handleUnlockNewPrompt} size="sm" variant="outline">
                    <Unlock className="w-4 h-4 mr-2" />
                    Unlock Prompt
                  </Button>
                )}
                <Button onClick={handleDownloadNewPrompt} size="sm" variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  Download Prompt
                </Button>
              </div>
              {isNewPromptLocked && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Lock className="w-4 h-4" />
                  <span>Prompt is saved and locked for editing</span>
                </div>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </Card>

      <Card className="p-6">
        <div className="flex items-center space-x-2 mb-4">
          <Checkbox 
            id="no-input-files" 
            checked={noInputFiles}
            onCheckedChange={(checked) => {
              setNoInputFiles(checked as boolean);
              if (checked) {
                setUploadedFiles([]);
              }
            }}
          />
          <label htmlFor="no-input-files" className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            No input files
          </label>
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          Check this option if you don't need to upload any input files for processing.
        </p>
      </Card>

      {!noInputFiles && <FileUploadZone onFilesUpload={handleFilesUpload} />}

      {uploadedFiles.length > 0 && !noInputFiles && (
        <div className="text-center p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>{uploadedFiles.length}</strong> uploaded files ready for processing
          </p>
        </div>
      )}

      <div className="flex justify-center">
        <Button 
          onClick={handleSubmit}
          disabled={isProcessing || (uploadedFiles.length === 0 && !noInputFiles)}
          className="px-8 py-2"
        >
          {isProcessing ? "Processing..." : "AI assist"}
        </Button>
      </div>

      <ProgressTracker 
        isProcessing={isProcessing}
        progress={progress}
        isCompleted={isCompleted}
        downloadUrl={downloadUrl}
        downloadFilename={downloadFilename}
        errorMessage={errorMessage}
      />
    </div>
  );
} 