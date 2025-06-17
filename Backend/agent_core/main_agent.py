# Main agent script to orchestrate the workflow
from .logging_module import LoggingModule
from .input_module import InputModule
from .instruction_processing_module import InstructionProcessingModule
from .code_generation_module import CodeGenerationModule
from .code_execution_module import CodeExecutionModule
from .output_delivery_module import OutputDeliveryModule
from .feedback_control_module import FeedbackControlModule
import os # For path operations
import configparser # For reading .ini configuration files
import json # For reading service account JSON
import logging # For logging levels
import traceback # For exception handling

CONFIG_FILE_NAME = "configuration.ini" # Define at module level for potential reuse

class MainAgent:
    def __init__(self, 
                 gemini_model_name: str, # Moved required parameter to the front
                 log_level="INFO", 
                 max_retries=2, 
                 execution_timeout=20, 
                 log_file="agent.log", # Add log_file parameter
                 service_account_json_path: str | None = None,
                 gcp_project_id: str | None = None,
                 gcp_location: str = "us-central1",
                 output_base_dir: str | None = None): # New parameter for output directory
        # 1. Initialize Logging
        self.logger_module = LoggingModule(log_file=log_file, log_level=log_level)
        self.logger = self.logger_module # Convenience
        self.logger.info("MainAgent initializing...")

        self.output_base_dir = output_base_dir # Store the output directory

        # Resolve the absolute path for the service account file if a relative path is given
        # Assumes the path might be relative to the workspace root if not absolute.
        resolved_sa_json_path = None
        if service_account_json_path:
            if os.path.isabs(service_account_json_path):
                resolved_sa_json_path = service_account_json_path
            else:
                # Assuming the script is run from workspace root or path is relative to it
                # For robustness, one might pass workspace_root as an arg to MainAgent
                resolved_sa_json_path = os.path.abspath(service_account_json_path)
                self.logger.info(f"Resolved service account path to: {resolved_sa_json_path}")

        # 2. Initialize Core Modules
        self.input_mod = InputModule(logger=self.logger_module)
        self.instruction_proc_mod = InstructionProcessingModule(logger=self.logger_module)
        self.code_gen_mod = CodeGenerationModule(
            logger=self.logger_module, 
            service_account_file=resolved_sa_json_path, 
            project_id=gcp_project_id,
            location=gcp_location,
            model_name=gemini_model_name
        )
        self.code_exec_mod = CodeExecutionModule(logger=self.logger_module, timeout_seconds=execution_timeout)
        self.feedback_ctrl_mod = FeedbackControlModule(logger=self.logger_module, max_retries=max_retries)
        self.output_delivery_mod = OutputDeliveryModule(logger=self.logger_module)
        
        log_msg_suffix = f" (Model: {gemini_model_name})"
        if not self.code_gen_mod._is_mock:
            log_msg_suffix += " (real Vertex AI calls will be attempted)"
        else:
            log_msg_suffix += " (operating in mock mode for code generation)"
        self.logger.info(f"All modules initialized. Max retries: {max_retries}, Execution timeout: {execution_timeout}s.{log_msg_suffix}")

    def run(self):
        self.logger.info("Autonomous Code Generation Agent: Run started.")
        final_agent_result = {}
        instruction_file_path = "instructions.txt" 
        self.logger.info(f"Attempting to load instructions from: {os.path.abspath(instruction_file_path)}")

        # Read input_file_paths from config if available
        input_file_paths = None
        config = configparser.ConfigParser()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path_workspace = os.path.join(os.path.dirname(script_dir), CONFIG_FILE_NAME)
        config_file_path_local = os.path.join(script_dir, CONFIG_FILE_NAME)
        actual_config_path = None
        if os.path.exists(config_file_path_workspace):
            actual_config_path = config_file_path_workspace
        elif os.path.exists(config_file_path_local):
            actual_config_path = config_file_path_local
        if actual_config_path:
            try:
                config.read(actual_config_path)
                if config.has_option('AgentSettings', 'input_file_paths'):
                    input_file_paths = config.get('AgentSettings', 'input_file_paths')
                if config.has_option('VertexAI', 'model_name'):
                    vertex_ai_model_name_from_config = config.get('VertexAI', 'model_name')
                    print(f"Read configuration from: {actual_config_path}. Using model: {vertex_ai_model_name_from_config}")
                else:
                    print(f"CRITICAL: 'model_name' not found under [VertexAI] in '{actual_config_path}'.")
                if config.has_option('VertexAI', 'service_account_json_path'):
                    gcp_service_account_file = config.get('VertexAI', 'service_account_json_path')
                # Read agent_max_retries and agent_execution_timeout from AgentSettings
                agent_max_retries_from_config = None
                agent_execution_timeout_from_config = None
                if config.has_option('AgentSettings', 'max_retries'):
                    agent_max_retries_from_config = config.getint('AgentSettings', 'max_retries')
                    self.logger.info(f"Read max_retries from config: {agent_max_retries_from_config}")
                if config.has_option('AgentSettings', 'execution_timeout'):
                    agent_execution_timeout_from_config = config.getint('AgentSettings', 'execution_timeout')
                    self.logger.info(f"Read execution_timeout from config: {agent_execution_timeout_from_config}")
            except Exception as e:
                self.logger.warning(f"Could not read input_file_paths from config: {e}")

        try:
            # 3. Get User Input from file
            user_instructions = self.input_mod.get_user_instructions(instruction_file_path)
            if not user_instructions:
                self.logger.warning(f"No instructions found in '{instruction_file_path}' or file could not be read. Exiting.")
                final_agent_result = {"status": "FAILURE_NO_INPUT", "message": f"No instructions found in '{instruction_file_path}' or file unreadable."}
                self.output_delivery_mod.deliver_output(final_agent_result)
                return final_agent_result

            file_paths = self.input_mod.get_file_paths(
                file_paths=input_file_paths
            )

            # 4. Process Instructions to Create Initial Prompt
            self.logger.info("Processing user instructions...")
            processed_input = self.instruction_proc_mod.process_instructions(user_instructions, file_paths)
            
            if processed_input.get("error"):
                self.logger.error(f"Error during instruction processing: {processed_input['error']}")
                final_agent_result = {"status": "FAILURE_INSTRUCTION_PROCESSING", "message": processed_input['error']}
                self.output_delivery_mod.deliver_output(final_agent_result)
                return final_agent_result

            current_prompt_base = processed_input["prompt"]
            # Augment the prompt with instructions for saving files to the specified output directory
            output_dir_instruction = ""
            if self.output_base_dir:
                output_dir_instruction = (
                    f"\nIMPORTANT: All output files MUST be saved to the directory: '{self.output_base_dir}'. "
                    "When creating or saving files, use `os.path.join('{self.output_base_dir}', 'your_filename.xlsx')` "
                    "or similar constructs to ensure they are placed in this specific output directory. "
                    "Do NOT save files to the current working directory or any other location." # Emphasize the restriction
                )
            current_prompt = current_prompt_base + output_dir_instruction

            current_retry_attempt = 0
            last_generated_code = None
            last_execution_result = None
            last_validation_result = None

            # --- Iterative Loop: Code Generation, Execution, Validation, Feedback ---
            while True:
                self.logger.info(f"Attempt {current_retry_attempt + 1} of {self.feedback_ctrl_mod.max_retries + 1}")

                # 5. Generate Code
                self.logger.info("Requesting code generation...")
                codegen_result = self.code_gen_mod.generate_code(current_prompt)
                last_generated_code = codegen_result.get("code")
                # Store the last validation result for this attempt to pass to feedback control
                current_attempt_validation_feedback = []
                if codegen_result.get("error") or not codegen_result.get("syntax_valid"):
                     error_msg = codegen_result.get("error", "Syntax error in generated code.")
                     current_attempt_validation_feedback.append(f"Code generation/syntax error: {error_msg}")

                # Extract required packages from the code generation result
                required_packages = codegen_result.get("required_packages", [])
                self.logger.info(f"Identified required packages: {required_packages}")

                if codegen_result.get("error") or not codegen_result.get("syntax_valid"):
                    error_msg = codegen_result.get("error", "Syntax error in generated code.")
                    self.logger.error(f"Code generation/syntax validation failed: {error_msg}")
                    
                    retry_decision = self.feedback_ctrl_mod.prepare_for_retry(
                        current_prompt, 
                        current_attempt_validation_feedback,
                        current_retry_attempt
                    )
                    if retry_decision["should_retry"]:
                        current_prompt = retry_decision["refined_prompt"]
                        current_retry_attempt = retry_decision["next_retry_attempt"]
                        continue 
                    else:
                        final_agent_result = {
                            "status": "FAILURE_CODE_GENERATION", 
                            "message": f"Failed to generate valid code after {current_retry_attempt + 1} attempt(s). Last error: {error_msg}",
                            "generated_code": last_generated_code,
                            "validation_feedback": current_attempt_validation_feedback
                        }
                        break 
                
                self.logger.info("Code generated and syntax validated successfully.")

                # 6. Execute Code
                self.logger.info("Executing generated code...")
                execution_result = self.code_exec_mod.execute_code(
                    last_generated_code,
                    required_packages=required_packages, # Pass the extracted list
                    output_dir=self.output_base_dir # Pass the output directory
                )
                last_execution_result = execution_result

                # Check if execution was successful
                if not execution_result.get("success"):
                    execution_error_feedback = [f"Code execution failed: {execution_result.get('error', 'Unknown execution error')}"]
                    if execution_result.get("stdout"):
                        execution_error_feedback.append(f"STDOUT:\n{execution_result['stdout']}")
                    if execution_result.get("stderr"):
                        execution_error_feedback.append(f"STDERR:\n{execution_result['stderr']}")
                    
                    self.logger.error(f"Code execution failed: {execution_result.get('error', 'Unknown execution error')}")
                    self.logger.error(f"Execution result details: {execution_result}")
                    
                    # NEW LOGIC: Check for critical errors that should stop retries
                    is_critical_error = False
                    if execution_result.get("exit_code") == 1:
                        error_output = execution_result.get("stderr") or execution_result.get("stdout")
                        if error_output:
                            for pattern in self.code_exec_mod.critical_error_patterns:
                                if pattern.search(error_output):
                                    self.logger.error(f"Critical error detected: '{pattern.pattern}'. Stopping retries.")
                                    is_critical_error = True
                                    break
                    
                    if is_critical_error:
                        final_agent_result = {
                            "status": "FAILURE_CRITICAL_EXECUTION", # New status for critical failures
                            "message": f"Critical Error: Code execution failed due to an unrecoverable error (e.g., file not found). Last error: {execution_result.get('error', 'Unknown critical error')}",
                            "generated_code": last_generated_code,
                            "execution_stdout": execution_result.get("stdout"),
                            "execution_stderr": execution_result.get("stderr"),
                            "validation_feedback": execution_error_feedback
                        }
                        break # Exit the loop immediately for critical errors
                    
                    retry_decision = self.feedback_ctrl_mod.prepare_for_retry(
                        current_prompt,
                        execution_error_feedback, # Pass detailed execution feedback
                        current_retry_attempt
                    )
                    
                    if retry_decision["should_retry"]:
                        current_prompt = retry_decision["refined_prompt"]
                        current_retry_attempt = retry_decision["next_retry_attempt"]
                        self.logger.info("Retrying after execution failure with refined prompt...")
                        continue # Continue the loop for retry
                    else:
                        self.logger.error("Maximum retries reached or retry not advised after execution failure. Task failed.")
                        final_agent_result = {
                            "status": "FAILURE_EXECUTION",
                            "message": f"Code execution failed after {current_retry_attempt + 1} attempt(s). Last error: {execution_result.get('error', 'Unknown execution error')}",
                            "generated_code": last_generated_code, # Include code that failed execution
                            "execution_stdout": execution_result.get("stdout"),
                            "execution_stderr": execution_result.get("stderr"),
                            "validation_feedback": execution_error_feedback # Include the detailed feedback
                        }
                        break # Exit the loop as no more retries

                # 7. Post-execution Output Processing & Final Delivery
                # Use the consolidated OutputDeliveryModule for validation and final delivery
                self.logger.info("Processing and delivering final output...")
                # Prepare a preliminary final_agent_result to be updated by the delivery module
                prelim_final_agent_result = {
                    "status": "SUCCESS", # Assume success initially, delivery module will refine
                    "message": f"Task completed successfully after {current_retry_attempt + 1} attempt(s).",
                    "generated_code": last_generated_code,
                    "execution_stdout": execution_result.get("stdout"),
                    "execution_stderr": execution_result.get("stderr"),
                    # execution_feedback will be populated by output_delivery_mod
                }

                final_agent_result = self.output_delivery_mod.process_and_deliver_output(
                    final_result=prelim_final_agent_result,
                    execution_result=last_execution_result,
                    expected_stdout=None, # If you had specific expected output for the final run, pass it here
                    test_cases=None # If you had final test cases to run, pass them here
                )

                break # Exit the loop as task is completed successfully

            # If we are here, it means execution failed, and we need to prepare for retry or final failure
            # The execution error handling already prepares the final_agent_result and breaks for critical errors.
            # For non-critical execution failures that lead to max retries, the final_agent_result would be set
            # in the `else` block of `if retry_decision["should_retry"]` above.

        except Exception as e:
            self.logger.critical(f"An unhandled critical error occurred during agent run: {e}", exc_info=True)
            final_agent_result = {
                "status": "CRITICAL_FAILURE_UNHANDLED_EXCEPTION",
                "message": f"An unhandled critical error occurred: {str(e)}",
                "error_details": traceback.format_exc(),
                "generated_code": last_generated_code, # Include last generated code if available
                "execution_stdout": last_execution_result.get("stdout") if last_execution_result else None,
                "execution_stderr": last_execution_result.get("stderr") if last_execution_result else None,
            }
        finally:
            # Ensure output is always delivered, even if an unhandled exception occurred
            if "status" not in final_agent_result: # If no status was set, it means a critical unhandled error occurred
                 # In this case, we would have already set CRITICAL_FAILURE_UNHANDLED_EXCEPTION above
                 # so this block might be redundant or for very early failures.
                 self.logger.warning("Final agent result status not set, setting to UNKNOWN_FINAL_STATE.")
                 final_agent_result["status"] = "UNKNOWN_FINAL_STATE"
                 final_agent_result["message"] = "Agent finished in an unknown state."
                 # Deliver whatever partial result we have
                 self.output_delivery_mod.process_and_deliver_output(final_agent_result, {}, None, None)
            elif final_agent_result.get("status") != "SUCCESS" and "execution_feedback" not in final_agent_result:
                # This covers cases where the loop breaks due to non-success (e.g., code gen failure, max retries)
                # and output_delivery_mod.process_and_deliver_output was NOT called yet for the final status.
                # We need to call it with whatever partial execution_result we have (if any) to get feedback.
                self.logger.info(f"Delivering final agent result for non-success status: {final_agent_result.get("status")}")
                # Pass an empty execution_result if no execution happened, or last_execution_result if it did.
                self.output_delivery_mod.process_and_deliver_output(final_agent_result, last_execution_result or {}, None, None)

            self.logger.info("Autonomous Code Generation Agent: Run finished.")
            return final_agent_result


