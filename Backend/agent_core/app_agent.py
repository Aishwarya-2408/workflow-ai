import configparser
import logging
import os
import uuid
import json
import traceback
import base64
import asyncio
import threading # Use threading for background task in sync Flask
import queue # NEW IMPORT
import re # NEW IMPORT: For regex to extract file paths from stdout
import zipfile # NEW IMPORT: For zipping multiple output files
from typing import Any, Dict, List, Literal, Optional

from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
from flask import Blueprint

# Attempt to import the original MainAgent and its dependencies
from .main_agent import MainAgent
from .logging_module import LoggingModule # For setting up a logger instance

task_store: Dict[str, Dict[str, Any]] = {}

downloadable_files: Dict[str, str] = {}

# To store paths of generated downloadable files
stream_queues: Dict[str, queue.Queue] = {} # MODIFIED: Changed to queue.Queue

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

def save_file_part(part: Dict[str, Any], task_id: str, workspace_root: str):
    """Saves a file part (either bytes or via URI) and returns the absolute path."""
    file_info = part.get('file')
    if not file_info:
        logger.error("Received a file part with no file_info.")
        return None

    if file_info.get('bytes'):
        # Handle base64 encoded content
        filename = os.path.basename(file_info.get('name', f"uploaded_bytes_{task_id}"))
        uploads_dir = os.path.join(workspace_root, "uploads")
        os.makedirs(uploads_dir, exist_ok=True)
        # Append task_id to the filename
        save_filename = f"{task_id}_{filename}"
        save_path = os.path.join(uploads_dir, save_filename)

        try:
            file_bytes = base64.b64decode(file_info['bytes'])
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            logger.info(f"Saved uploaded file from bytes to: {save_path}")
            return os.path.abspath(save_path) # Return absolute path
        except Exception as e:
            logger.error(f"Error saving uploaded file from bytes {filename}: {e}", exc_info=True)
            return None

    elif file_info.get('uri'):
        # Handle file URIs (assume relative workspace path)
        relative_path = file_info['uri']
        # Basic sanitization against directory traversal
        if ".." in relative_path or relative_path.startswith('/'):
             logger.error(f"Potential directory traversal attempt with URI: {relative_path}")
             return None

        resolved_path = os.path.join(workspace_root, relative_path)
        resolved_path = os.path.abspath(resolved_path)

        # Ensure the resolved path is within the workspace_root
        if not resolved_path.startswith(os.path.abspath(workspace_root)):
            logger.error(f"Resolved URI path is outside workspace root: {resolved_path}")
            return None

        if not os.path.exists(resolved_path) or not os.path.isfile(resolved_path):
            logger.error(f"File referenced by URI not found or is not a file: {resolved_path}")
            return None

        logger.info(f"Using file from URI for task {task_id}: {resolved_path}")
        return resolved_path

    else:
        logger.warning("File part has neither bytes nor URI.")
        return None

