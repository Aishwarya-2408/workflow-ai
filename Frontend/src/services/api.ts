// API utilities for connecting to the backend for Workflow application

// Use environment variables for API URL with fallback to default
// Read from .env.production or fallback to localhost
console.log("API URL from env:", import.meta.env.VITE_API_URL);
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api/v1';
console.log("Final API_BASE_URL:", API_BASE_URL);

// Types
import { WorkflowRun } from '@/components/Dashboard/WorkflowRunsTable';

// Mock data for fallback when API fails
const mockWorkflowRuns: WorkflowRun[] = [
  {
    id: '1',
    name: 'Invoice Processing',
    type: 'excel',
    status: 'completed',
    stage: 'download',
    progress: 100,
    createdAt: new Date(Date.now() - 3600000 * 24 * 2),
    updatedAt: new Date(Date.now() - 3600000 * 24),
  },
  {
    id: '2',
    name: 'Contract Workflow',
    type: 'excel',
    status: 'processing',
    stage: 'validation',
    progress: 65,
    createdAt: new Date(Date.now() - 3600000 * 2),
    updatedAt: new Date(Date.now() - 1800000),
  },
  {
    id: '3',
    name: 'Purchase Order Scan',
    type: 'image',
    status: 'processing',
    stage: 'extracting',
    progress: 30,
    createdAt: new Date(Date.now() - 1800000),
    updatedAt: new Date(),
  },
  {
    id: '4',
    name: 'Vendor Management Process',
    type: 'image',
    status: 'completed',
    stage: 'download',
    progress: 100,
    createdAt: new Date(Date.now() - 3600000 * 5),
    updatedAt: new Date(Date.now() - 3600000 * 4),
  },
  {
    id: '5',
    name: 'Expense Report Analysis',
    type: 'excel',
    status: 'failed',
    stage: 'validation',
    progress: 45,
    createdAt: new Date(Date.now() - 3600000 * 10),
    updatedAt: new Date(Date.now() - 3600000 * 9),
  }
];

/**
 * Login a user
 * @param username - The username to login with
 * @param password - The password to login with
 * @returns Promise with the login response
 */
export const login = async (username: string, password: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include', // Important for cookies/session
      body: JSON.stringify({ username, password }),
    });
    
    return await response.json();
  } catch (error) {
    console.error('Login error:', error);
    return { status: 'error', message: 'Failed to login. Please try again.' };
  }
};

/**
 * Logout the current user
 * @returns Promise with the logout response
 */
export const logout = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/logout`, {
      method: 'POST',
      credentials: 'include',
    });
    
    return await response.json();
  } catch (error) {
    console.error('Logout error:', error);
    return { status: 'error', message: 'Failed to logout. Please try again.' };
  }
};

/**
 * Get the current logged in user
 * @returns Promise with the current user info
 */
export const getCurrentUser = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/user`, {
      credentials: 'include',
    });
    
    return await response.json();
  } catch (error) {
    console.error('Get current user error:', error);
    return { status: 'error', message: 'Failed to get user information.' };
  }
};

/**
 * Fetch workflow runs for the dashboard
 * @param page - The page number to fetch (starting from 1)
 * @param pageSize - The number of records per page
 * @param type - Filter by workflow type (excel, image, or all)
 * @param status - Filter by workflow status (completed, processing, failed, or all)
 * @returns Promise with workflow runs data
 */
export const fetchWorkflowRuns = async (
  page: number = 1,
  pageSize: number = 10,
  type?: string,
  status?: string
): Promise<{ 
  data: WorkflowRun[],
  total: number,
  page: number,
  pageSize: number,
  totalPages: number
}> => {
  try {
    // Construct query parameters
    const queryParams = new URLSearchParams({
      page: page.toString(),
      pageSize: pageSize.toString(),
    });
    
    if (type && type !== 'all') {
      queryParams.append('type', type);
    }
    
    if (status && status !== 'all') {
      queryParams.append('status', status);
    }
    
    const response = await fetch(`${API_BASE_URL}/workflow-runs?${queryParams.toString()}`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Convert string dates to Date objects
      const convertedData = data.data.map((run: any) => ({
        ...run,
        createdAt: new Date(run.createdAt),
        updatedAt: new Date(run.updatedAt)
      }));
      
      return {
        data: convertedData,
        total: data.total,
        page: data.page,
        pageSize: data.pageSize,
        totalPages: data.totalPages
      };
    } else {
      throw new Error(data.message || 'Failed to fetch workflow runs');
    }
  } catch (error) {
    console.error('Error fetching workflow runs:', error);
    // Return mock data if API fails
    return {
      data: mockWorkflowRuns,
      total: mockWorkflowRuns.length,
      page: 1,
      pageSize: 10,
      totalPages: 1
    };
  }
};

