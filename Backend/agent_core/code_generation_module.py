import logging,sys
import ast
import os
from .logging_module import LoggingModule
import configparser # For reading .ini file in __main__

# Import Vertex AI and related libraries
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel
    # import vertexai.preview.generative_models as generative_models
    from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold, GenerationConfig
 
    from google.oauth2 import service_account
    GOOGLE_CLOUD_SDK_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_SDK_AVAILABLE = False
    # print("Vertex AI SDK not found. CodeGenerationModule will operate in mock mode.")

CONFIG_FILE_NAME = "configuration.ini" # Define at module level for __main__

class CodeGenerationModule:
    def __init__(self, 
                 logger: LoggingModule, 
                 model_name: str,
                 service_account_file: str | None = None, 
                 project_id: str | None = None,
                 location: str = "us-central1"):
        self.logger = logger
        self.service_account_file = service_account_file
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.model = None
        self._is_mock = True

        if GOOGLE_CLOUD_SDK_AVAILABLE and self.service_account_file and self.project_id:
            try:
                if not os.path.exists(self.service_account_file):
                    self.logger.error(f"Service account file not found: {self.service_account_file}. Will operate in mock mode.")
                else:
                    credentials = service_account.Credentials.from_service_account_file(self.service_account_file)
                    vertexai.init(project=self.project_id, location=self.location, credentials=credentials)
                    self.model = GenerativeModel(self.model_name)
                    self._is_mock = False
                    self.logger.info(f"Vertex AI initialized successfully. Model: {self.model_name} in project {self.project_id}, location {self.location}.")
            except Exception as e:
                self.logger.error(f"Failed to initialize Vertex AI: {e}. Will operate in mock mode.", exc_info=True)
                self.model = None
                self._is_mock = True
        else:
            if not GOOGLE_CLOUD_SDK_AVAILABLE:
                self.logger.warning("Vertex AI SDK (google-cloud-aiplatform) not found.")
            if not self.service_account_file:
                self.logger.warning("Service account file not provided for CodeGenerationModule.")
            if not self.project_id:
                 self.logger.warning("GCP Project ID not provided for CodeGenerationModule.")
            self.logger.warning("CodeGenerationModule operating in MOCK mode due to missing configuration or SDK.")

    def _validate_python_syntax(self, code: str) -> bool:
        """Validates the syntax of the generated Python code."""
        try:
            ast.parse(code)
            self.logger.info("Generated code passed Python syntax check.")
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error in generated code: {e}")
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during syntax validation: {e}")
            return False

    def _extract_code_from_response(self, response_text: str) -> str | None:
        """Extracts Python code from a markdown code block in the response."""
        self.logger.debug(f"Attempting to extract code from AI response. Full response text:\n--BEGIN AI RESPONSE--\n{response_text}\n--END AI RESPONSE--")
        
        # Try to find ```python ... ``` block first
        python_block_start = response_text.find("```python")
        if python_block_start != -1:
            block_end = response_text.find("```", python_block_start + len("```python"))
            if block_end != -1:
                code = response_text[python_block_start + len("```python"):block_end].strip()
                self.logger.info("Extracted code using ```python block.")
                return code

        # If not found, try to find general ``` ... ``` block
        general_block_start = response_text.find("```")
        if general_block_start != -1:
            block_end = response_text.find("```", general_block_start + len("```"))
            if block_end != -1:
                # Check if this block might actually be a python block without the explicit tag
                potential_code = response_text[general_block_start + len("```"):block_end].strip()
                # Basic heuristic: if it contains typical python keywords or structures, assume it is code
                if "def " in potential_code or "import " in potential_code or "print(" in potential_code or "class " in potential_code:
                    self.logger.info("Extracted code using general ``` block (heuristic match for Python).")
                    return potential_code
                else:
                    self.logger.warning("Found general ``` block, but content doesn't strongly resemble Python code. No code extracted by this method.")
        
        # If no markdown blocks, and the response is short and looks like code, assume it might be raw code
        # This is a weaker heuristic
        if "```" not in response_text and len(response_text.splitlines()) < 20: # Arbitrary line limit
             if "def " in response_text or "import " in response_text or "print(" in response_text:
                self.logger.info("No markdown block found, but response is short and heuristically looks like Python code.")
                return response_text.strip()

        self.logger.warning("Could not extract Python code from AI response using markdown blocks or simple heuristics.")
        return None

    def _extract_packages_from_response(self, response_text: str) -> list[str]:
        """Extracts package names from a ```text\nrequirements.txt\n...``` block."""
        packages = []
        start_marker = "```text\nrequirements.txt\n"
        end_marker = "```"

        start_index = response_text.find(start_marker)
        if start_index != -1:
            content_start = start_index + len(start_marker)
            end_index = response_text.find(end_marker, content_start)
            if end_index != -1:
                package_block = response_text[content_start:end_index].strip()
                # Split into lines and filter out empty lines
                packages = [line.strip() for line in package_block.splitlines() if line.strip() and not line.strip().startswith('#')]
                self.logger.info(f"Extracted packages from requirements.txt block: {packages}")
            else:
                self.logger.warning("Found start of requirements.txt block but no closing ```.")
        else:
            self.logger.info("No requirements.txt block found in AI response.")

        return packages

    def generate_code(self, prompt: str) -> dict:
        self.logger.info("Code generation process started.")
        self.logger.debug(f"Received prompt for code generation (first 200 chars): {prompt[:200]}...")

        if not prompt:
            self.logger.error("Cannot generate code: Prompt is empty.")
            return {"code": None, "error": "Prompt is empty", "syntax_valid": False, "required_packages": []}

        generated_code_text = None
        error_message = None
        required_packages = []

        if not self._is_mock and self.model:
            try:
                self.logger.info(f"Sending prompt to Vertex AI model: {self.model_name}")
                generation_config = GenerationConfig(
                    temperature=0.4, 
                    max_output_tokens=64000, # Increased as requested
                    top_p=0.9 
                )
                # Add a small instruction to the system/context part of the prompt
                effective_prompt = prompt + "\nEnsure the generated Python code is complete, executable, and fits within token limits. Also provide a list of all required packages in a ```text\nrequirements.txt\n...``` block."

                response = self.model.generate_content(
                    [effective_prompt],
                    generation_config=generation_config,
                    safety_settings=({
                        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    })
                )
                
                raw_response_text = ""
                finish_reason_name = "UNKNOWN" # Default if not available

                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    # Safely get finish_reason
                    if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                        try:
                            finish_reason_name = candidate.finish_reason.name
                        except AttributeError: # In case .name is not present on some FinishReason enum values
                            finish_reason_name = str(candidate.finish_reason)
                    
                    self.logger.info(f"Vertex AI response received. Finish Reason: {finish_reason_name}")

                    # Safely get content parts
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts and len(candidate.content.parts) > 0:
                        part = candidate.content.parts[0]
                        raw_response_text = ""
                        
                        # Check for text attribute first (most common case)
                        if hasattr(part, 'text'):
                            raw_response_text = part.text
                        # Check for thought attribute (may appear in Gemini 2.5 models)
                        elif hasattr(part, 'thought'):
                            raw_response_text = str(part.thought)
                        # Check if part itself can be converted to string as fallback
                        elif hasattr(part, '__str__'):
                            raw_response_text = str(part)
                        else:
                            # Part exists but has no usable text content
                            self.logger.error(f"Vertex AI response part has no extractable text content. Finish Reason: {finish_reason_name}. Part: {part}")
                            error_message = f"Vertex AI response part has no extractable text content. Finish Reason: {finish_reason_name}. Part type: {type(part)}. (see logs for details)."
                            # Continue to extraction attempt with potentially empty raw_response_text
                        
                        # Log and print the raw response text
                        self.logger.info(f"Raw Vertex AI Response for Task (first 500 chars):\n{raw_response_text[:500]}...")
                        print(f"\n--- Raw Vertex AI Response ---\n{raw_response_text}\n--- End Raw Response ---\n") # Print to console

                        if raw_response_text:
                            # Extract code and packages from the raw response text
                            generated_code_text = self._extract_code_from_response(raw_response_text)
                            required_packages = self._extract_packages_from_response(raw_response_text)

                            if not generated_code_text:
                                # Code extraction failed, log with finish reason and raw response
                                self.logger.error(f"Code extraction failed. Finish Reason: {finish_reason_name}. Raw response from Vertex AI was: {raw_response_text}")
                                error_message = f"Code extraction failed from Vertex AI response. Finish Reason: {finish_reason_name}. (see logs for raw response)."
                        else:
                            # No text could be extracted from the part
                            self.logger.error(f"No text content could be extracted from response part. Finish Reason: {finish_reason_name}.")
                            error_message = f"No text content could be extracted from Vertex AI response part. Finish Reason: {finish_reason_name}."
                    else: # No content parts, but have a candidate
                        error_message = f"Vertex AI response has no content parts. Finish Reason: {finish_reason_name}."
                        self.logger.error(error_message)
                else: # No candidates in response
                    error_message = "Vertex AI response was empty or contained no candidates."
                    # Log the base error message first. If prompt_feedback exists, it will append to this.
                    self.logger.error(error_message) 
                    
                    # Check for prompt feedback (usually on the main response object, even if candidates list is empty)
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        # Safely get block_reason name
                        block_reason_name = "UNKNOWN_BLOCK_REASON"
                        if hasattr(response.prompt_feedback.block_reason, 'name'):
                            block_reason_name = response.prompt_feedback.block_reason.name
                        else:
                            block_reason_name = str(response.prompt_feedback.block_reason)
                        
                        blocked_reason_msg = response.prompt_feedback.block_reason_message or "No specific message."
                        self.logger.error(f"Prompt blocked. Reason: {block_reason_name}. Message: {blocked_reason_msg}")
                        # Append to existing error_message
                        error_message += f" Prompt blocked due to {block_reason_name}: {blocked_reason_msg}"

            except Exception as e:
                self.logger.error(f"Error during Vertex AI code generation: {e}", exc_info=True)
                error_message = str(e)
        else: # MOCK MODE
            self.logger.info("Using MOCK code generation.")
            if "add two numbers" in prompt.lower():
                generated_code_text = (
                    "def add(a, b):\n"
                    "    \"\"\"Adds two numbers.\"\"\"\n"
                    "    return a + b\n"
                    "\n"
                    "# Example usage:\n"
                    "num1 = 5\n"
                    "num2 = 3\n"
                    "print(f\"The sum of {num1} and {num2} is {add(num1, num2)}\")"
                )
                required_packages = [] # No specific packages needed for this simple example
            elif "refactor" in prompt.lower() and "dummy_script.py" in prompt:
                 generated_code_text = (
                    "# Refactored code for dummy_script.py\n"
                    "def efficient_function():\n"
                    "    # Improved logic here\n"
                    "    return 2 * 2\n"
                    "\n"
                    "print(efficient_function())"
                )
                 required_packages = []
            elif "read the excel file" in prompt.lower() or "sort by spend_usd" in prompt.lower():
                 # Simulate the response you provided for the Excel task
                 generated_code_text = (
                    "import pandas as pd\n"
                    "import sys\n"
                    "\n"
                    "try:\n"
                    "    # Read the Excel file into a pandas DataFrame\n"
                    "    excel_file_path = 'C:\\\\Users\\\\aishwarya.rane\\\\OneDrive - Zycus\\\\Documents\\\\File_Processing_Agent\\\\uploads\\\\13a74e6a-a734-4b52-8b61-5ea8577d05bc_Input.xlsx' # Placeholder - path should be dynamic\n"
                    "    df = pd.read_excel(excel_file_path, engine='openpyxl')  # Explicitly use openpyxl engine\n"
                    "\n"
                    "    # Sort the DataFrame by 'spend_usd' in descending order\n"
                    "    df_sorted = df.sort_values(by='spend_usd', ascending=False)\n"
                    "\n"
                    "    # Save the sorted DataFrame to a new Excel file\n"
                    "    output_file_path = 'output.xlsx'\n"
                    "    df_sorted.to_excel(output_file_path, index=False, engine='openpyxl')  # Explicitly use openpyxl engine\n"
                    "\n"
                    "    print(f\"Successfully sorted and saved the data to {output_file_path}\")\n"
                    "\n"
                    "except FileNotFoundError:\n"
                    "    print(f\"Error: File not found at {excel_file_path}\", file=sys.stderr)\n"
                    "    sys.exit(1)  # Exit with non-zero status code\n"
                    "except Exception as e:\n"
                    "    print(f\"Error processing Excel file: {e}\", file=sys.stderr)\n"
                    "    sys.exit(1)  # Exit with non-zero status code\n"
                    "\n"
                )
                 required_packages = ["pandas", "openpyxl"]
            else:
                generated_code_text = "# Placeholder for AI-generated code\nprint('Hello from MOCK generated code!')"
                required_packages = []

        if error_message:
             return {"code": None, "error": error_message, "syntax_valid": False, "required_packages": []}

        if not generated_code_text:
            # This condition might be redundant if error_message is always set when generated_code_text is None
            # but kept for safety.
            return {"code": None, "error": "No code was generated or extracted.", "syntax_valid": False, "required_packages": []}
            
        # Validate syntax of the generated code only if code was extracted/generated
        syntax_valid = self._validate_python_syntax(generated_code_text)

        return {"code": generated_code_text, "error": error_message, "syntax_valid": syntax_valid, "required_packages": required_packages}