def load_agent_config():
    """Loads configuration from configuration.ini."""
    config = configparser.ConfigParser()
    script_dir = os.path.dirname(os.path.abspath(__file__)) # agent_core
    workspace_root = os.path.dirname(script_dir) # Parent of agent_core

    config_file_path_workspace = os.path.join(workspace_root, CONFIG_FILE_NAME)
    config_file_path_local = os.path.join(script_dir, CONFIG_FILE_NAME)

    actual_config_path = None
    if os.path.exists(config_file_path_workspace):
        actual_config_path = config_file_path_workspace
    elif os.path.exists(config_file_path_local):
        actual_config_path = config_file_path_local

    parsed_config = {
        "gemini_model_name": "gemini-2.5-pro-preview-05-06",
        "gcp_service_account_file": None,
        "agent_log_level": logging.INFO,
        "agent_max_retries": 2,
        "agent_execution_timeout": 20,
        "agent_log_file": "agent.log",
        "agent_log_folder": "LOGS"
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
            if config.has_section('LOG'):
                log_level_str = config.get('LOG', 'log_level', fallback="INFO").upper()
                parsed_config["agent_log_level"] = getattr(logging, log_level_str, logging.INFO)
                parsed_config["agent_log_file"] = config.get('LOG', 'log_file', fallback=parsed_config["agent_log_file"])
                parsed_config["agent_log_folder"] = config.get('LOG', 'log_folder', fallback="LOGS")
            print(f"Loaded A2A agent configuration from: {actual_config_path}")
        except Exception as e:
            print(f"Error reading A2A agent config '{actual_config_path}': {e}. Using defaults.")
    else:
        print(f"A2A agent config file '{CONFIG_FILE_NAME}' not found in expected locations. Using defaults.")
    return parsed_config

AGENT_CONFIG = load_agent_config()

# Initialize logger
try:
    workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Getting workspace root
    log_folder_path = os.path.join(workspace_root, AGENT_CONFIG["agent_log_folder"])
    # os.makedirs(log_folder_path, exist_ok=True) # Ensure the log folder exists - Now handled by LoggingModule
    # full_log_file_path = os.path.join(log_folder_path, AGENT_CONFIG["agent_log_file"])

    lm = LoggingModule(log_file=AGENT_CONFIG["agent_log_file"], log_level=AGENT_CONFIG["agent_log_level"], log_folder=log_folder_path)
    logger = lm.get_logger() if hasattr(lm, 'get_logger') else lm.logger
except Exception as e:
     print(f"Error initializing LoggingModule: {e}. Using basic logging.")
     logging.basicConfig(level=AGENT_CONFIG["agent_log_level"], filename=None) # Explicitly set filename to None
     logger = logging.getLogger(__name__)

# Create blueprint for file processing API
def create_file_processor_blueprint():
    file_processor_api = Blueprint('file_processor_api', __name__, url_prefix='/api/v1/file-preprocessing')

    # Helper function to run the async main agent in a sync context
    async def run_main_agent_for_a2a(task: Dict[str, Any], instructions_text: str, input_file_paths: List[str], event_sink_q: Optional[queue.Queue]): # MODIFIED: Changed stream_q to event_sink_q (synchronous queue)
        task_id = task['id'] # Get task_id from the passed task object

        logger.info(f"Task {task_id}: Initializing MainAgent for A2A processing.")
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        original_main_agent_instruction_file = "instructions.txt"
        original_main_agent_instruction_path = os.path.join(workspace_root, original_main_agent_instruction_file)

        # Create a unique output directory for this task
        task_output_dir = os.path.join(workspace_root, DOWNLOADS_DIR, task_id)
        os.makedirs(task_output_dir, exist_ok=True)
        logger.info(f"Task {task_id}: Created task-specific output directory: {task_output_dir}")

        # Get config values
        service_account_path = AGENT_CONFIG["gcp_service_account_file"]
        agent_execution_timeout = AGENT_CONFIG["agent_execution_timeout"]
        agent_max_retries = AGENT_CONFIG["agent_max_retries"]
        gcp_project_id = None
        gcp_location = None

        if not service_account_path or str(service_account_path).strip().lower() in ("", "none"):
            logger.error(f"GCP service account file is not set in the config file. Please set 'service_account_json_path' under [VertexAI] in {CONFIG_FILE_NAME}.")
            current_status = {"state": "failed", "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [{"type": "text", "text": "GCP service account file is not set in the config file. Please set 'service_account_json_path' under [VertexAI] in configuration.ini."}]}}
            task['status'] = current_status
            if event_sink_q: event_sink_q.put({"id": task_id, "status": current_status, "final": True, "event_type": "task_status_update"}) # MODIFIED: put to synchronous queue
            return

        try:
            with open(service_account_path, 'r', encoding='utf-8') as f:
                sa_data = json.load(f)
                gcp_project_id = sa_data.get('project_id')
                gcp_location = sa_data.get('location')
            if not gcp_project_id:
                logger.error(f"'project_id' not found in service account file: {service_account_path}")
                current_status = {"state": "failed", "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [{"type": "text", "text": f"'project_id' not found in service account file: {service_account_path}"}]}}
                task['status'] = current_status
                if event_sink_q: event_sink_q.put({"id": task_id, "status": current_status, "final": True, "event_type": "task_status_update"}) # MODIFIED: put to synchronous queue
                return
            if not gcp_location:
                gcp_location = "us-central1"
        except Exception as e:
            logger.error(f"Could not read project_id/location from service account file: {e}")
            current_status = {"state": "failed", "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [{"type": "text", "text": f"Could not read project_id/location from service account file: {e}"}]}}
            task['status'] = current_status
            if event_sink_q: event_sink_q.put({"id": task_id, "status": current_status, "final": True, "event_type": "task_status_update"}) # MODIFIED: put to synchronous queue
            return

        # Progress Update: After config and service account validation
        if event_sink_q: event_sink_q.put({"id": task_id, "progress": 20, "message": "Input module processing complete.", "event_type": "task_progress_update"})

        main_agent_instance = MainAgent(
            gemini_model_name=AGENT_CONFIG["gemini_model_name"],
            log_level=AGENT_CONFIG["agent_log_level"],
            max_retries=agent_max_retries,
            execution_timeout=agent_execution_timeout,
            service_account_json_path=service_account_path,
            gcp_project_id=gcp_project_id,
            gcp_location=gcp_location,
            output_base_dir=task_output_dir # Pass the task-specific output directory
        )

        current_status = {"state": "submitted", "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [{"type": "text", "text": "Task submitted: Initializing agent."}]}}
        task['status'] = current_status
        if event_sink_q: event_sink_q.put({"id": task_id, "status": current_status, "event_type": "task_status_update"}) # MODIFIED: put to synchronous queue

        logger.info(f"Task {task_id}: Writing provided instructions to '{original_main_agent_instruction_path}' for MainAgent.")
        try:
            with open(original_main_agent_instruction_path, "w", encoding="utf-8") as f:
                f.write(instructions_text)
        except Exception as e:
            logger.error(f"Task {task_id}: Failed to write temporary instruction file: {e}")
            current_status = {"state": "failed", "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [{"type": "text", "text": f"Internal error: could not prepare instructions: {e}"}]}}
            task['status'] = current_status
            if event_sink_q: event_sink_q.put({"id": task_id, "status": current_status, "final": True, "event_type": "task_status_update"}) # MODIFIED: put to synchronous queue
            return

        # Progress Update: After instruction processing
        if event_sink_q: event_sink_q.put({"id": task_id, "progress": 40, "message": "Instruction processing complete.", "event_type": "task_progress_update"})

        try:
            logger.info(f"Task {task_id}: Running MainAgent.run() for actual processing.")
            # Call the real agent and get the result
            result = await asyncio.to_thread(main_agent_instance.run)

            # Progress Update: After code generation/execution (if successful)
            if result.get("status") == "SUCCESS":
                if event_sink_q: event_sink_q.put({"id": task_id, "progress": 80, "message": "Code generation and execution complete.", "event_type": "task_progress_update"})

            # Log the full result for debugging
            logger.info(f"Task {task_id}: MainAgent.run() returned result: {json.dumps(result, indent=2)}")

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
            
            # If the state is completed, and we have execution feedback, incorporate that into the final message.
            if state == "completed" and result.get("execution_feedback"):
                message_text += "\nExecution Feedback: " + "\n".join(result["execution_feedback"])

            current_status = {"state": state, "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [{"type": "text", "text": message_text}]}}
            task['status'] = current_status
            if event_sink_q: event_sink_q.put({"id": task_id, "status": current_status, "event_type": "task_status_update"}) # MODIFIED: put to synchronous queue

            # Build artifact if code was generated
            artifacts = []
            download_url = None
            download_filename = None

            # Prioritize saving execution stdout if available and task was successful
            if state == "completed" and result.get("execution_stdout"):
                # NEW LOGIC: Extract Excel file paths from stdout
                excel_file_paths = re.findall(r"Successfully processed '.*?\.xlsx' and saved output to '(.*?\.xlsx)'", result["execution_stdout"])

                if excel_file_paths:
                    downloads_dir_abs = os.path.join(workspace_root, DOWNLOADS_DIR)
                    os.makedirs(downloads_dir_abs, exist_ok=True)

                    if len(excel_file_paths) == 1:
                        # If only one Excel file, make it directly downloadable
                        output_path = excel_file_paths[0] # Use the path directly
                        output_filename = os.path.basename(output_path)
                        # Ensure the output_path is absolute and within DOWNLOADS_DIR for security
                        resolved_output_path = os.path.abspath(output_path)
                        # The output path should be in task_output_dir, not downloads_dir_abs directly
                        expected_prefix = os.path.abspath(os.path.join(downloads_dir_abs, task_id))
                        if not resolved_output_path.startswith(expected_prefix):
                            logger.warning(f"Task {task_id}: Generated Excel file path '{output_path}' is outside expected task-specific downloads directory ('{expected_prefix}'). Skipping direct download.")
                            output_path = None # Invalidate if not in expected dir

                        if output_path:
                            downloadable_files[task_id] = resolved_output_path # Store the absolute path
                            download_url = f"/api/v1/file-preprocessing/tasks/download/{task_id}"
                            logger.info(f"Task {task_id}: Saved single Excel output to {resolved_output_path}. URL: {download_url}")
                            if event_sink_q: event_sink_q.put({"id": task_id, "progress": 90, "message": "Excel file generation and download setup complete.", "event_type": "task_progress_update"})
                    else:
                        # If multiple Excel files, create a zip file
                        zip_filename = f"{task_id}_workflow_outputs.zip"
                        zip_filepath = os.path.join(downloads_dir_abs, zip_filename)

                        try:
                            with zipfile.ZipFile(zip_filepath, 'w') as zipf:
                                for file_path in excel_file_paths:
                                    resolved_file_path = os.path.abspath(file_path)
                                    # Ensure the file being zipped is from the task's output directory
                                    expected_prefix = os.path.abspath(os.path.join(downloads_dir_abs, task_id))
                                    if resolved_file_path.startswith(expected_prefix):
                                        zipf.write(resolved_file_path, os.path.relpath(resolved_file_path, expected_prefix)) # Save with relative path in zip
                                        logger.info(f"Task {task_id}: Added {os.path.basename(resolved_file_path)} to zip.")
                                    else:
                                        logger.warning(f"Task {task_id}: Skipping zipping file '{file_path}' as it is outside expected task-specific downloads directory ('{expected_prefix}').")

                            downloadable_files[task_id] = zip_filepath
                            download_url = f"/api/v1/file-preprocessing/tasks/download/{task_id}"
                            output_filename = zip_filename
                            logger.info(f"Task {task_id}: Zipped multiple Excel outputs to {zip_filepath}. URL: {download_url}")
                            if event_sink_q: event_sink_q.put({"id": task_id, "progress": 90, "message": "Zipped Excel files generation and download setup complete.", "event_type": "task_progress_update"})

                        except Exception as e:
                            logger.error(f"Task {task_id}: Failed to create zip file for download: {e}", exc_info=True)
                            download_url = None
                            output_filename = None
                else:
                    logger.info(f"Task {task_id}: No Excel files found in stdout to make downloadable.")

            # Prepare artifact parts
            artifact_parts = []
            artifact_description = "Output from the agent"

            # Include execution stdout/stderr as text parts
            if result.get("execution_stdout"):
                artifact_parts.append({"type": "text", "text": f"Execution STDOUT:\n{result['execution_stdout']}"})
                artifact_description += ", including execution output"
            if result.get("execution_stderr"):
                artifact_parts.append({"type": "text", "text": f"Execution STDERR:\n{result['execution_stderr']}"})
                artifact_description += " and errors"

            # Include generated code as a text part if available
            if result.get("generated_code"):
                artifact_parts.append({"type": "text", "text": f"Generated Code:\n```python\n{result['generated_code']}\n```"})
                artifact_description += ", including generated code"

            # Include execution feedback as a text part
            if result.get("execution_feedback"):
                artifact_parts.append({"type": "text", "text": f"Execution Feedback:\n{chr(10).join(result['execution_feedback'])}"})
                artifact_description += " and execution feedback"

            # Add a part indicating the downloadable file if successful
            if download_url and output_filename:
                artifact_parts.append({"type": "text", "text": f"\nDownloadable output available: {output_filename}"})

            # Create the artifact
            if artifact_parts:
                artifact = {
                    "name": "task_results", # Generic name
                    "description": artifact_description,
                    "parts": artifact_parts
                }
                # task_store[task_id]['artifacts'] = artifacts # This would overwrite existing
                if 'artifacts' not in task or not isinstance(task['artifacts'], list):
                    task['artifacts'] = []
                task['artifacts'].append(artifact)
                if event_sink_q:
                    event_sink_q.put({"id": task_id, "artifact": artifact, "event_type": "task_artifact_update"}) # MODIFIED: put to synchronous queue

            # Send final status update
            final_metadata = {"downloadUrl": download_url, "downloadFilename": output_filename} if download_url else {}
            final_status_update = {"id": task_id, "status": current_status, "final": True, "metadata": final_metadata, "event_type": "task_status_update", "progress": 100}
            if event_sink_q:
                event_sink_q.put(final_status_update) # MODIFIED: put to synchronous queue
                logger.info(f"Task {task_id}: Successfully put final_status_update to queue.") # NEW LOG

            logger.info(f"Task {task_id}: MainAgent processing completed with state: {state}. Download URL included: {bool(download_url)}")

        except Exception as e:
            logger.error(f"Task {task_id}: Error during MainAgent execution: {e}", exc_info=True)
            error_message_part = {"type": "text", "text": f"An unexpected error occurred during agent execution: {str(e)}!"}
            current_status = {"state": "failed", "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [error_message_part]}}
            task['status'] = current_status
            if event_sink_q: event_sink_q.put({"id": task_id, "status": current_status, "final": True, "event_type": "task_status_update", "progress": 100}) # MODIFIED: added progress: 100
        finally:
            if os.path.exists(original_main_agent_instruction_path):
                 pass

            uploads_dir_abs = os.path.join(workspace_root, "uploads")
            logger.info(f"Task {task_id}: Cleaning up {len(input_file_paths)} input files from uploads.")
            for file_path in input_file_paths:
                resolved_file_path = os.path.abspath(file_path)
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

    def _run_async_task_in_thread(task: Dict[str, Any], instructions_text: str, input_file_paths: List[str], sync_stream_q: Optional[queue.Queue]): # MODIFIED: Changed signature to accept sync_stream_q
        """Helper to run an async function in a new event loop within a thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_main_agent_for_a2a(task, instructions_text, input_file_paths, sync_stream_q)) # MODIFIED: Pass sync_stream_q
        except Exception as e:
            logger.error(f"Task {task['id']}: Error in _run_async_task_in_thread: {e}", exc_info=True)
            task['status']['state'] = "failed"
            task['status']['timestamp'] = get_iso_timestamp()
            task['status']['message'] = {"role": "agent", "parts": [{"type": "text", "text": f"Task failed in background thread: {str(e)}"}]}
            task['error'] = str(e)
            if sync_stream_q: # MODIFIED: Signal failure to client through sync queue
                sync_stream_q.put({"id": task['id'], "status": task['status'], "final": True, "event_type": "task_status_update"})
        finally:
            loop.close()
            # Always signal end of stream to the generator after the background task completes/fails
            if sync_stream_q: # Only attempt if the queue was actually provided (i.e., for streaming tasks)
                try:
                    sync_stream_q.put(None) # Signal end of stream for synchronous generator
                    logger.info(f"Task {task['id']}: Put None to sync queue in finally block.") # NEW LOG
                except Exception as e_put:
                    logger.warning(f"Failed to put None to sync queue in finally block: {e_put}") # NEW LOG

    @file_processor_api.route('/health', methods=['GET', 'HEAD'])
    def health_check():
        logger.info("File processing workflow health check received.")
        return jsonify({'status': 'healthy', 'service': 'file-processing-workflow'}), 200

    @file_processor_api.route("/upload", methods=['POST'])
    def file_processor_upload_file():
        """Accepts a file upload specific to the file processing workflow, saves it, and returns a URI reference."""
        try:
            workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # Use a subdirectory specific to file processing uploads if needed, or the generic one
            temp_uploads_dir = os.path.join(workspace_root, "uploads", "file_processing_temp") # Using a slightly different temp dir name
            os.makedirs(temp_uploads_dir, exist_ok=True)

            if 'file' not in request.files:
                logger.error("File Processor Upload: No file part in the request")
                return jsonify({'detail': 'No file part in the request'}), 400

            file = request.files['file']

            if file.filename == '':
                logger.error("File Processor Upload: No selected file")
                return jsonify({'detail': 'No selected file'}), 400

            # Generate a unique filename
            unique_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            save_path = os.path.join(temp_uploads_dir, unique_filename)

            # Save the file
            file.save(save_path)

            # Create a URI reference relative to the workspace root
            # The path needs to be understood by the MainAgent if it loads files from URIs
            # Let's keep it relative to workspace root, but reflect the new subdirectory
            relative_uri = os.path.relpath(save_path, workspace_root).replace('\\', '/')

            logger.info(f"File Processor Upload: file saved to {save_path}. URI: {relative_uri}")

            return jsonify({"uri": relative_uri})

        except Exception as e:
            logger.error(f"File Processor Upload: Error during file upload: {e}", exc_info=True)
            # Return JSON error response
            return jsonify({'detail': f"Failed to upload file: {e}"}), 500

    @file_processor_api.route("/tasks/send", methods=['POST'])
    def file_processor_tasks_send():
        """Receives a task for the file processing workflow, initiates processing, and returns the initial task status."""
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        params = request.json
        if not params:
            return jsonify({'detail': 'Invalid JSON payload'}), 400

        task_id = params.get('id') or generate_task_id()
        if task_id in task_store:
            return jsonify({'detail': 'Task ID already exists. Use tasks/get or a unique ID.'}), 409

        message = params.get('message')
        if not message or not isinstance(message, dict):
            return jsonify({'detail': 'Invalid message format'}), 400

        instruction_text = ""
        file_paths_for_agent = []

        parts = message.get('parts', [])
        if not isinstance(parts, list):
            return jsonify({'detail': 'Invalid message parts format'}), 400

        for part in parts:
            if not isinstance(part, dict): continue

            if part.get('type') == "text" and part.get('text'):
                instruction_text += part['text'] + "\n"
            elif part.get('type') == "file" and part.get('file'):
                saved_path = save_file_part(part, task_id, workspace_root)
                if saved_path:
                    file_paths_for_agent.append(saved_path)

        update_input_file_paths_in_config(file_paths_for_agent, workspace_root)

        if not instruction_text and not file_paths_for_agent:
            return jsonify({'detail': "No text instructions or file inputs provided."}), 400

        logger.info(f"File Processor tasks/send: new task ID {task_id}. Instructions: {instruction_text[:100]}... Files: {file_paths_for_agent}")

        initial_status = {"state": "submitted", "timestamp": get_iso_timestamp(), "message": message}
        task = {"id": task_id, "sessionId": params.get('sessionId'), "status": initial_status, "metadata": params.get('metadata')}
        task_store[task_id] = task

        # Run the async task in a separate thread, passing None for the streaming queue
        thread = threading.Thread(target=_run_async_task_in_thread, args=(task, instruction_text.strip(), file_paths_for_agent, None))
        thread.start()

        return jsonify(task)

    @file_processor_api.route("/tasks/sendSubscribe", methods=['POST'])
    def file_processor_tasks_send_subscribe(): # MODIFIED: Changed from async def to def (synchronous)
        """Receives a task for the file processing workflow, initiates processing, and returns streaming updates."""
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        params = request.get_json()
        if not params:
            return jsonify({'detail': 'Invalid JSON payload'}), 400

        task_id = params.get('id') or generate_task_id()
        if task_id in task_store:
            return jsonify({'detail': 'Task ID already exists or is actively streaming.'}), 409

        message = params.get('message')
        if not message or not isinstance(message, dict):
            return jsonify({'detail': 'Invalid message format'}), 400

        instruction_text = ""
        file_paths_for_agent = []

        parts = message.get('parts', [])
        if not isinstance(parts, list):
            return jsonify({'detail': 'Invalid message parts format'}), 400

        for part in parts:
            if not isinstance(part, dict): continue

            if part.get('type') == "text" and part.get('text'):
                instruction_text += part['text'] + "\n"
            elif part.get('type') == "file" and part.get('file'):
                saved_path = save_file_part(part, task_id, workspace_root)
                if saved_path:
                    file_paths_for_agent.append(saved_path)

        update_input_file_paths_in_config(file_paths_for_agent, workspace_root)

        if not instruction_text and not file_paths_for_agent:
            return jsonify({'detail': "No text instructions or file inputs provided."}), 400

        logger.info(f"File Processor tasks/sendSubscribe (streaming): new task ID {task_id}. Instructions: {instruction_text[:100]}... Files: {file_paths_for_agent}")

        initial_status = {"state": "submitted", "timestamp": get_iso_timestamp(), "message": message}
        task = {"id": task_id, "sessionId": params.get('sessionId'), "status": initial_status, "metadata": params.get('metadata')}
        task_store[task_id] = task

        # Create a synchronous queue for streaming events
        sync_stream_q = queue.Queue() # MODIFIED: Use synchronous queue
        stream_queues[task_id] = sync_stream_q

        # Start the async MainAgent task in a separate thread, passing the synchronous queue
        thread = threading.Thread(target=_run_async_task_in_thread, args=(task, instruction_text.strip(), file_paths_for_agent, sync_stream_q)) # MODIFIED: Pass sync_stream_q
        thread.start()

        def event_generator(): # MODIFIED: This is now a synchronous generator
            try:
                while True:
                    # Get from the synchronous queue with a timeout
                    try:
                        update_event = sync_stream_q.get(timeout=1.0) # MODIFIED: Synchronous get with timeout
                        logger.debug(f"Task {task_id}: Generator received event: {update_event}") # NEW LOG

                        if update_event is None: # Keep this to handle the explicit None from the producer
                            logger.info(f"Task {task_id}: Received explicit None signal, closing stream.")
                            break

                        event_type = update_event.pop("event_type", "message")
                        json_data = json.dumps(update_event)
                        yield f"event: {event_type}\ndata: {json_data}\n\n"

                        if update_event.get("final"):
                            logger.info(f"Task {task_id}: Sent final status update, closing stream.")
                            break
                    except queue.Empty: # This exception occurs when the timeout is reached
                        logger.debug(f"Task {task_id}: Queue empty, sending keep-alive.") # NEW LOG
                        yield ": keep-alive\n\n" # Send a keep-alive comment
                        continue # Continue the loop after sending keep-alive
            except Exception as e_stream:
                logger.error(f"Error in stream for task {task_id}: {e_stream}", exc_info=True)
                error_message_part = {"type": "text", "text": f"Streaming error: {e_stream}"}
                error_status = {"state": "failed", "timestamp": get_iso_timestamp(), "message": {"role": "agent", "parts": [error_message_part]}}
                json_data = json.dumps({"id": task_id, "status": error_status, "final": True})
                yield f"event: task_status_update\ndata: {json_data}\n\n"
            finally:
                if task_id in stream_queues:
                    del stream_queues[task_id]
                logger.info(f"Task {task_id} stream generator finished.")

        return Response(event_generator(), mimetype="text/event-stream")

    @file_processor_api.route("/tasks/download/<task_id>", methods=['GET'])
    def file_processor_download_task_output_file(task_id: str):
        """Serves the generated output file for a given task ID within the file processing workflow."""
        file_path = downloadable_files.get(task_id)

        if not file_path:
            logger.warning(f"File Processor Download: Download requested for task {task_id}, but no downloadable file found.")
            return jsonify({"detail": f"No downloadable file found for task ID '{task_id}'."}), 404

        # Security check: Ensure the file path is within the designated downloads directory
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        downloads_dir_abs = os.path.join(workspace_root, DOWNLOADS_DIR)
        resolved_file_path = os.path.abspath(file_path)

        if not resolved_file_path.startswith(downloads_dir_abs):
            logger.error(f"File Processor Download: Attempted download path traversal: {resolved_file_path} is outside {downloads_dir_abs}")
            return jsonify({"detail": "Access denied."}), 403 # Forbidden

        if not os.path.exists(resolved_file_path) or not os.path.isfile(resolved_file_path):
            logger.error(f"File Processor Download: Download requested for task {task_id}, file not found at expected path: {resolved_file_path}")
            return jsonify({"detail": f"Downloadable file not found for task ID '{task_id}'."}), 404

        logger.info(f"File Processor Download: Serving downloadable file for task {task_id} from: {resolved_file_path}")

        # Determine mime type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(resolved_file_path)
        if not mime_type:
            mime_type = 'application/octet-stream'

        # Try to get the original filename if stored, otherwise use the saved filename
        # In this specific case (task output), the saved filename is the primary name.
        original_filename = os.path.basename(resolved_file_path)

        # Use send_from_directory to serve the file safely
        download_dir = os.path.dirname(resolved_file_path)
        download_filename_base = os.path.basename(resolved_file_path)

        try:
            return send_from_directory(
                download_dir,
                download_filename_base,
                mimetype=mime_type,
                as_attachment=True, # Suggest download
                download_name=original_filename # Use the friendly filename for download
            )
        except Exception as e:
            logger.error(f"File Processor Download: Error serving file {resolved_file_path}: {e}", exc_info=True)
            return jsonify({"detail": "Error serving file."}), 500

    @file_processor_api.route("/tasks/<task_id>/artifacts/<filename>", methods=['GET'])
    def file_processor_get_artifact_file(task_id: str, filename: str):
        """Serves a specific artifact file for a given task within the file processing workflow."""
        task = task_store.get(task_id)
        if not task:
            return jsonify({"detail": f"Task with ID '{task_id}' not found."}), 404

        # Basic sanitization to prevent directory traversal
        sanitized_filename = secure_filename(filename)

        # Reconstruct the expected save path based on save_file_part logic
        # Artifact files (uploaded inputs) are saved in 'uploads'
        workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uploads_dir_abs = os.path.join(workspace_root, "uploads")
        # Assuming files saved via save_file_part are named {task_id}_{original_name}
        expected_path = os.path.join(uploads_dir_abs, f"{task_id}_{sanitized_filename}")

        resolved_path = os.path.abspath(expected_path)

        # Ensure resolved path is within the uploads directory (redundant with send_from_directory but good practice)
        if not resolved_path.startswith(uploads_dir_abs):
            logger.error(f"File Processor Artifact: Download path outside uploads directory: {resolved_path}")
            return jsonify({"detail": "Access denied."}), 403 # Forbidden

        if not os.path.exists(resolved_path) or not os.path.isfile(resolved_path):
            logger.error(f"File Processor Artifact: Artifact requested for task {task_id}, file not found at expected path: {resolved_path}")
            return jsonify({"detail": f"Artifact file '{filename}' not found for task '{task_id}'."}), 404

        logger.info(f"File Processor Artifact: Serving artifact file for task {task_id}: {filename} from {resolved_path}")

        # Determine mime type - could try to guess or use the one stored in the artifact if available
        import mimetypes
        mime_type, _ = mimetypes.guess_type(resolved_path)
        if not mime_type:
            # Attempt to find mime type in stored task artifact data if possible
            stored_mime_type = None
            if task.get('artifacts'):
                for artifact in task['artifacts']:
                    if artifact.get('parts'):
                        for part in artifact['parts']:
                            if part.get('type') == 'file' and part.get('file') and part['file'].get('name') == filename:
                                stored_mime_type = part['file'].get('mimeType')
                                break
                        if stored_mime_type: break
            mime_type = stored_mime_type or 'application/octet-stream'

        # Use send_from_directory to serve the file safely
        artifact_dir = os.path.dirname(resolved_path)
        artifact_filename_base = os.path.basename(resolved_path)

        try:
            return send_from_directory(
                artifact_dir,
                artifact_filename_base,
                mimetype=mime_type,
                as_attachment=True, # Suggest download
                download_name=sanitized_filename # Use the friendly filename for download
            )
        except Exception as e:
            logger.error(f"File Processor Artifact: Error serving artifact file {resolved_path}: {e}", exc_info=True)
            return jsonify({"detail": "Error serving artifact file."}), 500

    @file_processor_api.route("/tasks/get", methods=['POST'])
    def file_processor_tasks_get():
        """Retrieves the current state of a task by ID within the file processing workflow."""
        params = request.json
        if not params or 'id' not in params:
            return jsonify({'detail': 'Task ID not provided in the request'}), 400

        task_id = params['id']
        task = task_store.get(task_id)

        if not task:
            return jsonify({"detail": f"Task with ID '{task_id}' not found."}), 404

        # TODO: Implement historyLength if needed
        logger.info(f"File Processor tasks/get: Received tasks/get for task ID {task_id}. Current state: {task['status']['state']}")

        # Return the full task object from the store
        return jsonify(task)

    @file_processor_api.route("/tasks/cancel", methods=['POST'])
    def file_processor_tasks_cancel():
        """Requests cancellation of a running task within the file processing workflow."""
        params = request.json
        if not params or 'id' not in params:
            return jsonify({'detail': 'Task ID not provided in the request'}), 400

        task_id = params['id']
        task = task_store.get(task_id)

        if not task:
            return jsonify({"detail": f"Task with ID '{task_id}' not found."}), 404

        logger.info(f"File Processor tasks/cancel: Received tasks/cancel for task {task_id}.")

        # Basic cancellation: mark as canceled if not in a final state.
        # This does NOT actually stop the background thread running the agent.
        # Implementing true cancellation would require signaling mechanisms (e.g., events, flags checked by MainAgent).
        if task['status']['state'] not in ["completed", "failed", "canceled", "unknown"]:
            task['status']['state'] = "canceled"
            task['status']['timestamp'] = get_iso_timestamp()
            task['status']['message'] = {"role": "agent", "parts": [{"type": "text", "text": "Task cancellation requested and marked."}]}
            logger.info(f"Task {task_id} marked as canceled.")

            # If there's an active stream, send a final cancel event
            if task_id in stream_queues:
                sync_stream_q = stream_queues[task_id]
                try:
                    # Signal cancellation to the client via the queue
                    cancel_event = {"id": task_id, "status": task['status'], "final": True, "event_type": "task_status_update"}
                    sync_stream_q.put(cancel_event)
                except Exception as e:
                    logger.warning(f"Failed to put cancellation event to sync queue for task {task_id}: {e}")

        else:
            logger.warning(f"Task {task_id} is already in a final state ({task['status']['state']}), cannot cancel.")

        # Return the updated task object
        return jsonify(task)

    # Move the error handler inside the blueprint function
    @file_processor_api.errorhandler(Exception)
    def handle_file_processor_error(e):
        logger.error(f"Unhandled exception in file_processor_api: {e}", exc_info=True)
        return jsonify({
            "detail": "An internal server error occurred while processing your request.",
            "error": str(e)
        }), 500

    return file_processor_api # Return the configured blueprint 