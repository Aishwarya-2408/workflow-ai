import React, { useState } from 'react';
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { FileSpreadsheet, Image, Download, Clock, CheckCircle, MoreVertical, ExternalLink, Loader2 } from 'lucide-react';
import { format } from 'date-fns';
import { useToast } from "@/components/ui/use-toast";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { downloadWorkflowResult } from '@/services/api';

// Types for workflow runs
export interface WorkflowRun {
  id: string;
  name: string;
  type: 'excel' | 'image';
  status: 'queued' | 'processing' | 'completed' | 'failed';
  stage: string;
  progress: number;
  createdAt: Date;
  updatedAt: Date;
}

interface WorkflowRunsTableProps {
  runs: WorkflowRun[];
}

const WorkflowRunsTable: React.FC<WorkflowRunsTableProps> = ({ runs }) => {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const { toast } = useToast();

  // Format date in human readable format
  const formatDate = (date: Date) => {
    return format(date, "MMMM d, yyyy 'at' hh:mm:ss a");
  };

  // Get status with appropriate icon and color
  const getStatus = (status: string) => {
    switch (status) {
      case 'processing':
        return (
          <div className="flex items-center text-blue-600">
            <Clock className="h-4 w-4 mr-2" />
            <span>Processing</span>
          </div>
        );
      case 'completed':
        return (
          <div className="flex items-center text-green-600">
            <CheckCircle className="h-4 w-4 mr-2" />
            <span>Completed</span>
          </div>
        );
      case 'failed':
        return (
          <div className="flex items-center text-red-600">
            <svg className="h-4 w-4 mr-2" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 8V12M12 16H12.01M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>Failed</span>
          </div>
        );
      default:
        return <span className="text-gray-600">{status}</span>;
    }
  };

  // Handle download of workflow result
  const handleDownload = async (runId: string) => {
    setDownloadingId(runId);
    try {
      const response = await downloadWorkflowResult(runId);
      if (response.status === 'success') {
        toast({
          title: "Download started",
          description: "Your file is being downloaded",
          variant: "default",
        });
      } else {
        throw new Error(response.message || "Failed to download result");
      }
    } catch (error) {
      toast({
        title: "Download failed",
        description: error instanceof Error ? error.message : "An unknown error occurred",
        variant: "destructive",
      });
    } finally {
      setDownloadingId(null);
    }
  };

  // Handle view details
  const handleViewDetails = (runId: string) => {
    // This would navigate to a detail page in a real implementation
    toast({
      title: "View Details",
      description: `Viewing details for run #${runId}`,
      variant: "default",
    });
  };

  return (
    <div className="overflow-hidden">
      <div className="bg-white dark:bg-slate-800 p-4 border-b border-slate-200 dark:border-slate-700">
        <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-200">Executions In Progress</h3>
        <p className="text-sm text-slate-500 dark:text-slate-400">Track the status of your workflow transformations</p>
      </div>
      
      <div className="overflow-x-auto">
        <Table>
          <TableHeader className="bg-slate-50 dark:bg-slate-900">
            <TableRow>
              <TableHead className="text-slate-600 dark:text-slate-400 w-[60px]">Run ID</TableHead>
              <TableHead className="text-slate-600 dark:text-slate-400">Name</TableHead>
              <TableHead className="text-slate-600 dark:text-slate-400 w-[90px]">Type</TableHead>
              <TableHead className="text-slate-600 dark:text-slate-400">Progress</TableHead>
              <TableHead className="text-slate-600 dark:text-slate-400 w-[120px]">Status</TableHead>
              <TableHead className="text-slate-600 dark:text-slate-400 w-[180px]">Started</TableHead>
              <TableHead className="text-slate-600 dark:text-slate-400 w-[180px]">Completed</TableHead>
              <TableHead className="text-slate-600 dark:text-slate-400 w-[60px]">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {runs.length > 0 ? (
              runs.map((run) => (
                <TableRow key={run.id} className="border-b border-slate-200 dark:border-slate-700">
                  <TableCell className="text-sm text-slate-500 dark:text-slate-400">#{run.id}</TableCell>
                  <TableCell className="font-medium text-slate-700 dark:text-slate-300">{run.name}</TableCell>
                  <TableCell>
                    {run.type === 'excel' ? (
                      <div className="flex items-center text-emerald-600 dark:text-emerald-400">
                        <FileSpreadsheet className="h-4 w-4 mr-2" />
                        <span>Excel</span>
                      </div>
                    ) : (
                      <div className="flex items-center text-blue-600 dark:text-blue-400">
                        <Image className="h-4 w-4 mr-2" />
                        <span>Image</span>
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center">
                      <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 mr-2 overflow-hidden">
                        <div 
                          className="h-2 rounded-full bg-blue-600"
                          style={{ width: `${run.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-xs font-medium text-slate-600 dark:text-slate-400 min-w-[35px] text-right">{run.progress}%</span>
                    </div>
                  </TableCell>
                  <TableCell>{getStatus(run.status)}</TableCell>
                  <TableCell className="text-xs text-slate-600 dark:text-slate-400">{formatDate(run.createdAt)}</TableCell>
                  <TableCell className="text-xs text-slate-600 dark:text-slate-400">
                    {run.status === 'completed' ? formatDate(run.updatedAt) : '-'}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8 p-0">
                          <MoreVertical className="h-4 w-4" />
                          <span className="sr-only">Open menu</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => handleViewDetails(run.id)}>
                          <ExternalLink className="h-4 w-4 mr-2" />
                          <span>View Details</span>
                        </DropdownMenuItem>
                        {run.status === 'completed' && (
                          <DropdownMenuItem onClick={() => handleDownload(run.id)} disabled={downloadingId === run.id}>
                            {downloadingId === run.id ? (
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                              <Download className="h-4 w-4 mr-2" />
                            )}
                            <span>{downloadingId === run.id ? 'Downloading...' : 'Download'}</span>
                          </DropdownMenuItem>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-10 text-gray-500">
                  No workflow runs found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
};

export default WorkflowRunsTable; 