def main():
    # Configuration for running the agent
    agent_log_level = "DEBUG"  
    agent_max_retries = 1 
    agent_execution_timeout = 20 # Increased timeout slightly for potentially slower API calls
    
    # Default configuration values
    default_log_level = "INFO"
    default_max_retries = 2
    default_execution_timeout = 20 # Consistent with MainAgent default
    default_gemini_model_name = "gemini-2.5-pro-preview-05-06" # Default model name
    default_service_account_path = None
    default_log_file = "agent.log" # Default log file

    # Read configuration from configuration.ini
    config = configparser.ConfigParser()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    config_file_path_workspace = os.path.join(workspace_root, CONFIG_FILE_NAME)
    config_file_path_local = os.path.join(script_dir, CONFIG_FILE_NAME) # Less likely location

    actual_config_path = None
    if os.path.exists(config_file_path_workspace):
        actual_config_path = config_file_path_workspace
    elif os.path.exists(config_file_path_local):
        actual_config_path = config_file_path_local


    if actual_config_path:
        print(f"Reading configuration from: {actual_config_path}")
        try:
            config.read(actual_config_path)

            if config.has_section('AgentSettings'):
                agent_max_retries = config.getint('AgentSettings', 'max_retries', fallback=default_max_retries)
                agent_execution_timeout = config.getint('AgentSettings', 'execution_timeout', fallback=default_execution_timeout)

            if config.has_section('VertexAI'):
                gemini_model_name = config.get('VertexAI', 'model_name', fallback=default_gemini_model_name)
                gcp_service_account_file = config.get('VertexAI', 'service_account_json_path', fallback=default_service_account_path)

            if config.has_section('LOG'):
                agent_log_level_str_log = config.get('LOG', 'log_level', fallback='INFO').upper()
                # Only update log_level if found in [LOG] section (override AgentSettings if both exist)
                agent_log_level = getattr(logging, agent_log_level_str_log, default_log_level)
                agent_log_file = config.get('LOG', 'log_file', fallback=default_log_file)
                agent_log_folder = config.get('LOG', 'log_folder', fallback="LOGS") # NEW

        except Exception as e:
            print(f"Error reading config file '{actual_config_path}': {e}. Using default settings.")
    else:
        print(f"Config file '{CONFIG_FILE_NAME}' not found in expected locations. Using default settings.")

    # Read project_id and location from the service account JSON file if path is provided
    if gcp_service_account_file and os.path.exists(gcp_service_account_file):
        try:
            with open(gcp_service_account_file, 'r', encoding='utf-8') as f:
                sa_data = json.load(f)
                gcp_project_id = sa_data.get('project_id')
                # Try to get location from service account JSON (custom field or fallback)
                gcp_location = sa_data.get('location', "us-central1") # Default location if not in JSON
            if not gcp_project_id:
                 print(f"Warning: 'project_id' not found in service account file: {gcp_service_account_file}")
        except Exception as e:
            print(f"Error reading project_id/location from service account file {gcp_service_account_file}: {e}")

    if gcp_project_id is None:
        print("CRITICAL: GCP project ID not found in service account file. Code generation may fail.")

    # Construct full log file path
    log_folder_path = os.path.join(workspace_root, agent_log_folder)
    os.makedirs(log_folder_path, exist_ok=True)
    full_agent_log_file_path = os.path.join(log_folder_path, agent_log_file)

    # Initialize and run the agent
    agent = MainAgent(
        gemini_model_name=gemini_model_name,
        log_file=full_agent_log_file_path, # Pass configured log file path
        log_level=agent_log_level, # Pass configured log level
        max_retries=agent_max_retries, # Pass configured max retries
        execution_timeout=agent_execution_timeout, # Pass configured execution timeout
        service_account_json_path=gcp_service_account_file, # Pass configured service account path
        gcp_project_id=gcp_project_id, # Pass extracted project ID
        gcp_location=gcp_location # Pass extracted location
    )
    agent.run()

if __name__ == "__main__":
    main() 