import asyncio
import configparser
import logging
import os
import uuid
import json
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Literal, Optional
import base64
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse, FileResponse
from pydantic import BaseModel
import uvicorn
from fastapi.middleware.cors import CORSMiddleware

# Attempt to import the original MainAgent and its dependencies
# This assumes main_agent.py and its modules are in the python path or same directory
try:
    from .main_agent import MainAgent
    from .logging_module import LoggingModule # For setting up a logger instance
except ImportError:
    # This might happen if running main_agent2.py directly from agent_core
    # Adjust based on your project structure if needed
    from main_agent import MainAgent
    from logging_module import LoggingModule


# --- A2A Protocol Data Models (Simplified) ---

class AgentProvider(BaseModel):
    name: str = "FileProcessingAgent-A2A"
    url: Optional[str] = None

class AgentCapabilities(BaseModel):
    streaming: bool = True
    pushNotifications: bool = False
    stateTransitionHistory: bool = True

class AgentSkill(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    inputModes: Optional[List[str]] = ["text", "file"] # Example
    outputModes: Optional[List[str]] = ["text", "file"] # Example

class AgentCard(BaseModel):
    name: str = "Autonomous Code Generation Agent (A2A)"
    description: str = "An A2A-compliant agent that autonomously generates, executes, and validates code based on user instructions."
    url: str # Base URL of this agent service
    provider: Optional[AgentProvider] = AgentProvider()
    version: str = "0.1.0-a2a"
    documentationUrl: Optional[str] = None
    capabilities: AgentCapabilities = AgentCapabilities()
    authentication: Optional[Dict[str, Any]] = None # Example: {"type": "apiKey", "in": "header", "name": "X-API-KEY"}
    defaultInputModes: List[str] = ["text"]
    defaultOutputModes: List[str] = ["text"]
    skills: List[AgentSkill] = [
        AgentSkill(
            id="generate_and_run_code",
            name="Generate and Run Code",
            description="Takes natural language instructions, generates Python code, executes it, validates output, and retries if necessary."
        )
    ]

class FileContent(BaseModel):
    name: Optional[str] = None
    mimeType: Optional[str] = None
    bytes: Optional[str] = None # Base64 encoded
    uri: Optional[str] = None

class Part(BaseModel):
    type: Literal["text", "file", "data"]
    text: Optional[str] = None
    file: Optional[FileContent] = None
    data: Optional[Dict[str, Any]] = None # For structured data/forms
    metadata: Optional[Dict[str, Any]] = None

class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: List[Part]
    metadata: Optional[Dict[str, Any]] = None

class TaskStatus(BaseModel):
    state: Literal["submitted", "working", "input-required", "completed", "canceled", "failed", "unknown"]
    message: Optional[Message] = None
    timestamp: str # ISO 8601

class Artifact(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    parts: List[Part]
    index: int = 0
    append: Optional[bool] = None
    lastChunk: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None

class Task(BaseModel):
    id: str
    sessionId: Optional[str] = None
    status: TaskStatus
    artifacts: Optional[List[Artifact]] = None
    history: Optional[List[Message]] = None # If requested
    metadata: Optional[Dict[str, Any]] = None

class TaskSendParams(BaseModel):
    id: Optional[str] = None # Client can suggest, server can override/generate
    sessionId: Optional[str] = None
    message: Message
    pushNotification: Optional[Dict[str, Any]] = None # Simplified
    historyLength: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

class TaskIdParams(BaseModel):
    id: str

class TaskQueryParams(BaseModel):
    id: str
    historyLength: Optional[int] = None

class TaskStatusUpdateEvent(BaseModel):
    id: str # Task ID
    status: TaskStatus
    final: bool = False
    metadata: Optional[Dict[str, Any]] = None

class TaskArtifactUpdateEvent(BaseModel):
    id: str # Task ID
    artifact: Artifact
    final: bool = False
    metadata: Optional[Dict[str, Any]] = None


# --- Global State & Configuration ---
# For a production system, use a proper database or distributed cache for task_store
task_store: Dict[str, Task] = {}
# For streaming updates: one queue per task ID
stream_queues: Dict[str, asyncio.Queue] = {}
# To store paths of generated downloadable files
downloadable_files: Dict[str, str] = {}

CONFIG_FILE_NAME = "configuration.ini"
DEFAULT_INSTRUCTION_FILENAME_PREFIX = "temp_a2a_instructions_"
DOWNLOADS_DIR = "Output" # Directory for saving downloadable output files

# --- Helper Functions ---

def get_iso_timestamp() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def generate_task_id() -> str:
    return str(uuid.uuid4())

# --- Helper Functions related to file handling and config update ---
def update_input_file_paths_in_config(file_paths: list[str], workspace_root: str):
    config_path = os.path.join(workspace_root, CONFIG_FILE_NAME)
    config = configparser.ConfigParser()
    config.read(config_path)
    if not config.has_section('AgentSettings'):
        config.add_section('AgentSettings')
    if file_paths:
        config.set('AgentSettings', 'input_file_paths', ','.join(file_paths))
    else:
        config.set('AgentSettings', 'input_file_paths', 'none')
    with open(config_path, 'w') as configfile:
        config.write(configfile)

def save_file_part(part, task_id: str, workspace_root: str):
    """Saves a file part (either bytes or via URI) and returns the absolute path.

    If part.file.bytes is present, saves the base64 encoded content.
    If part.file.uri is present, assumes it's a relative path within the workspace (e.g., in 'uploads')
    and resolves the absolute path. Does NOT move or copy the file if using URI.
    """
    file_info = part.file
    if file_info is None: # Should not happen based on Pydantic model, but safety check
        logger.error("Received a file part with no file_info.")
        return None

    if file_info.bytes:
        # Existing logic for handling base64 bytes
        # Sanitize filename from the name provided in the A2A message part
        filename = os.path.basename(file_info.name) if file_info.name else f"uploaded_bytes_{task_id}"
        uploads_dir = os.path.join(workspace_root, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        # Append task_id to the filename to associate the uploaded file with the task
        save_filename = f"{task_id}_{filename}"
        save_path = os.path.join(uploads_dir, save_filename)
        # TODO: Add file type validation (e.g., check extension against ALLOWED_EXTENSIONS)
        
        try:
            file_bytes = base64.b64decode(file_info.bytes)
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            logger.info(f"Saved uploaded file from bytes to: {save_path}")
            return os.path.abspath(save_path) # Return absolute path
        except Exception as e:
            logger.error(f"Error saving uploaded file from bytes {filename}: {e}")
            return None # Indicate failure

    elif file_info.uri:
        # New logic for handling file URIs
        # Assume URI is a path relative to the workspace root
        relative_path = file_info.uri
        # Basic sanitization to prevent directory traversal above the workspace root
        # This is a crucial security step.
        if ".." in relative_path or relative_path.startswith('/'):
             logger.error(f"Potential directory traversal attempt with URI: {relative_path}")
             return None

        resolved_path = os.path.join(workspace_root, relative_path)
        resolved_path = os.path.abspath(resolved_path) # Resolve to absolute path

        # Ensure the resolved path is still within the workspace_root (canonical path check)
        if not resolved_path.startswith(os.path.abspath(workspace_root)):
            logger.error(f"Resolved URI path is outside workspace root: {resolved_path}")
            return None

        if not os.path.exists(resolved_path) or not os.path.isfile(resolved_path):
            logger.error(f"File referenced by URI not found or is not a file: {resolved_path}")
            return None
            
        logger.info(f"Using file from URI for task {task_id}: {resolved_path}")
        # We don't save/copy the file again, just return the resolved absolute path
        return resolved_path

    else:
        logger.warning("File part has neither bytes nor URI.")
        return None # Neither bytes nor URI found

def load_agent_config():
    """Loads configuration from configuration.ini. Only reads service_account_json_path, gemini_model_name, agent_max_retries, agent_execution_timeout."""
    config = configparser.ConfigParser()
    script_dir = os.path.dirname(os.path.abspath(__file__)) # agent_core
    workspace_root = os.path.dirname(script_dir) # Parent of agent_core
    
    config_file_path_workspace = os.path.join(workspace_root, CONFIG_FILE_NAME)
    config_file_path_local = os.path.join(script_dir, CONFIG_FILE_NAME) # Less likely

    actual_config_path = None
    if os.path.exists(config_file_path_workspace):
        actual_config_path = config_file_path_workspace
    elif os.path.exists(config_file_path_local):
        actual_config_path = config_file_path_local
    
    parsed_config = {
        "gemini_model_name": "gemini-2.5-pro-preview-05-06", # Default if not found
        "gcp_service_account_file": None, # Default is None, not a specific file
        "agent_log_level": logging.INFO, 
        "agent_max_retries": 2, # Default if not found
        "agent_execution_timeout": 20, # Default if not found
        "agent_log_file": "main_agent2_a2a.log" # Default log file name
    }

    if actual_config_path:
        try:
            config.read(actual_config_path)
            if config.has_section('VertexAI'):
                parsed_config["gemini_model_name"] = config.get('VertexAI', 'model_name', fallback=parsed_config["gemini_model_name"])
                parsed_config["gcp_service_account_file"] = config.get('VertexAI', 'service_account_json_path', fallback=parsed_config["gcp_service_account_file"])
            if config.has_section('AgentSettings'):
                parsed_config["agent_max_retries"] = config.getint('AgentSettings', 'agent_max_retries', fallback=parsed_config["agent_max_retries"])
                parsed_config["agent_execution_timeout"] = config.getint('AgentSettings', 'agent_execution_timeout', fallback=parsed_config["agent_execution_timeout"])
            # Read log_level and log_file from [LOG] section
            if config.has_section('LOG'):
                log_level_str = config.get('LOG', 'log_level', fallback="INFO").upper()
                parsed_config["agent_log_level"] = getattr(logging, log_level_str, logging.INFO)
                parsed_config["agent_log_file"] = config.get('LOG', 'log_file', fallback=parsed_config["agent_log_file"])
            print(f"Loaded A2A agent configuration from: {actual_config_path}")
        except Exception as e:
            print(f"Error reading A2A agent config '{actual_config_path}': {e}. Using defaults.")
    else:
        print(f"A2A agent config file '{CONFIG_FILE_NAME}' not found in expected locations. Using defaults.")
    return parsed_config

AGENT_CONFIG = load_agent_config()

# Initialize logger (can use the one from logging_module or a new one)
lm = LoggingModule(log_file=AGENT_CONFIG["agent_log_file"], log_level=AGENT_CONFIG["agent_log_level"])
logger = lm.get_logger() if hasattr(lm, 'get_logger') else lm.logger

async def run_main_agent_for_a2a(task_id: str, instructions_text: str, input_file_paths: list[str], stream_q: Optional[asyncio.Queue]):
    logger.info(f"Task {task_id}: Initializing MainAgent for A2A processing.")
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_main_agent_instruction_file = "instructions.txt"
    original_main_agent_instruction_path = os.path.join(workspace_root, original_main_agent_instruction_file)

    # Get config values
    service_account_path = AGENT_CONFIG["gcp_service_account_file"]
    agent_execution_timeout = AGENT_CONFIG["agent_execution_timeout"]
    agent_max_retries = AGENT_CONFIG["agent_max_retries"]
    gcp_project_id = None
    gcp_location = None
    if not service_account_path or str(service_account_path).strip().lower() in ("", "none"):
        logger.error(f"GCP service account file is not set in the config file. Please set 'service_account_json_path' under [VertexAI] in {CONFIG_FILE_NAME}.")
        current_status = TaskStatus(state="failed", timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[Part(type="text", text="GCP service account file is not set in the config file. Please set 'service_account_json_path' under [VertexAI] in configuration.ini.")]))
        task_store[task_id].status = current_status
        if stream_q: await stream_q.put(TaskStatusUpdateEvent(id=task_id, status=current_status, final=True))
        return
    try:
        with open(service_account_path, 'r', encoding='utf-8') as f:
            sa_data = json.load(f)
            gcp_project_id = sa_data.get('project_id')
            # Try to get location from service account JSON (custom field or fallback)
            gcp_location = sa_data.get('location')
        if not gcp_project_id:
            logger.error(f"'project_id' not found in service account file: {service_account_path}")
            current_status = TaskStatus(state="failed", timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[Part(type="text", text=f"'project_id' not found in service account file: {service_account_path}")]))
            task_store[task_id].status = current_status
            if stream_q: await stream_q.put(TaskStatusUpdateEvent(id=task_id, status=current_status, final=True))
            return
        if not gcp_location:
            # Default to 'us-central1' if not present in JSON
            gcp_location = "us-central1"
    except Exception as e:
        logger.error(f"Could not read project_id/location from service account file: {e}")
        current_status = TaskStatus(state="failed", timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[Part(type="text", text=f"Could not read project_id/location from service account file: {e}")]))
        task_store[task_id].status = current_status
        if stream_q: await stream_q.put(TaskStatusUpdateEvent(id=task_id, status=current_status, final=True))
        return

    main_agent_instance = MainAgent(
        gemini_model_name=AGENT_CONFIG["gemini_model_name"],
        log_level=AGENT_CONFIG["agent_log_level"],
        max_retries=agent_max_retries,
        execution_timeout=agent_execution_timeout,
        service_account_json_path=service_account_path,
        gcp_project_id=gcp_project_id,
        gcp_location=gcp_location
    )

    current_status = TaskStatus(state="submitted", timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[Part(type="text", text="Task submitted for processing.")]))
    task_store[task_id].status = current_status
    if stream_q: await stream_q.put(TaskStatusUpdateEvent(id=task_id, status=current_status))

    logger.info(f"Task {task_id}: Writing provided instructions to '{original_main_agent_instruction_path}' for MainAgent.")
    try:
        with open(original_main_agent_instruction_path, "w", encoding="utf-8") as f:
            f.write(instructions_text)
    except Exception as e:
        logger.error(f"Task {task_id}: Failed to write temporary instruction file: {e}")
        current_status = TaskStatus(state="failed", timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[Part(type="text", text=f"Internal error: could not prepare instructions: {e}")]))
        task_store[task_id].status = current_status
        if stream_q: await stream_q.put(TaskStatusUpdateEvent(id=task_id, status=current_status, final=True))
        return

    try:
        logger.info(f"Task {task_id}: Running MainAgent.run() for actual processing.")
        # Call the real agent and get the result
        result = await asyncio.to_thread(main_agent_instance.run)

        # Map result to A2A TaskStatus and Artifact
        status_map = {
            "SUCCESS": "completed",
            "FAILURE_NO_INPUT": "failed",
            "FAILURE_INSTRUCTION_PROCESSING": "failed",
            "FAILURE_CODE_GENERATION": "failed",
            "FAILURE_MAX_RETRIES": "failed",
            "CRITICAL_FAILURE_UNHANDLED_EXCEPTION": "failed",
        }
        state = status_map.get(result.get("status", "unknown"), "unknown")
        message_text = result.get("message", "")
        current_status = TaskStatus(state=state, timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[Part(type="text", text=message_text)]))
        task_store[task_id].status = current_status

        # Build artifact if code was generated
        artifacts = []
        download_url = None
        download_filename = None

        # Determine the primary output content to save and make downloadable
        output_content_to_save = None
        output_filename = None

        # Prioritize saving execution stdout if available and task was successful
        if state == "completed" and result.get("execution_stdout"):
            output_content_to_save = result["execution_stdout"]
            output_filename = f"{task_id}_output.txt"
            logger.info(f"Task {task_id}: Saving execution stdout as primary output.")

        if output_content_to_save:
            downloads_dir_abs = os.path.join(workspace_root, DOWNLOADS_DIR)
            os.makedirs(downloads_dir_abs, exist_ok=True)
            download_path = os.path.join(downloads_dir_abs, output_filename)

            try:
                with open(download_path, "w", encoding="utf-8") as f:
                    f.write(output_content_to_save)
                downloadable_files[task_id] = download_path # Store the path
                # Construct the download URL
                download_url = f"/api/tasks/download/{task_id}"
                logger.info(f"Task {task_id}: Saved primary output to {download_path}. URL: {download_url}")

            except Exception as e:
                logger.error(f"Task {task_id}: Failed to save primary output for download: {e}", exc_info=True)
                download_url = None # Ensure download_url is None on failure

            # Prepare artifact parts
            artifact_parts = []
            artifact_description = "Output from the agent"

            # Include execution stdout/stderr as text parts
            if result.get("execution_stdout"):
                artifact_parts.append(Part(type="text", text=f"Execution STDOUT:\n{result['execution_stdout']}"))
                artifact_description += ", including execution output"
            if result.get("execution_stderr"):
                artifact_parts.append(Part(type="text", text=f"Execution STDERR:\n{result['execution_stderr']}"))
                artifact_description += " and errors"

            # Include validation feedback as a text part
            if result.get("validation_feedback"):
                artifact_parts.append(Part(type="text", text=f"Validation Feedback:\n{chr(10).join(result['validation_feedback'])}"))
                artifact_description += " and validation feedback"

            # Add a part indicating the downloadable file if successful
            if download_url and output_filename:
                artifact_parts.append(Part(type="text", text=f"\nDownloadable output available: {output_filename}")) # Simple text indicator
                # Or a file part with URI if the A2A client supports it, referencing the download URL
                # artifact_parts.append(Part(type='file', file=FileContent(name=output_filename, uri=download_url, mimeType='application/octet-stream')))

            # Create the artifact
            # Only create an artifact if there are parts to include
            if artifact_parts:
                artifact = Artifact(
                    name="task_results", # Generic name
                    description=artifact_description,
                    parts=artifact_parts
                )
                artifacts.append(artifact)
                task_store[task_id].artifacts = artifacts
                if stream_q:
                    # Send artifact update event (if any artifacts were created)
                    await stream_q.put(TaskArtifactUpdateEvent(id=task_id, artifact=artifact))


        # Send final status update
        # Include download URL and filename in metadata if available
        final_metadata = {"downloadUrl": download_url, "downloadFilename": output_filename} if download_url else {}

        final_status_update = TaskStatusUpdateEvent(id=task_id, status=current_status, final=True, metadata=final_metadata)

        if stream_q:
            await stream_q.put(final_status_update)

        logger.info(f"Task {task_id}: MainAgent processing completed with state: {state}. Download URL included: {bool(download_url)}")

    except Exception as e:
        logger.error(f"Task {task_id}: Error during MainAgent execution: {e}", exc_info=True)
        error_message_part = Part(type="text", text=f"An unexpected error occurred during agent execution: {str(e)}")
        current_status = TaskStatus(state="failed", timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[error_message_part]))
        task_store[task_id].status = current_status
        if stream_q: await stream_q.put(TaskStatusUpdateEvent(id=task_id, status=current_status, final=True))
    finally:
        # Clean up the temporary instruction file
        if os.path.exists(original_main_agent_instruction_path):
             try:
                 # Note: This might be tricky if MainAgent holds onto the file handle.
                 # Consider if MainAgent should delete it or if it's safe to delete here.
                 # For now, assume it's safe after MainAgent.run returns.
                 # If not, this cleanup might need to be handled differently.
                 # Let's add a small delay and try, or perhaps just leave it for OS cleanup.
                 # Given the risk, let's NOT delete it here immediately. A separate cleanup process might be better.
                 pass # Skipping deletion for now
             except Exception as e:
                 logger.warning(f"Task {task_id}: Could not delete temporary instruction file '{original_main_agent_instruction_path}': {e}")

        # --- Clean up input files from uploads directory ---
        uploads_dir_abs = os.path.join(workspace_root, "uploads") # Directory where input files are expected
        logger.info(f"Task {task_id}: Cleaning up {len(input_file_paths)} input files from uploads.")
        for file_path in input_file_paths:
            resolved_file_path = os.path.abspath(file_path)
            # Basic security check: ensure the file is within the uploads directory
            if resolved_file_path.startswith(uploads_dir_abs):
                if os.path.exists(resolved_file_path):
                    try:
                        os.remove(resolved_file_path)
                        logger.info(f"Task {task_id}: Deleted input file: {resolved_file_path}")
                    except OSError as e:
                        logger.warning(f"Task {task_id}: Could not delete input file {resolved_file_path}: {e}")
                else:
                    logger.warning(f"Task {task_id}: Input file not found during cleanup: {resolved_file_path}")
            else:
                logger.error(f"Task {task_id}: Skipping deletion of file outside uploads directory: {resolved_file_path}")

        logger.info(f"Task {task_id}: Processing finished.")


