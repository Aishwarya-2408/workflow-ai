import { useState, useCallback, useRef } from "react";
import { Upload, FileText, X, FolderOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

interface FileUploadZoneProps {
  onFilesUpload: (files: File[]) => void;
}

export function FileUploadZone({ onFilesUpload }: FileUploadZoneProps) {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files) {
      const droppedFiles = Array.from(e.dataTransfer.files).filter(file => 
        file.type.includes('excel') || 
        file.type.includes('spreadsheet') || 
        file.name.endsWith('.xlsx') || 
        file.name.endsWith('.xls')
      );
      
      if (droppedFiles.length > 0) {
        const newFiles = [...uploadedFiles, ...droppedFiles];
        setUploadedFiles(newFiles);
        onFilesUpload(newFiles);
      }
    }
  }, [onFilesUpload, uploadedFiles]);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    console.log('File input triggered');
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      console.log('Files selected:', selectedFiles.length);
      const newFiles = [...uploadedFiles, ...selectedFiles];
      setUploadedFiles(newFiles);
      onFilesUpload(newFiles);
    }
    // Reset the input so the same files can be selected again if needed
    e.target.value = '';
  };

  const handleBrowseClick = () => {
    console.log('Browse button clicked');
    fileInputRef.current?.click();
  };

  const removeFile = (indexToRemove: number) => {
    const newFiles = uploadedFiles.filter((_, index) => index !== indexToRemove);
    setUploadedFiles(newFiles);
    onFilesUpload(newFiles);
  };

  const clearAllFiles = () => {
    setUploadedFiles([]);
    onFilesUpload([]);
  };

  return (
    <Card className="p-6">
      <h3 className="text-sm font-medium mb-3">Upload Input Excel Files</h3>
      <p className="text-xs text-muted-foreground mb-4">
        Upload files from any folder on your system. You can select files from multiple folders.
      </p>
      
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors mb-4 ${
          dragActive 
            ? "border-primary bg-primary/5" 
            : "border-gray-300 hover:border-gray-400"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p className="text-sm text-gray-600 mb-2">
          Drag and drop your Excel files here, or
        </p>
        <div className="flex gap-2 justify-center">
          <Button 
            variant="outline" 
            type="button"
            onClick={handleBrowseClick}
            className="cursor-pointer"
          >
            <FolderOpen className="w-4 h-4 mr-2" />
            Browse Files
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".xlsx,.xls"
            multiple
            onChange={handleFileInput}
          />
        </div>
        <p className="text-xs text-muted-foreground mt-2">
          You can select multiple files at once or add files from different folders
        </p>
      </div>

      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium">Uploaded Files ({uploadedFiles.length})</h4>
            <Button
              variant="ghost"
              size="sm"
              onClick={clearAllFiles}
              className="text-red-600 hover:text-red-700"
            >
              Clear All
            </Button>
          </div>
          <div className="max-h-40 overflow-y-auto space-y-2">
            {uploadedFiles.map((file, index) => (
              <div key={`${file.name}-${index}`} className="flex items-center justify-between p-3 border rounded-lg bg-green-50">
                <div className="flex items-center gap-3">
                  <FileText className="w-6 h-6 text-green-600" />
                  <div>
                    <p className="text-sm font-medium">{file.name}</p>
                    <p className="text-xs text-gray-500">
                      {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeFile(index)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  <X className="w-4 h-4" />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
} 