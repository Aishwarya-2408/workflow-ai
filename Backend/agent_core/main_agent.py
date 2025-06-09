# Main agent script to orchestrate the workflow
from .logging_module import LoggingModule
from .input_module import InputModule
from .instruction_processing_module import InstructionProcessingModule
from .code_generation_module import CodeGenerationModule
from .code_execution_module import CodeExecutionModule
from .output_validation_module import OutputValidationModule
from .feedback_control_module import FeedbackControlModule
from .output_delivery_module import OutputDeliveryModule
import os # For path operations
import configparser # For reading .ini configuration files
import json # For reading service account JSON

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
                 gcp_location: str = "us-central1"):
        # 1. Initialize Logging
        self.logger_module = LoggingModule(log_file=log_file, log_level=log_level)
        self.logger = self.logger_module # Convenience
        self.logger.info("MainAgent initializing...")

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
        self.output_val_mod = OutputValidationModule(logger=self.logger_module)
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

            current_prompt = processed_input["prompt"]
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
                    required_packages=required_packages # Pass the extracted list
                )
                last_execution_result = execution_result

                # Check if execution was successful
                if not execution_result.get("success"):
                    self.logger.error(f"Code execution failed: {execution_result.get('error', 'Unknown execution error')}")
                    final_agent_result = {
                        "status": "FAILURE_EXECUTION", 
                        "message": f"Code execution failed after attempt {current_retry_attempt + 1}. Error: {execution_result.get('error', 'Unknown execution error')}",
                        "generated_code": last_generated_code, # Include code that failed execution
                        "execution_stdout": execution_result.get("stdout"),
                        "execution_stderr": execution_result.get("stderr"),
                        "validation_feedback": ["Execution failed, validation skipped."] # Indicate validation was skipped
                    }
                    break # Exit the loop on execution failure

                # 7. Validate Output
                self.logger.info("Validating execution output...")
                validation_result = self.output_val_mod.validate_output(
                    execution_result=execution_result,
                    generated_code=last_generated_code,
                    expected_stdout=None, 
                    test_cases=None 
                )
                # current_attempt_validation_feedback = validation_result["feedback"] # Overwrite with actual validation feedback

                if validation_result["passed"]:
                    self.logger.info("Validation successful! Task completed.")
                    final_agent_result = {
                        "status": "SUCCESS",
                        "message": f"Task completed successfully after {current_retry_attempt + 1} attempt(s).",
                        "generated_code": last_generated_code,
                        "execution_stdout": execution_result.get("stdout"),
                        "execution_stderr": execution_result.get("stderr"),
                        "validation_feedback": validation_result["feedback"]
                    }
                    break 
                else:
                    self.logger.warning("Validation failed. Preparing for potential retry.")
                    retry_decision = self.feedback_ctrl_mod.prepare_for_retry(
                        current_prompt, 
                        validation_result["feedback"], # Use actual validation feedback here
                        current_retry_attempt
                    )
                    if retry_decision["should_retry"]:
                        current_prompt = retry_decision["refined_prompt"]
                        current_retry_attempt = retry_decision["next_retry_attempt"]
                        self.logger.info("Retrying with refined prompt...")
                    else:
                        self.logger.error("Maximum retries reached or retry not advised. Task failed.")
                        final_agent_result = {
                            "status": "FAILURE_MAX_RETRIES", 
                            "message": f"Task failed after {current_retry_attempt + 1} attempt(s).",
                            "generated_code": last_generated_code,
                            "execution_stdout": execution_result.get("stdout"),
                            "execution_stderr": execution_result.get("stderr"),
                            "validation_feedback": validation_result["feedback"]
                        }
                        break 
            # --- End of Iterative Loop ---

        except Exception as e:
            self.logger.error(f"An unhandled exception occurred in the MainAgent: {e}", exc_info=True)
            final_agent_result = {"status": "CRITICAL_FAILURE_UNHANDLED_EXCEPTION", "message": str(e)}
        
        # 8. Deliver Output
        self.logger.info("Delivering final agent output.")
        self.output_delivery_mod.deliver_output(final_agent_result)
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
                agent_log_level = getattr(agent_log_level_str_log, default_log_level)
                agent_log_file = config.get('LOG', 'log_file', fallback=default_log_file)

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

    # Initialize and run the agent
    agent = MainAgent(
        gemini_model_name=gemini_model_name,
        log_file=agent_log_file, # Pass configured log file
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