# --- Main execution for testing CodeGenerationModule directly ---
if __name__ == '__main__':
    # This __main__ block is for isolated testing of CodeGenerationModule
    # In the full agent, MainAgent initializes and uses this module.

    # Setup logging for standalone test
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        handlers=[
                            logging.StreamHandler(sys.stdout) # Log to console
                        ])
    test_logger = logging.getLogger(__name__)

    # Assume a dummy config file for testing purposes if needed
    # For this test, we'll rely on environment variables or defaults

    # --- Test with MOCK mode enabled (simulating no SDK or config) ---
    print("\n--- Testing CodeGenerationModule in MOCK Mode ---")
    mock_generator = CodeGenerationModule(logger=test_logger, model_name="mock-model") # No SA file, Project ID -> mock mode

    # Test case 1: Simple prompt in MOCK mode
    prompt1 = "Generate a python script to add two numbers"
    result1 = mock_generator.generate_code(prompt1)
    print(f"Result 1 (MOCK): {result1}")
    assert result1["code"] is not None
    assert result1["syntax_valid"] is True
    assert result1["required_packages"] == []

    # Test case 2: Excel prompt in MOCK mode (to test requirements extraction sim)
    print("\n--- Testing CodeGenerationModule in MOCK Mode (Excel Prompt) ---")
    prompt2 = "read the excel file and sort by spend_usd column in descending order"
    result2 = mock_generator.generate_code(prompt2)
    print(f"Result 2 (MOCK - Excel): {result2}")
    assert result2["code"] is not None
    assert result2["syntax_valid"] is True
    assert result2["required_packages"] == ["pandas", "openpyxl"]

    # --- Test with actual Vertex AI (if config is set) ---
    # To run this part, ensure GOOGLE_CLOUD_SDK_AVAILABLE is True
    # and set up configuration.ini with service_account_json_path, project_id, location.

    # Determine workspace root to find configuration.ini
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(script_dir)
    config_path = os.path.join(workspace_root, CONFIG_FILE_NAME)

    print("\n--- Testing CodeGenerationModule with actual Vertex AI (if configured) ---")

    if GOOGLE_CLOUD_SDK_AVAILABLE and os.path.exists(config_path):
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            sa_file = config.get('VertexAI', 'service_account_json_path', fallback=None)
            proj_id = config.get('VertexAI', 'project_id', fallback=None) # Read project_id from config for test init
            loc = config.get('VertexAI', 'location', fallback='us-central1')
            model = config.get('VertexAI', 'model_name', fallback='gemini-2.5-pro-preview-05-06')
            
            if sa_file and proj_id and os.path.exists(sa_file):
                 # Initialize Vertex AI with credentials for this test run if possible
                 # Note: In the A2A wrapper, this init happens based on the JSON file read in run_main_agent_for_a2a
                 # This is just for direct testing of CodeGenerationModule
                 credentials = service_account.Credentials.from_service_account_file(sa_file)
                 vertexai.init(project=proj_id, location=loc, credentials=credentials)

                 real_generator = CodeGenerationModule(
                     logger=test_logger, 
                     model_name=model, # Use model from config
                     service_account_file=sa_file, # Pass config values
                     project_id=proj_id,
                     location=loc
                )
                
                 if not real_generator._is_mock:
                    # Test case 3: Simple prompt with real AI
                    print("\n--- Running Test Case 3: Simple Prompt with Real AI ---")
                    prompt3 = "Generate a python script that prints the current date and time."
                    result3 = real_generator.generate_code(prompt3)
                    print(f"Result 3 (REAL AI): {result3}")
                    # Assertions might vary based on AI output, check for code and package list structure
                    assert result3["code"] is not None
                    assert isinstance(result3["required_packages"], list)

                    # Test case 4: Prompt that likely needs packages with real AI
                    print("\n--- Running Test Case 4: Prompt needing packages with Real AI ---")
                    prompt4 = "Write a python script that reads a CSV file named 'data.csv' using pandas and prints the first 5 rows."
                    result4 = real_generator.generate_code(prompt4)
                    print(f"Result 4 (REAL AI - Pandas): {result4}")
                    assert result4["code"] is not None
                    assert isinstance(result4["required_packages"], list)
                    # We might expect 'pandas' to be in the required_packages list
                    assert "pandas" in result4["required_packages"]

                 else:
                     print("Skipping real AI test: CodeGenerationModule is in mock mode even with config.")
            else:
                 print("Skipping real AI test: Missing required configuration (service account file or project ID) or service account file not found.")
        except Exception as e:
            print(f"An error occurred during real AI test setup or execution: {e}")
    else:
        print(f"Skipping real AI test: Vertex AI SDK not available or configuration.ini not found at {config_path}.")

    print("\nCodeGenerationModule tests finished.") 