/**
 * Fetch dashboard statistics
 * @returns Promise with dashboard statistics data
 */
export const fetchDashboardStats = async (): Promise<{
  completed: number,
  processing: number,
  failed: number,
  total: number
}> => {
  try {
    const response = await fetch(`${API_BASE_URL}/workflow-stats`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (data.status === 'success') {
      return {
        completed: data.stats.completed,
        processing: data.stats.processing,
        failed: data.stats.failed,
        total: data.stats.total
      };
    } else {
      throw new Error(data.message || 'Failed to fetch dashboard statistics');
    }
  } catch (error) {
    console.error('Error fetching dashboard statistics:', error);
    // Calculate stats from mock data if API fails
    const completed = mockWorkflowRuns.filter(run => run.status === 'completed').length;
    const processing = mockWorkflowRuns.filter(run => run.status === 'processing').length;
    const failed = mockWorkflowRuns.filter(run => run.status === 'failed').length;
    
    return {
      completed,
      processing,
      failed,
      total: mockWorkflowRuns.length
    };
  }
};

/**
 * Get details of a specific workflow run
 * @param workflowId - The ID of the workflow run
 * @returns Promise with the workflow run details
 */
export const getWorkflowRunDetails = async (workflowId: string): Promise<{
  status: string,
  data?: WorkflowRun,
  message?: string
}> => {
  try {
    const response = await fetch(`${API_BASE_URL}/workflow-run/${workflowId}`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`API error: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    
    if (data.status === 'success') {
      // Convert string dates to Date objects
      return {
        status: 'success',
        data: {
          ...data.data,
          createdAt: new Date(data.data.createdAt),
          updatedAt: new Date(data.data.updatedAt)
        }
      };
    } else {
      throw new Error(data.message || 'Failed to fetch workflow run details');
    }
  } catch (error) {
    console.error('Error fetching workflow run details:', error);
    // Return the matching mock data if API fails
    const mockRun = mockWorkflowRuns.find(run => run.id === workflowId);
    
    if (mockRun) {
      return {
        status: 'success',
        data: mockRun
      };
    } else {
      return {
        status: 'error',
        message: 'Workflow run not found'
      };
    }
  }
};

/**
 * Download the result file of a completed workflow
 * @param workflowId - The ID of the workflow
 * @returns Promise that resolves when download starts or rejects on error
 */
export const downloadWorkflowResult = async (workflowId: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/download-result/${workflowId}`, {
      method: 'GET',
      credentials: 'include',
    });
    
    if (!response.ok) {
      throw new Error(`Server returned ${response.status}: ${response.statusText}`);
    }
    
    // Get blob from response
    const blob = await response.blob();
    
    // Create object URL for the blob
    const url = window.URL.createObjectURL(blob);
    
    // Create a link and click it to start the download
    const a = document.createElement('a');
    a.href = url;
    
    // Get filename from Content-Disposition header or use default
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `workflow_result_${workflowId}.zip`;
    
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?([^"]*)"?/);
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1];
      }
    }
    
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
    
    return { status: "success", message: "Download started", filename: filename };
  } catch (error) {
    console.error('Error downloading workflow result:', error);
    return { 
      status: "error", 
      message: error instanceof Error ? error.message : "Failed to download result"
    };
  }
};

/**
 * Upload a file with configuration data
 * @param file - The file to upload
 * @param config - Configuration data
 * @returns Promise with the upload response
 */
export const uploadFile = async (file: File, config: any) => {
  try {
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('config', JSON.stringify(config));
    
    // Send request to backend
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      body: formData,
    });
    
    // Parse response
    const data = await response.json();
    
    if (!response.ok) {
      // Format error message with details if available
      let errorMessage = data.error || data.message || 'Failed to upload file';
      
      // Add details to the error message if available
      if (data.details) {
        if (Array.isArray(data.details)) {
          // If details is an array, format each item on a new line
          errorMessage = `${errorMessage}\n\nDetails:\n${data.details.map(detail => `• ${detail}`).join('\n')}`;
        } else if (typeof data.details === 'string') {
          // If details is a string, add it on a new line
          errorMessage = `${errorMessage}\n\nDetails:\n${data.details}`;
        }
      }
      
      throw new Error(errorMessage);
    }
    
    return data;
  } catch (error) {
    console.error('Error uploading file:', error);
    throw error;
  }
};