# --- FastAPI Application ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("A2A Agent Server is starting up...")
    # Initialize any resources if needed
    # Ensure the uploads directory exists
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uploads_dir = os.path.join(workspace_root, "uploads", "temp") # Temp dir for uploads
    os.makedirs(uploads_dir, exist_ok=True)
    # Ensure the downloads directory exists
    downloads_dir_abs = os.path.join(workspace_root, DOWNLOADS_DIR)
    os.makedirs(downloads_dir_abs, exist_ok=True)

    yield
    logger.info("A2A Agent Server is shutting down...")
    

app = FastAPI(lifespan=lifespan, title="A2A MainAgent Wrapper", version="0.1.0")

# Add CORS middleware for local UI testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon.ico file."""
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    favicon_path = os.path.join(workspace_root, "favicon.ico")
    if os.path.exists(favicon_path) and os.path.isfile(favicon_path):
        return FileResponse(path=favicon_path, media_type="image/x-icon")
    raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/.well-known/agent.json", response_model=AgentCard)
async def get_agent_card(request: Request):
    base_url = str(request.base_url)
    if base_url.endswith('/'): # Ensure no double slash later
        base_url = base_url[:-1]
    return AgentCard(url=f"{base_url}/api")


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Accepts a file upload, saves it, and returns a URI reference."""
    try:
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Save to a temporary uploads sub-directory or directly to uploads
        # Using a temporary directory structure for clarity
        temp_uploads_dir = os.path.join(workspace_root, "uploads", "temp")
        os.makedirs(temp_uploads_dir, exist_ok=True)

        # Generate a unique filename to avoid collisions
        unique_filename = f"{uuid.uuid4()}_{file.filename}"
        save_path = os.path.join(temp_uploads_dir, unique_filename)
    
        # Save the file
        with open(save_path, "wb") as f:
            # Read file in chunks to handle large files efficiently
            while chunk := await file.read(1024 * 1024): # Read 1MB chunks
                f.write(chunk)

        # Create a URI reference for the saved file
        # This URI is relative to the workspace root and points to the temp uploads folder
        relative_uri = os.path.join("uploads", "temp", unique_filename).replace('\\', '/') # Use forward slashes for URI style
        
        logger.info(f"Uploaded file saved to {save_path}. URI: {relative_uri}")

        return JSONResponse({"uri": relative_uri})

    except Exception as e:
        logger.error(f"Error during file upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {e}")


@app.post("/api/tasks/send", response_model=Task)
async def tasks_send(params: TaskSendParams):
    task_id = params.id or generate_task_id()
    if task_id in task_store: # Or in active streams
        raise HTTPException(status_code=409, detail="Task ID already exists. Use tasks/get or a unique ID.")

    instruction_text = ""
    file_paths_for_agent = [] # List of server-side paths to pass to MainAgent
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for part in params.message.parts:
        if part.type == "text" and part.text:
            instruction_text += part.text + "\n"
        elif part.type == "file" and part.file:
            # Use the updated save_file_part that handles both bytes (old) and uri (new)
            saved_path = save_file_part(part, task_id, workspace_root)
            if saved_path:
                file_paths_for_agent.append(saved_path)
            # Note: If save_file_part fails, it logs an error and returns None.
            # The current logic continues processing other parts.
            # Consider adding error handling here if a failed file save/resolution should fail the task.

    # Update the config file with the paths of successfully resolved/saved files
    # The MainAgent will read these paths from the config.
    update_input_file_paths_in_config(file_paths_for_agent, workspace_root)

    if not instruction_text and not file_paths_for_agent:
         raise HTTPException(status_code=400, detail="No text instructions or file inputs provided.")
    
    logger.info(f"Received tasks/send for new task ID {task_id}. Instructions: {instruction_text[:100]}... Files: {file_paths_for_agent}")

    initial_status = TaskStatus(state="submitted", timestamp=get_iso_timestamp(), message=params.message) # Store the received message
    task = Task(id=task_id, sessionId=params.sessionId, status=initial_status, metadata=params.metadata)
    task_store[task_id] = task

    # Pass the determined file_paths_for_agent to the async task function if needed, or rely on config
    # Currently, run_main_agent_for_a2a reads from config, so passing might be redundant but safer.
    # Let's rely on the config update for consistency with how MainAgent was designed to read inputs.
    asyncio.create_task(run_main_agent_for_a2a(task_id, instruction_text.strip(), file_paths_for_agent, None))

    return task


@app.post("/api/tasks/sendSubscribe")
async def tasks_send_subscribe(params: TaskSendParams, request: Request):
    task_id = params.id or generate_task_id()
    if task_id in task_store: # Or in active streams
        raise HTTPException(status_code=409, detail="Task ID already exists or is actively streaming.")

    instruction_text = ""
    file_paths_for_agent = [] # List of server-side paths to pass to MainAgent
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for part in params.message.parts:
        if part.type == "text" and part.text:
            instruction_text += part.text + "\n"
        elif part.type == "file" and part.file:
            # Use the updated save_file_part that handles both bytes (old) and uri (new)
            saved_path = save_file_part(part, task_id, workspace_root)
            if saved_path:
                file_paths_for_agent.append(saved_path)
            # Note: If save_file_part fails, it logs an error and returns None.
            # The current logic continues processing other parts.
            # Consider adding error handling here if a failed file save/resolution should fail the task.

    # Update the config file with the paths of successfully resolved/saved files
    # The MainAgent will read these paths from the config.
    update_input_file_paths_in_config(file_paths_for_agent, workspace_root)

    if not instruction_text and not file_paths_for_agent:
         raise HTTPException(status_code=400, detail="No text instructions or file inputs provided.")

    logger.info(f"Received tasks/sendSubscribe for new task ID {task_id}. Instructions: {instruction_text[:100]}... Files: {file_paths_for_agent}")

    initial_status = TaskStatus(state="submitted", timestamp=get_iso_timestamp(), message=params.message) # Store the received message
    task = Task(id=task_id, sessionId=params.sessionId, status=initial_status, metadata=params.metadata)
    task_store[task_id] = task

    stream_q = asyncio.Queue()
    stream_queues[task_id] = stream_q

    # Pass the determined file_paths_for_agent to the async task function if needed, or rely on config
    # Let's rely on the config update for consistency with how MainAgent was designed to read inputs.
    asyncio.create_task(run_main_agent_for_a2a(task_id, instruction_text.strip(), file_paths_for_agent, stream_q))

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from task {task_id} stream.")
                    break
                try:
                    update_event = await asyncio.wait_for(stream_q.get(), timeout=1.0)
                    if isinstance(update_event, TaskStatusUpdateEvent):
                        # Use model_dump_json to serialize Pydantic model, includes metadata
                        yield f"event: task_status_update\ndata: {update_event.model_dump_json()}\n\n"
                        if update_event.final:
                            logger.info(f"Task {task_id}: Sent final status update, closing stream.")
                            break
                    elif isinstance(update_event, TaskArtifactUpdateEvent):
                         # Use model_dump_json to serialize Pydantic model
                        yield f"event: task_artifact_update\ndata: {update_event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    continue
        except Exception as e_stream:
            logger.error(f"Error in stream for task {task_id}: {e_stream}", exc_info=True)
            error_message_part = Part(type="text", text=f"Streaming error: {e_stream}")
            error_status = TaskStatus(state="failed", timestamp=get_iso_timestamp(), message=Message(role="agent", parts=[error_message_part]))
            # Include error in final status update event
            yield f"event: task_status_update\ndata: {TaskStatusUpdateEvent(id=task_id, status=error_status, final=True).model_dump_json()}\n\n"
        finally:
            if task_id in stream_queues:
                del stream_queues[task_id]
            # Optionally clean up downloadable file if it was generated but stream ended prematurely?
            # Decided against automatic cleanup here; let it persist until server restart or separate cleanup.
            logger.info(f"Task {task_id} stream generator finished.")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/tasks/download/{task_id}")
async def download_task_output_file(task_id: str):
    """Serves the generated output file for a given task ID."""
    file_path = downloadable_files.get(task_id) # Get the path from our stored dictionary
    
    if not file_path:
         logger.warning(f"Download requested for task {task_id}, but no downloadable file found.")
         raise HTTPException(status_code=404, detail=f"No downloadable file found for task ID '{task_id}'.")

    # Security check: Ensure the file path is within the designated downloads directory
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    downloads_dir_abs = os.path.join(workspace_root, DOWNLOADS_DIR)
    resolved_file_path = os.path.abspath(file_path)

    if not resolved_file_path.startswith(downloads_dir_abs):
         logger.error(f"Attempted download path traversal: {resolved_file_path} is outside {downloads_dir_abs}")
         raise HTTPException(status_code=403, detail="Access denied.") # Forbidden

    if not os.path.exists(resolved_file_path) or not os.path.isfile(resolved_file_path):
         logger.error(f"Download requested for task {task_id}, file not found at expected path: {resolved_file_path}")
         raise HTTPException(status_code=404, detail=f"Downloadable file not found for task ID '{task_id}'.")

    logger.info(f"Serving downloadable file for task {task_id} from: {resolved_file_path}")

    # Determine mime type
    import mimetypes
    mime_type, _ = mimetypes.guess_type(resolved_file_path)
    if not mime_type:
        # Default for files where type can't be guessed
        mime_type = 'application/octet-stream'

    # Try to get the original filename if stored, otherwise use the saved filename
    original_filename = os.path.basename(resolved_file_path)
    # We could potentially store the user-friendly filename (like script.py) alongside the path
    # in the downloadable_files dictionary if needed, but using the saved filename is simpler.
    
    return FileResponse(path=resolved_file_path, filename=original_filename, media_type=mime_type)


@app.get("/api/tasks/{task_id}/artifacts/{filename}")
async def get_artifact_file(task_id: str, filename: str):
    """Serves a specific artifact file for a given task.
    Requires task_id and the filename of the artifact part.
    """
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID '{task_id}' not found.")

    # Basic sanitization to prevent directory traversal
    sanitized_filename = os.path.basename(filename)
    # Reconstruct the expected save path based on save_file_part logic
    # Artifact files are typically uploaded inputs, saved in 'uploads'
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # *** IMPORTANT SECURITY CHECK ***
    # Ensure the requested filename actually corresponds to a file artifact *associated with this specific task*
    # and that the resolved path is within the allowed uploads directory.

    artifact_part = None
    if task.artifacts:
        for artifact in task.artifacts:
            if artifact.parts:
                for part in artifact.parts:
                    # Check if this is a file part and the name matches the requested filename
                    if part.type == 'file' and part.file and part.file.name == filename:
                        # Found a matching artifact and file part with the correct name
                        # Now, need to confirm its saved path. If the file part included a URI,
                        # we need to re-resolve that URI. If it was bytes, we need the saved path.
                        # The save_file_part function returns the *absolute* path.
                        # We don't store the saved path in the artifact itself currently.
                        # This means we have to re-derive the path based on our saving logic.

                        # Assuming uploaded files saved via bytes or temp URI resolve to uploads/temp
                        expected_path_temp_upload = os.path.join(workspace_root, "uploads", "temp", f"{uuid.uuid4()}_{sanitized_filename}") # This doesn't work, need actual unique name
                        # Need a reliable way to map filename to saved path for artifacts.
                        # The current `save_file_part` logic names files like `{task_id}_{original_name}` in the main `uploads` dir.
                        expected_path = os.path.join(workspace_root, "uploads", f"{task_id}_{sanitized_filename}")
                        
                        # Check if this derived path exists AND if the artifact part *originally* referred to a file at this location or with this saved name.
                        # This is tricky without storing the saved_path in the Artifact Part metadata.
                        # For simplicity and basic security, let's check if the *derived* path exists and is within 'uploads'.
                        # This is a potential vulnerability if filenames can be arbitrary and match saved files outside uploads.
                        # A more robust approach stores the saved_path in the Artifact Part metadata.

                        resolved_path = os.path.abspath(expected_path) # Resolve the expected path

                        # Ensure resolved path is within the uploads directory
                        uploads_dir_abs = os.path.join(workspace_root, "uploads")
                        if not resolved_path.startswith(uploads_dir_abs):
                             logger.error(f"Artifact download path outside uploads directory: {resolved_path}")
                             raise HTTPException(status_code=403, detail="Access denied.") # Forbidden

                        if os.path.exists(resolved_path) and os.path.isfile(resolved_path):
                             # Found a potential match. Assume this is the correct file for now.
                             artifact_part = part
                             file_to_serve_path = resolved_path
                             break # Found the artifact part and derived path
                if artifact_part: break # Found the artifact part in this artifact

    if not artifact_part or not os.path.exists(file_to_serve_path):
        # File not found at the expected path OR the filename doesn't match any recorded artifact in the task
        logger.error(f"Attempted to access non-existent or unauthorized artifact file: Task ID {task_id}, Filename {filename}, Derived Path {file_to_serve_path if 'file_to_serve_path' in locals() else 'N/A'}")
        raise HTTPException(status_code=404, detail=f"Artifact file '{filename}' not found for task '{task_id}' or access denied.")

    logger.info(f"Serving artifact file for task {task_id}: {filename} from {file_to_serve_path}")

    # Determine mime type - could try to guess or use the one stored in the artifact if available
    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_to_serve_path)
    if not mime_type:
        mime_type = artifact_part.file.mimeType if artifact_part and artifact_part.file and artifact_part.file.mimeType else 'application/octet-stream'

    # Return the file as a FileResponse
    return FileResponse(path=file_to_serve_path, filename=sanitized_filename, media_type=mime_type)


@app.post("/api/tasks/get", response_model=Task)
async def tasks_get(params: TaskQueryParams):
    task = task_store.get(params.id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID '{params.id}' not found.")
    # TODO: Implement historyLength if needed
    logger.info(f"Received tasks/get for task ID {params.id}. Current state: {task.status.state}")
    return task

@app.post("/api/tasks/cancel", response_model=Task)
async def tasks_cancel(params: TaskIdParams):
    task = task_store.get(params.id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID '{params.id}' not found.")

    logger.info(f"Received tasks/cancel for task ID {params.id}.")
    
    # Basic cancellation: mark as canceled if not in a final state.
    # True cancellation would need to signal the running MainAgent task.
    if task.status.state not in ["completed", "failed", "canceled"]:
        task.status.state = "canceled"
        task.status.timestamp = get_iso_timestamp()
        task.status.message = Message(role="agent", parts=[Part(type="text", text="Task cancellation requested.")])
        
        # If there's an active stream queue, send a final cancel event
        if params.id in stream_queues:
            stream_q = stream_queues[params.id]
            # Include the cancellation message in the final status update metadata or message parts
            await stream_q.put(TaskStatusUpdateEvent(id=params.id, status=task.status, final=True))
        logger.info(f"Task {params.id} marked as canceled.")
    else:
        logger.warning(f"Task {params.id} is already in a final state ({task.status.state}), cannot cancel.")
    return task

@app.get("/", response_class=HTMLResponse)
async def serve_root_ui():
    return """
    <!DOCTYPE html>
    <html lang='en'>
    <head>
        <meta charset='UTF-8'>
        <title>Code Generation UI</title>
        <meta name='viewport' content='width=device-width, initial-scale=1.0'>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; /* Slightly updated font stack */
                line-height: 1.6; /* Improved line height for readability */
                background: linear-gradient(120deg, #e0e7ff 0%, #f7fafc 100%);
                margin: 0;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px; /* Add padding around the body for small screens */
                box-sizing: border-box;
                color: #333; /* Default text color */
            }
            .container {
                background: #fff;
                padding: 3em 2.5em; /* Increased padding top/bottom */
                border-radius: 18px;
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.18);
                max-width: 500px; /* Slightly increased max-width again */
                width: 100%;
                margin: 2em auto;
                display: flex;
                flex-direction: column;
                align-items: stretch;
                animation: fadeIn 0.7s;
                box-sizing: border-box;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(30px); }
                to { opacity: 1; transform: translateY(0); }
            }
            h1 {
                text-align: center;
                color: #2d3a5a;
                margin-bottom: 1.5em; /* Increased margin-bottom */
                font-weight: 600;
                letter-spacing: 0.8px; /* Increased letter spacing */
            }
            label {
                margin-bottom: 0.6em; /* Increased margin */
                color: #3b4252;
                font-size: 1.5em;
                font-weight: 500;
                display: block;
            }
            textarea {
                width: 100%;
                min-height: 150px; /* Increased min-height */
                border: 1px solid #cbd5e1; /* Thinner border */
                border-radius: 8px; /* Slightly more rounded */
                padding: 1.2em; /* Increased padding */
                font-size: 1em; /* Consistent font size */
                margin-bottom: 1.8em; /* Increased margin */
                resize: vertical;
                transition: border-color 0.2s, box-shadow 0.2s;
                box-shadow: 0 1px 3px rgba(99, 102, 241, 0.08); /* Refined shadow */
                box-sizing: border-box;
                font-family: inherit;
                line-height: 1.5; /* Line height for textarea */
            }
            textarea:focus {
                border-color: #6366f1; /* Color on focus */
                outline: none;
                box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
            }

            /* Styling for the custom file input area */
            .file-input-container {
                border: 2px dashed #cbd5e1; /* Dashed border */
                border-radius: 8px;
                padding: 1.5em; /* Padding inside the dashed area */
                margin-bottom: 1.8em; /* Consistent margin */
                background-color: #f8fafc; /* Light background */
                text-align: center;
                cursor: pointer; /* Indicate it's interactive */
                transition: border-color 0.2s, background-color 0.2s;
                position: relative; /* Needed for absolute positioning of hidden input */
            }
             .file-input-container:hover {
                 border-color: #a3b1cd; /* Darker border on hover */
                 background-color: #eef2ff; /* Lighter background on hover */
             }
            .file-input-container input[type='file'] {
                position: absolute; /* Hide the actual input */
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                opacity: 0; /* Make it completely invisible */
                cursor: pointer;
            }
             .file-input-container label {
                 display: block; /* Label for the custom area */
                 margin-bottom: 0.5em; /* Space below the label */
                 color: #4a5568; /* Darker grey color */
                 font-weight: 500;
                 font-size: 1em; /* Slightly smaller font for helper text */
             }
            .file-input-container .file-list {
                font-size: 0.9em;
                color: #555;
                margin-top: 0.8em;
                text-align: left;
            }
            .file-input-container .file-list div {
                 margin-bottom: 0.3em;
                 padding-left: 1em; /* Indent file names */
                 text-indent: -0.8em;
             }
             .file-input-container .file-list div::before {
                 content: '\2022'; /* Bullet point */
                 color: #6366f1;
                 display: inline-block;
                 width: 0.8em;
             }

            .row {
                margin-top: 0.5em; /* Adjusted margin */
                margin-bottom: 1em; /* Added margin */
                display: flex;
                align-items: center;
            }
            .row label[for='noFile'] {
                margin: 0 0 0 0.5em;
                font-size: 1em;
                color: #4b5563;
                font-weight: 400;
                display: inline;
            }
             .row input[type='checkbox'] {
                width: auto;
                margin-right: 0;
             }

            button {
                background: linear-gradient(90deg, #6366f1 0%, #2563eb 100%);
                color: #fff;
                border: none;
                padding: 1em 0;
                border-radius: 7px;
                font-size: 1.13em;
                font-weight: 600;
                cursor: pointer;
                margin-top: 2em; /* Increased top margin */
                box-shadow: 0 2px 8px rgba(99, 102, 241, 0.25);
                transition: background 0.3s ease, box-shadow 0.3s ease;
                width: 100%;
                letter-spacing: 0.5px;
            }
             button:hover {
                background: linear-gradient(90deg, #5054e0 0%, #1e54d4 100%);
            }
            button:active {
                 background: linear-gradient(90deg, #4347cc 0%, #1a49bc 100%);
                 box-shadow: 0 1px 4px rgba(99, 102, 241, 0.3);
            }
            button:disabled {
                background: #a5b4fc;
                cursor: not-allowed;
                box-shadow: none;
            }
            .result {
                margin-top: 2em;
                background: #f1f5f9;
                padding: 1.2em 1em;
                border-radius: 10px;
                min-height: 2.5em;
                color: #22223b;
                font-size: 1em; /* Consistent font size */
                box-shadow: 0 2px 8px rgba(99, 102, 241, 0.1);
                opacity: 0;
                transform: translateY(20px);
                transition: opacity 0.4s ease, transform 0.4s ease;
                word-break: break-word;
                white-space: pre-wrap;
            }
            .result.visible {
                opacity: 1;
                transform: translateY(0);
            }
            .spinner {
                display: inline-block;
                width: 22px;
                height: 22px;
                border: 3px solid #c7d2fe;
                border-top: 3px solid #6366f1;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin-right: 0.7em;
                vertical-align: middle;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .download-link { /* Style for the new download link */
                display: inline-block;
                margin-top: 15px; /* More space above */
                padding: 10px 18px; /* More padding */
                background: linear-gradient(90deg, #28a745 0%, #218838 100%); /* Green gradient */
                color: white;
                text-decoration: none;
                border-radius: 6px; /* Slightly more rounded */
                font-weight: 500; /* Slightly less bold */
                transition: background 0.3s ease, box-shadow 0.3s ease;
                box-shadow: 0 2px 8px rgba(40, 167, 69, 0.2); /* Green shadow */
            }
            .download-link:hover {
                background: linear-gradient(90deg, #218838 0%, #1e7e34 100%);
                box-shadow: 0 3px 10px rgba(40, 167, 69, 0.3);
            }
             .artifact-code pre code { /* Styling for code block within artifact */
                display: block;
                padding: 1em;
                background: #2b2b2b; /* Dark background for code */
                color: #f8f8f2; /* Light text */
                border-radius: 5px;
                overflow-x: auto; /* Enable horizontal scrolling for long lines */
                 word-break: normal; /* Prevent breaking long words */
                 white-space: pre; /* Preserve whitespace and line breaks */
            }


            @media (max-width: 600px) {
                .container { padding: 1.5em; max-width: 98vw; }
                h2 { font-size: 1.4em; margin-bottom: 1em; }
                button { font-size: 1.05em; padding: 0.8em 0;}
                label, textarea, input[type='file'] { font-size: 1em;}
                .result { font-size: 0.95em;}
                 .file-input-container { padding: 1em; }
            }
        </style>
    </head>
    <body>
        <div class='container'>
            <h1>Code Generation Agent</h1>
            <form id='agentForm' autocomplete='off'>
                <label for='instructions'>Instructions:</label>
                <textarea id='instructions' name='instructions' required placeholder='Describe what you want the agent to do...'></textarea>

                <label class='file-label'>Input Files:</label>
                 <div class='row'>
                    <input type='checkbox' id='noFile' name='noFile' checked>
                    <label for='noFile'>No input file required</label>
                </div>
                <div id='fileRow'>
                    <div class='file-input-container'>
                         <input type='file' id='inputFile' name='inputFile' multiple>
                         <label for='inputFile'>Click or drag files here to upload</label>
                         <div class='file-list' id='fileList'></div>
                    </div>
                </div>
                <button type='submit' id='submitBtn'>Submit</button>
            </form>
            <div class='result' id='result'></div>
            <div id="download-area" style="margin-top: 1em; text-align: center;"></div> <!-- Added download area -->
        </div>
        <script>
            const noFileCheckbox = document.getElementById('noFile');
            const fileRow = document.getElementById('fileRow');
            const fileInput = document.getElementById('inputFile');
            const fileListDiv = document.getElementById('fileList');
            const resultDiv = document.getElementById('result');
            const submitBtn = document.getElementById('submitBtn');
            const instructionsTextarea = document.getElementById('instructions');
            const downloadArea = document.getElementById('download-area'); // Get the download area

            function updateFileInputState() {
                const isDisabled = noFileCheckbox.checked;
                fileInput.disabled = isDisabled;
                // You could hide the file input container entirely if you prefer
                // fileRow.style.display = isDisabled ? 'none' : 'block';

                // Dim the file input container if disabled
                 const fileInputContainer = document.querySelector('.file-input-container');
                 if (isDisabled) {
                     fileInputContainer.style.opacity = 0.5;
                     fileInputContainer.style.pointerEvents = 'none'; // Disable interactions
                 } else {
                     fileInputContainer.style.opacity = 1;
                     fileInputContainer.style.pointerEvents = 'auto';
                 }
                 // Clear selected files when checkbox is checked
                 if (isDisabled && fileInput.files.length > 0) {
                     fileInput.value = ''; // Clear the file input
                     updateFileList(); // Update the displayed list
                 }
            }

            function updateFileList() {
                fileListDiv.innerHTML = ''; // Clear current list
                if (fileInput.files.length > 0) {
                    const fileCount = fileInput.files.length;
                    const fileText = fileCount === 1 ? 'file selected:' : 'files selected:';
                    fileListDiv.innerHTML = `<b>${fileCount} ${fileText}</b><br>`;
                    for (let i = 0; i < fileInput.files.length; i++) {
                        fileListDiv.innerHTML += `<div>${fileInput.files[i].name}</div>`;
                    }
                } else {
                    fileListDiv.innerHTML = ''; // Empty if no files
                }
            }

            noFileCheckbox.addEventListener('change', updateFileInputState);
            fileInput.addEventListener('change', updateFileList); // Update list when files are selected

            updateFileInputState(); // Initialize state

            const form = document.getElementById('agentForm');
            form.addEventListener('submit', handleSubmit);

            async function handleSubmit(event) {
                event.preventDefault();

                // Basic validation
                const instructions = instructionsTextarea.value.trim();
                if (!instructions) {
                    alert('Please provide instructions.');
                    instructionsTextarea.focus();
                    return;
                }
                const noFile = noFileCheckbox.checked;
                const files = fileInput.files;

                if (!noFile && files.length === 0) {
                     alert('Please select at least one input file or check "No input file required".');
                     return;
                }

                resultDiv.classList.remove('visible');
                resultDiv.innerHTML = `<span class='spinner'></span>Submitting task...`;
                downloadArea.innerHTML = ''; // Clear previous download link
                submitBtn.disabled = true;

                let parts = [{ type: 'text', text: instructions }];
                let uploadedFileParts = []; // To store file parts with URIs

                if (!noFile && files.length > 0) {
                     // --- File Upload Process ---
                     resultDiv.innerHTML = `<span class='spinner'></span>Uploading files...`;
                     for (let i = 0; i < files.length; i++) {
                        const file = files[i];
                        const formData = new FormData();
                        formData.append('file', file);

                        try {
                            const uploadResponse = await fetch('/api/upload', {
                                method: 'POST',
                                body: formData // No Content-Type header needed for FormData
                            });

                            if (!uploadResponse.ok) {
                                const errorText = await uploadResponse.text();
                                throw new Error(`Upload failed for ${file.name}: ${uploadResponse.status} ${errorText}`);
                            }

                            const uploadResult = await uploadResponse.json();
                            // Add the uploaded file info with URI to uploadedFileParts
                            uploadedFileParts.push({
                                type: 'file',
                                file: {
                                    name: file.name,
                                    mimeType: file.type || 'application/octet-stream',
                                    uri: uploadResult.uri // Use the URI from the upload response
                                    // No bytes needed here
                                }
                            });
                             resultDiv.innerHTML = `<span class='spinner'></span>Uploaded ${i + 1} of ${files.length} files...`;

                        } catch (error) {
                            console.error("Error uploading file:", file.name, error);
                            resultDiv.innerHTML = `<span style='color:#b91c1c;'>Error uploading file ${escapeHTML(file.name)}: ${escapeHTML(error.message || error)}</span>`;
                            resultDiv.classList.add('visible');
                            submitBtn.disabled = false;
                            return; // Stop processing if any file upload fails
                        }
                     }
                     resultDiv.innerHTML = `<span class='spinner'></span>File uploads complete. Submitting task...`;
                }

                // Add uploaded file parts (with URIs) to the main payload parts
                parts = parts.concat(uploadedFileParts);

                const payload = {
                    message: {
                        role: 'user',
                        parts: parts
                    }
                };

                try {
                    // Using /api/tasks/sendSubscribe to see streaming updates
                    // The fetch request below is now just to *initiate* the task after files are uploaded.
                    // The SSE connection opened earlier will handle updates.

                    // Re-initialize resultDiv for task updates after uploads
                    resultDiv.innerHTML = `<span class='spinner'></span>Submitting task...`;

                    let firstStatusUpdate = true; // Flag to handle initial status distinctly
                     // let accumulatedResponse = ''; // To accumulate response text or artifact HTML (No longer needed this way)

                     // Send initial payload via fetch to initiate the task on the server
                      const initialResponse = await fetch('/api/tasks/sendSubscribe', {
                          method: 'POST',
                          headers: { 'Content-Type': 'application/json' },
                          body: JSON.stringify(payload)
                      });

                      if (!initialResponse.ok) {
                         const err = await initialResponse.text();
                         console.error("Initial /sendSubscribe fetch failed:", initialResponse.status, err);
                         resultDiv.innerHTML = `<span style='color:#b91c1c;'>Error submitting task: ${initialResponse.status} ${err}</span>`;
                         resultDiv.classList.add('visible');
                         submitBtn.disabled = false;
                          // Also clear the download area on submission failure
                          downloadArea.innerHTML = '';
                      } else {
                          console.log("Initial /sendSubscribe fetch successful. Waiting for SSE updates.");
                          
                          const reader = initialResponse.body.getReader();
                          const decoder = new TextDecoder();
                          let buffer = '';

                          // Function to escape HTML characters to prevent XSS when displaying text
                          function escapeHTML(str) {
                              if (typeof str !== 'string') {
                                 console.warn("escapeHTML received non-string input:", str);
                                 return String(str);
                              }
                              return str.replace(/&/g, '&amp;')
                                        .replace(/</g, '&lt;')
                                        .replace(/>/g, '&gt;')
                                        .replace(/"/g, '&quot;')
                                        .replace(/'/g, '&#039;');
                          }

                          // Re-implement the logic from EventSource listeners
                          async function readStream() {
                              while (true) {
                                  const { done, value } = await reader.read();
                                  if (done) {
                                      console.log("Stream finished.");
                                      // Handle end of stream - task is likely completed or failed
                                      submitBtn.disabled = false; // Re-enable submit button
                                      break;
                                  }

                                  buffer += decoder.decode(value, { stream: true });
                                  
                                  // Process buffer line by line to find complete SSE messages
                                  const events = buffer.split('\\n\\n');
                                  buffer = events.pop(); // Keep the last potentially incomplete event

                                  for (const eventString of events) {
                                      if (!eventString) continue; // Skip empty strings
                                      
                                      try {
                                          // Parse SSE format (data:event: ...)
                                          let data = null;
                                          let eventType = 'message'; // Default event type
                                          const lines = eventString.split('\\n');
                                          for (const line of lines) {
                                              if (line.startsWith('data: ')) {
                                                  // Concatenate data lines
                                                  data = (data || '') + line.substring('data: '.length);
                                              } else if (line.startsWith('event: ')) {
                                                  eventType = line.substring('event: '.length);
                                              } // Ignore other lines like id, retry
                                          }

                                          if (data) {
                                              console.log(`Received event (Type: ${eventType}):`, data);
                                              
                                              // Process the event based on type
                                              if (eventType === 'task_status_update') {
                                                   try {
                                                        const update = JSON.parse(data);
                                                        // Replicate task_status_update logic from removed listener
                                                        console.log("Processing task_status_update:", update);
                                                        const statusLineId = `task-status`;
                                                        let statusLine = document.getElementById(statusLineId);
                                                        if (!statusLine) {
                                                            statusLine = document.createElement('p');
                                                            statusLine.id = statusLineId;
                                                            resultDiv.parentNode.insertBefore(statusLine, resultDiv);
                                                        }

                                                        let messageText = update.status.message && update.status.message.parts && update.status.message.parts[0] ? update.status.message.parts[0].text : '';
                                                        statusLine.innerHTML = `<b>Task Status:</b> <span style='color:#2563eb;'>${update.status.state}</span>`;
                                                        if (messageText) {
                                                            statusLine.innerHTML += ` (${escapeHTML(messageText)})`;
                                                        }

                                                        if (firstStatusUpdate) {
                                                            resultDiv.innerHTML = `<b>Task ID:</b> <span style='color:#6366f1;'>${update.id}</span><br>`;
                                                            const updatesHeader = document.createElement('p');
                                                            updatesHeader.id = `task-updates-header`;
                                                            updatesHeader.innerHTML = '<b>Updates & Artifacts:</b>';
                                                            resultDiv.appendChild(updatesHeader);
                                                            firstStatusUpdate = false;
                                                            resultDiv.classList.add('visible');
                                                        }

                                                        if (update.final) {
                                                            statusLine.innerHTML = `<b>Task Finished:</b> <span style='color:${update.status.state === 'completed' ? '#22c55e' : '#b91c1c'};'>${update.status.state.toUpperCase()}</span>`;
                                                            if (messageText) {
                                                                 statusLine.innerHTML += ` (${escapeHTML(messageText)})`;
                                                            }

                                                            if (update.status.state === 'completed' && update.metadata && update.metadata.downloadUrl) {
                                                                const downloadUrl = update.metadata.downloadUrl;
                                                                const downloadFilename = update.metadata.downloadFilename || 'download';
                                                                console.log("Download URL received:", downloadUrl);
                                                                const link = document.createElement('a');
                                                                link.href = downloadUrl;
                                                                link.textContent = `Download Result (${escapeHTML(downloadFilename)})`;
                                                                link.className = 'download-link';
                                                                link.target = '_blank';
                                                                link.download = downloadFilename;
                                                                downloadArea.innerHTML = '';
                                                                downloadArea.appendChild(link);
                                                            } else {
                                                                downloadArea.innerHTML = '';
                                                            }

                                                            if (resultDiv.innerHTML.includes("<span class='spinner'></span>")) {
                                                                resultDiv.innerHTML = resultDiv.innerHTML.replace(/<span class='spinner'><\/span>/g, \'\');
                                                            }
                                                            submitBtn.disabled = false;
                                                        }
                                                    } catch (e) {
                                                        console.error("Error parsing status update data:", e, data);
                                                        const updatesHeader = document.getElementById(`task-updates-header`);
                                                        if (updatesHeader) {
                                                            const errorDiv = document.createElement('div');
                                                            errorDiv.innerHTML = `<span style='color:#b91c1c;'>Error parsing status update data.</span>`;
                                                            resultDiv.appendChild(errorDiv);
                                                        } else {
                                                            resultDiv.innerHTML += `<br><span style='color:#b91c1c;'>Error parsing status update data.</span>`;
                                                        }
                                                        resultDiv.classList.add('visible');
                                                    }
                                              } else if (eventType === 'task_artifact_update') {
                                                   try {
                                                        const update = JSON.parse(data);
                                                        // Replicate task_artifact_update logic from removed listener
                                                        console.log("Processing task_artifact_update:", update);
                                                        let artifactHtml = `<br>Artifact: <span style='color:#6366f1;'>${escapeHTML(update.artifact.name || 'Unnamed Artifact')}</span>`;

                                                        if (update.artifact.description) {
                                                            artifactHtml += `<p>${escapeHTML(update.artifact.description)}</p>`;
                                                        }

                                                        update.artifact.parts.forEach(part => {
                                                             if (part.type === 'text' && part.text) {
                                                                 artifactHtml += `<div class="artifact-text"><p>Text Output:</p><pre>${escapeHTML(part.text)}</pre></div>`;
                                                             } else if (part.type === 'file' && part.file) {
                                                                 const filename = part.file.name || 'artifact_file';
                                                                 const fileUrl = `/api/tasks/${update.id}/artifacts/${encodeURIComponent(filename)}`;
                                                                 artifactHtml += `<div class="artifact-file"><p>File Artifact: <a href="${fileUrl}" download="${escapeHTML(filename)}">${escapeHTML(filename)}</a> (${escapeHTML(part.file.mimeType || 'unknown type')})</p></div>`;
                                                                 if (filename === 'script.py' && part.file.bytes) {
                                                                      try {
                                                                          const decodedCode = atob(part.file.bytes);
                                                                          artifactHtml += `<div class="artifact-code"><p>Code Preview:</p><pre><code class="language-python">${escapeHTML(decodedCode)}</code></pre></div>`;
                                                                      } catch (decodeError) {
                                                                          console.error("Error decoding code bytes for preview:", decodeError);
                                                                           artifactHtml += `<br><span style='color:#b91c1c;'>Error decoding code preview.</span>`;
                                                                      }
                                                                 } else if (part.file.uri) {
                                                                      console.log("File artifact with URI received:", part.file.uri);
                                                                 }
                                                            } else if (part.type === 'data' && part.data) {
                                                                 artifactHtml += `<div class="artifact-data"><p>Data:</p><pre>${escapeHTML(JSON.stringify(part.data, null, 2))}</pre></div>`;
                                                            }
                                                        });

                                                        const updatesHeader = document.getElementById(`task-updates-header`);
                                                        if (updatesHeader) {
                                                             const artifactDiv = document.createElement('div');
                                                             artifactDiv.innerHTML = artifactHtml;
                                                             resultDiv.appendChild(artifactDiv);
                                                        } else {
                                                             resultDiv.innerHTML += artifactHtml;
                                                        }
                                                         resultDiv.classList.add('visible');

                                                    } catch (e) {
                                                        console.error("Error parsing artifact update data:", e, data);
                                                        const updatesHeader = document.getElementById(`task-updates-header`);
                                                        if (updatesHeader) {
                                                            const errorDiv = document.createElement('div');
                                                            errorDiv.innerHTML = `<span style='color:#b91c1c;'>Error parsing artifact update data.</span>`;
                                                            resultDiv.appendChild(errorDiv);
                                                        } else {
                                                            resultDiv.innerHTML += `<br><span style='color:#b91c1c;'>Error parsing artifact update data.</span>`;
                                                        }
                                                        resultDiv.classList.add('visible');
                                                    }
                                              } // Add other event types here if needed
                                          }
                                      } catch (parseError) {
                                          console.error("Error parsing SSE data:", parseError, eventString);
                                          // Handle potential non-JSON data or parsing errors
                                          // Append the raw problematic event string if it's not empty
                                           if (eventString.trim() !== '') {
                                               const updatesHeader = document.getElementById(`task-updates-header`);
                                               if (updatesHeader) {
                                                    const errorDiv = document.createElement('div');
                                                    errorDiv.innerHTML = `<span style='color:#b91c1c;'>Error processing event data: ${escapeHTML(eventString.substring(0, 100))}...</span>`;
                                                     resultDiv.appendChild(errorDiv);
                                               } else {
                                                    resultDiv.innerHTML += `<br><span style='color:#b91c1c;'>Error processing event data: ${escapeHTML(eventString.substring(0, 100))}...</span>`;
                                               }
                                                resultDiv.classList.add('visible');
                                           }
                                      }
                                  }
                              } // End while
                          }

                          readStream().catch(err => {
                              console.error("Stream reading failed:", err);
                               let errorMessage = `Stream reading error: ${err}`; 
                              // Only update UI if not already in a final state
                              const statusLine = document.getElementById(`task-status`);
                              if (!statusLine || (!statusLine.innerHTML.includes('Task Finished') && !statusLine.innerHTML.includes('FAILED')) ) {
                                   resultDiv.innerHTML += `<br><span style='color:#b91c1c;'>${escapeHTML(errorMessage)}. Check console for details.</span>`;
                                   resultDiv.classList.add('visible');
                              }
                              submitBtn.disabled = false;
                              downloadArea.innerHTML = '';
                          });
                      }


                } catch (err) {
                    console.error("Fetch or SSE setup error:", err);
                    resultDiv.innerHTML = `<span style='color:#b91c1c;'>An unexpected error occurred: ${err}</span>`;
                    resultDiv.classList.add('visible');
                    submitBtn.disabled = false;
                     // Also clear the download area on unexpected error
                    downloadArea.innerHTML = '';
                }
            }
        </script>
    </body>
    </html>
    """

# --- Main execution (for running this server directly) ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8088)) # Make port configurable
    logger.info(f"Starting A2A Agent Server on http://localhost:{port}")
    print(f"Agent Config Loaded: {AGENT_CONFIG}")
    print(f"To view Agent Card: http://localhost:{port}/.well-known/agent.json")
    print(f"Access the UI at: http://localhost:{port}/") # Print UI URL
    print("Example usage with curl (after starting):")
    print("curl -X POST -H \"Content-Type: application/json\" -d '{\"message\": {\"role\": \"user\", \"parts\": [{\"type\": \"text\", \"text\": \"Generate a python script to print hello world\"}]}}' http://localhost:8088/api/tasks/sendSubscribe")
    
    # Ensure uvicorn runs the app from this script's context if __main__
    # This setup is for direct execution. For production, use a proper ASGI server like Gunicorn with Uvicorn workers.
    # reload=True is good for development, remove for production
    uvicorn.run("__main__:app", host="0.0.0.0", port=port, reload=True, log_level="info") 