/**
 * Upload an image file with configuration data
 * @param file - The image file to upload
 * @param config - Configuration data
 * @returns Promise with the upload response
 */
export const uploadImageFile = async (file: File, config: any) => {
  try {
    // Create form data
    const formData = new FormData();
    formData.append('file', file);
    formData.append('config', JSON.stringify(config));
    
    // Send request to backend - Note the image-specific endpoint
    const response = await fetch(`${API_BASE_URL}/image-upload`, {
      method: 'POST',
      body: formData,
    });
    
    // Parse response
    const data = await response.json();
    
    if (!response.ok) {
      // Format error message with details if available
      let errorMessage = data.error || data.message || 'Failed to upload image';
      
      // Add details to the error message if available
      if (data.details) {
        if (Array.isArray(data.details)) {
          // If details is an array, format each item on a new line
          errorMessage = `${errorMessage}\n\nDetails:\n${data.details.map(detail => `• ${detail}`).join('\n')}`;
        } else if (typeof data.details === 'string') {
          // If details is a string, add it on a new line
          errorMessage = `${errorMessage}\n\nDetails:\n${data.details}`;
        }
      }
      
      throw new Error(errorMessage);
    }
    
    return data;
  } catch (error) {
    console.error('Error uploading image file:', error);
    throw error;
  }
};

/**
 * Process validation data
 * @param validationData - The validation data to process
 * @param projectId - Project ID
 * @returns Promise with the processed data
 */
export const processValidationData = async (validationData: any, projectId?: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/process-validation`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ...validationData,
        project_id: projectId
      }),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // Format error message with details if available
      let errorMessage = data.error || data.message || 'Failed to process validation data';
      
      // Add details to the error message if available
      if (data.details) {
        if (Array.isArray(data.details)) {
          errorMessage = `${errorMessage}:\n${data.details.join('\n')}`;
        } else {
          errorMessage = `${errorMessage}:\n${data.details}`;
        }
      }
      
      throw new Error(errorMessage);
    }
    
    return data;
  } catch (error) {
    console.error('Error processing validation data:', error);
    throw error;
  }
};

/**
 * Transform tree data
 * @param treeData - The tree data to transform
 * @param projectId - Project ID
 * @returns Promise with the transformed data
 */
export const transformTreeData = async (treeData: any, projectId?: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/transform`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        tree_data: treeData,
        project_id: projectId
      }),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // Format error message with details if available
      let errorMessage = data.error || data.message || 'Failed to transform data';
      
      // Add details to the error message if available
      if (data.details) {
        if (Array.isArray(data.details)) {
          errorMessage = `${errorMessage}\n\nDetails:\n${data.details.map((detail: string) => `• ${detail}`).join('\n')}`;
        } else if (typeof data.details === 'string') {
          errorMessage = `${errorMessage}\n\nDetails:\n${data.details}`;
        }
      }
      
      throw new Error(errorMessage);
    }
    
    return data;
  } catch (error) {
    console.error('Error transforming tree data:', error);
    throw error;
  }
};

/**
 * Download a specific file
 * @param filePath - Path to the file
 * @param filename - Name for the downloaded file
 * @returns Promise that resolves when download starts or rejects on error
 */
export const downloadFile = async (filePath: string, filename?: string) => {
  try {
    // Reset error state
    console.log("Attempting to download file:", filePath);
    
    // Use fetch to handle any API errors properly
    const response = await fetch(`${API_BASE_URL}/download?file=${encodeURIComponent(filePath)}`);
    
    console.log("Download response status:", response.status);
    if (!response.ok) {
      if (response.headers.get("content-type")?.includes("application/json")) {
        const errorData = await response.json();
        throw new Error(errorData.details || errorData.message || errorData.error || 'Download failed');
      } else {
        throw new Error(`Download failed with status: ${response.status}`);
      }
    }
    
    const blob = await response.blob();
    console.log("Received blob:", blob.type, blob.size, "bytes");
    
    // Create a blob URL and trigger download
    const blobUrl = window.URL.createObjectURL(blob);
    
    // Create an anchor element
    const link = document.createElement('a');
    link.href = blobUrl;
    
    // Use the provided filename or extract it from the file path
    const downloadFilename = filename || filePath.split('/').pop() || filePath.split('\\').pop() || 'download.file';
    link.download = downloadFilename;
    
    // Append to the document
    document.body.appendChild(link);
    
    // Trigger the download
    link.click();
    
    // Clean up
    document.body.removeChild(link);
    window.URL.revokeObjectURL(blobUrl);
    
    return { 
      status: "success", 
      message: "Download successful", 
      filename: downloadFilename 
    };
  } catch (error) {
    console.error('Download error:', error);
    return { 
      status: "error", 
      message: error instanceof Error ? error.message : "Failed to download file" 
    };
  }
};

/**
 * Download all workflow files as a zip
 * @param filePaths - Object containing paths to the files
 * @returns Promise that resolves when download starts or rejects on error
 */
export const downloadAllFiles = async (filePaths: { 
  mcw_file?: string; 
  wcm_file?: string;
  metadata_file?: string;
}) => {
  try {
    // Construct the URL with query parameters for the files
    let downloadUrl = `${API_BASE_URL}/download-all?`;
    
    const params = [];
    
    if (filePaths.mcw_file) {
      params.push(`mcw_file=${encodeURIComponent(filePaths.mcw_file)}`);
    }
    
    if (filePaths.wcm_file) {
      params.push(`wcm_file=${encodeURIComponent(filePaths.wcm_file)}`);
    }
    
    if (filePaths.metadata_file) {
      params.push(`metadata_file=${encodeURIComponent(filePaths.metadata_file)}`);
    }
    
    downloadUrl += params.join('&');
    
    // Download the zip file
    const zipFilename = `workflow_files_${new Date().getTime()}.zip`;
    return await downloadFile(downloadUrl, zipFilename);
  } catch (error) {
    console.error('Error downloading all files:', error);
    return { 
      status: "error", 
      message: error instanceof Error ? error.message : "Failed to download files" 
    };
  }
};

// -------- FOLLOWING FUNCTIONS ARE FOR IMAGE WORKFLOW --------

/**
 * Upload an image for image workflow processing
 * @param file - The image file to upload
 * @returns Promise with the upload response
 */
export const uploadImage = async (file: File) => {
  try {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/image/upload`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to upload image');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error uploading image:', error);
    throw error;
  }
};

/**
 * Process a previously uploaded image
 * @param filename - The filename of the uploaded image
 * @returns Promise with the processing response
 */
export const processImage = async (filename: string) => {
  try {
    const response = await fetch(`${API_BASE_URL}/image/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ filename }),
    });
    
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to process image');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error processing image:', error);
    throw error;
  }
};

/**
 * Get workflow data for an image
 * @param filename - The filename to get workflow data for
 * @returns Promise with the workflow data
 */
export const getWorkflowData = async (filename: string) => {
  try {
    console.log(`Attempting to fetch workflow data for file: ${filename}`);
    
    const response = await fetch(`${API_BASE_URL}/image/workflows/${filename}`);
    
    if (!response.ok) {
      console.error(`Failed to fetch workflow data. Status: ${response.status} ${response.statusText}`);
      
      let errorDetail = '';
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.error || '';
        if (errorJson.available_files) {
          errorDetail += `\n\nAvailable files: ${errorJson.available_files.join(', ')}`;
        }
      } catch (e) {
        errorDetail = response.statusText;
      }
      
      if (response.status === 404) {
        console.error(`File not found: ${filename}`);
        throw new Error(`File not found: ${filename}\n${errorDetail}`);
      }
      
      throw new Error(`API Error (${response.status}): ${errorDetail}`);
    }
    
    const data = await response.json();
    console.log(`Successfully fetched workflow data for ${filename}`);
    return data;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      console.error('Network error:', error);
      throw new Error(`Network error: Could not connect to server. Please ensure the backend API is running and accessible.`);
    }
    console.error('Error fetching workflow data:', error);
    throw error;
  }
};

/**
 * Get the current filename from the backend
 */
export const getCurrentFile = async () => {
  try {
    console.log('Fetching current file information from server...');
    const response = await fetch(`${API_BASE_URL}/image/current-file`);
    
    if (!response.ok) {
      console.error(`Failed to get current file. Status: ${response.status} ${response.statusText}`);
      if (response.status === 404) {
        console.error('No current file found in server configuration');
        throw new Error('No current file found. Please upload an image first.');
      }
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to get current file info');
    }
    
    const data = await response.json();
    console.log(`Current file info retrieved: ${JSON.stringify(data)}`);
    return data;
  } catch (error) {
    console.error('Error getting current file:', error);
    throw error;
  }
};

/**
 * Get any available image from the server
 */
export const getAvailableImage = async () => {
  try {
    // First try to get the current file
    try {
      const fileInfo = await getCurrentFile();
      if (fileInfo && fileInfo.filename) {
        return fileInfo.filename;
      }
      
      // If that fails but there are available images, use the first one
      if (fileInfo && fileInfo.available_images && fileInfo.available_images.length > 0) {
        return fileInfo.available_images[0];
      }
    } catch (e) {
      console.log('No current file found, trying other methods');
    }
    
    // Try to infer image name from output files
    const outputsResponse = await fetch(`${API_BASE_URL}/image/outputs`);
    if (outputsResponse.ok) {
      const data = await outputsResponse.json();
      if (data && data.files && data.files.length > 0) {
        // Get the base name of the first output file and assume there's a matching image
        const outputFile = data.files[0];
        return outputFile.replace('_gpt_op.json', '.png');
      }
    }
    
    return null;
  } catch (error) {
    console.error('Error getting any available image:', error);
    return null;
  }
};

/**
 * Generate workflow files based on selected options
 * @param filename - The filename of the original image
 * @param options - Object specifying which files to generate (mcw, wcm, metadata)
 * @returns Promise with the generation response containing generated file names
 */
export const generateWorkflowFiles = async (filename: string, options: { mcw?: boolean; wcm?: boolean; metadata?: boolean }) => {
  try {
    console.log(`Attempting to generate files for ${filename} with options:`, options);
    const response = await fetch(`${API_BASE_URL}/image/generate-files`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ filename, options }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Failed to generate workflow files');
    }

    const data = await response.json();
    console.log('Generated files response:', data);
    if (data.success) {
       return data.generated_files; // Return the object with generated file names
    } else {
       throw new Error(data.message || 'File generation did not report success');
    }
  } catch (error) {
    console.error('Error generating workflow files:', error);
    throw error;
  }
};

/**
 * Sends a task to the file processing agent blueprint and returns the fetch response for streaming.
 * @param payload - The task payload including message with parts (text, file URIs).
 * @returns A Promise resolving to the Fetch Response object.
 */
export const sendFileProcessingTask = async (payload: any): Promise<Response> => {
  console.log("Sending file processing task payload:", payload);
  const response = await fetch(`${API_BASE_URL}/file-preprocessing/tasks/sendSubscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    // Attempt to read error response body if available
    let errorDetail = response.statusText;
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || JSON.stringify(errorJson);
    } catch (e) { /* ignore json parsing errors */ }
    throw new Error(`Task submission failed: ${response.status} ${errorDetail}`);
  }

  return response; // Return the response object for streaming
};

/**
 * Gets the status of a file processing task.
 * @param taskId - The ID of the task.
 * @returns A Promise resolving to the task status object.
 */
export const getFileProcessingTaskStatus = async (taskId: string): Promise<any> => {
  console.log(`Fetching status for file processing task: ${taskId}`);
  const response = await fetch(`${API_BASE_URL}/file-preprocessing/tasks/get`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: taskId }),
  });

  if (!response.ok) {
     let errorDetail = response.statusText;
     try {
       const errorJson = await response.json();
       errorDetail = errorJson.detail || JSON.stringify(errorJson);
     } catch (e) { /* ignore json parsing errors */ }
     throw new Error(`Failed to fetch task status: ${response.status} ${errorDetail}`);
  }

  return response.json();
};

/**
 * Requests cancellation of a file processing task.
 * @param taskId - The ID of the task.
 * @returns A Promise resolving to the task status object after cancellation request.
 */
export const cancelFileProcessingTask = async (taskId: string): Promise<any> => {
  console.log(`Requesting cancellation for file processing task: ${taskId}`);
  const response = await fetch(`${API_BASE_URL}/file-preprocessing/tasks/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id: taskId }),
  });

  if (!response.ok) {
     let errorDetail = response.statusText;
     try {
       const errorJson = await response.json();
       errorDetail = errorJson.detail || JSON.stringify(errorJson);
     } catch (e) { /* ignore json parsing errors */ }
     throw new Error(`Failed to request task cancellation: ${response.status} ${errorDetail}`);
  }

  return response.json();
};
