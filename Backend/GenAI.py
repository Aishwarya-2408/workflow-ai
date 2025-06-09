import csv
import io
import os
import configparser
import time
import threading
import concurrent.futures
import queue
from threading import Lock
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
from vertexai.generative_models import GenerativeModel, Part, Content, ChatSession
from vertexai.generative_models import HarmCategory, HarmBlockThreshold
import vertexai
import json
import xlrd
import jsonschema

from PromptOptimizer import PromptOptimizer
from utility.logger import get_logger


class GeminiVertexAI:
    """
    A class to interact with Google's Gemini models via Vertex AI.

    Reads configuration from a .ini file.  Supports chat history and CSV file
    parsing for context.  Loads chat history from a separate JSON file.
    """

    def __init__(self, config_file_path: str = "configuration.ini", history_file_path: str = "./chat_history/workflow_chat_history.json", timestamp = None):
        """
        Initializes the GeminiVertexAI object.

        Args:
            config_file_path: Path to the .ini configuration file.  Defaults to "configuration.ini".
            history_file_path: Base path to the JSON file containing the chat history.
                                If the file exists, it's loaded.  If not, a new file with a timestamp is created.

        Raises:
            ValueError: If any required configuration parameters are missing or invalid.
            FileNotFoundError: If the config file is not found.
        """
        # Configure logging
        self.logger = get_logger()

        self.config_file_path = config_file_path
        self.history_file_path = history_file_path  # Store the base path
        self.config = configparser.ConfigParser()
        self.df = None
        self.logger.info(f"\n\n{20 * '*'} Initializing GeminiVertexAI with config file: {config_file_path} and history file: {history_file_path} {20 * '*'}\n")

        try:
            if not os.path.exists(self.config_file_path):
                self.logger.error(f"Config file not found: {self.config_file_path}")
                raise FileNotFoundError(f"Config file not found: {self.config_file_path}")

            self.timestamp = None
            if timestamp is not None:
                self.timestamp = timestamp
            # Check if the history file exists.  If not, create a timestamped version.
            if not os.path.exists(self.history_file_path):
                base, ext = os.path.splitext(self.history_file_path)
                if self.timestamp is None:
                    self.timestamp = time.strftime("%Y%m%d_%H%M%S")
                self.history_file_path = f"{base}_{self.timestamp}{ext}"  # Update with timestamped path
                self.logger.info(f"History file not found.  Using timestamped file: {self.history_file_path}")
            else:
                self.logger.info(f"Using existing history file: {self.history_file_path}")

            self.config.read(self.config_file_path)
            self._validate_config()
            self._load_config()
            self._load_history()  # Always attempt to load; will create if not exists
            self._initialize_model()
            self.prompt_optimizer = PromptOptimizer(self.logger, self.config)
            self.logger.info("GeminiVertexAI initialized successfully")

        except (FileNotFoundError, ValueError, configparser.Error) as e:
            self.logger.error(f"Initialization error: {e}")
            raise

    def _validate_config(self):
        """Validates the configuration from the .ini file."""
        self.logger.debug("Validating configuration...")
        required_sections = ["GEMINI"]
        for section in required_sections:
            if not self.config.has_section(section):
                self.logger.error(f"Missing required section in config file: {section}")
                raise ValueError(f"Missing required section in config file: {section}")

        required_keys = {
            "GEMINI": [
                "GOOGLE_APPLICATION_CREDENTIALS",
                "MODEL_NAME",
                "TEMPERATURE",
                "TOP_P",
                "TOP_K",
                "PROJECT_ID",
            ]
        }
        for section, keys in required_keys.items():
            for key in keys:
                if not self.config.has_option(section, key):
                    self.logger.error(f"Missing required key '{key}' in section '{section}' of config file.")
                    raise ValueError(f"Missing required key '{key}' in section '{section}' of config file.")

        credentials_path = self.config.get("GEMINI", "GOOGLE_APPLICATION_CREDENTIALS")
        if not os.path.exists(credentials_path):
            self.logger.error(f"GOOGLE_APPLICATION_CREDENTIALS file not found: {credentials_path}")
            raise ValueError(f"GOOGLE_APPLICATION_CREDENTIALS file not found: {credentials_path}")

        self.logger.debug("Configuration validation successful.")

    def _load_config(self):
        """Loads configuration parameters from the .ini file."""
        try:
            gemini_config = self.config["GEMINI"]
            self.logger.debug("Loading configuration from GEMINI section.")

            self.model_name = gemini_config.get("MODEL_NAME")
            self.temperature = float(gemini_config.get("TEMPERATURE"))
            self.top_p = float(gemini_config.get("TOP_P"))
            self.top_k = int(gemini_config.get("TOP_K"))
            self.max_output_tokens = int(gemini_config.get("MAX_OUTPUT_TOKENS", '8192'))
            self.max_workers = int(gemini_config.get("MAX_WORKERS", '10'))
            self.project_id = gemini_config.get("PROJECT_ID")
            self.location = gemini_config.get("LOCATION", "us-central1")
            self.safety_settings = self._get_safety_settings()

            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gemini_config.get("GOOGLE_APPLICATION_CREDENTIALS")

            self.logger.info(f"Loaded configuration: model_name={self.model_name}, temperature={self.temperature}, top_p={self.top_p}, top_k={self.top_k}, max_output_tokens={self.max_output_tokens}, max_workers={self.max_workers}, project_id={self.project_id}, location={self.location}")
            self.logger.debug("Configuration loaded successfully.")
        except (ValueError, KeyError) as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise

    def _get_safety_settings(self) -> Dict[HarmCategory, HarmBlockThreshold]:
        """Processes and returns the safety settings from configuration.ini.

        Returns:
            Dict[HarmCategory, HarmBlockThreshold]: A dictionary of safety settings.
                Returns a default set of BLOCK_NONE settings if no valid settings are found in the config file.
        """
        safety_settings = {}
        if self.config.has_section("SAFETY_SETTINGS"):
            self.logger.debug("Processing safety settings from SAFETY_SETTINGS section.")
            for key, value in self.config.items("SAFETY_SETTINGS"):
                try:
                    harm_category = HarmCategory[key.upper()]
                    harm_threshold = HarmBlockThreshold[value.upper()]
                    safety_settings[harm_category] = harm_threshold
                    self.logger.debug(f"Loaded safety setting: {harm_category} = {harm_threshold}")
                except KeyError:
                    self.logger.warning(f"Invalid safety setting key or value: {key} = {value}. Skipping.")
        else:
            self.logger.warning("No SAFETY_SETTINGS section found in config file.")

        if not safety_settings:
            self.logger.info("No valid safety settings found in config.  Defaulting to BLOCK_NONE.")
            safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                # HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
            }

        self.logger.debug(f"Final safety settings: {safety_settings}")
        return safety_settings

    def _initialize_model(self):
        """Initializes the Vertex AI model and sets the system instruction."""
        try:
            self.chat_history = []

            vertexai.init(project=self.project_id, location=self.location)
            self.logger.info(f"Initialized Vertex AI with project: {self.project_id}")

            self.system_instruction = "Strictly just return only JSON response and follow the JSON schema as given in examples."  # Store as instance variable
            self.model = GenerativeModel(
                model_name=self.model_name,
                system_instruction=self.system_instruction
            )
            self.chat = self.model.start_chat(response_validation=False)
            self.logger.info(f"Chat session ID: {id(self.chat)}")

            self.logger.info(f"Initialized GenerativeModel with model name: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Error initializing model: {e}")
            raise

    def _add_to_history(self, content: Content):
        """Adds a Content object to the chat history and saves it to the file.
        """
        # if self.chat is not None:  # Only add to history if chat is initialized
        #     self.chat_history.append(content)  # Add ALL content to self.chat_history
        #     if self.history_file_path:
        #         self._save_history()
        # else:
        #     self.logger.warning("Chat not initialized. Cannot add to history.")

        if self.chat is not None:  # Only add to history if chat is initialized
            if content.role == 'model':  # *ONLY* add model responses!
                self.chat_history.append(content)
                if self.history_file_path:
                    self._save_history()
        else:
            self.logger.warning("Chat not initialized. Cannot add to history.")

    def _detect_header_row(self, df: pd.DataFrame) -> int:
        """Detects the header row index in a DataFrame.

        Args:
            df: A DataFrame.

        Returns:
            int: The index of the detected header row (0-indexed).  Returns 0
                 if no header is detected (i.e., the first row is assumed to be data).
        """

        # Heuristic 1: Check for a row where most entries are strings
        for i, row in df.iterrows():
            str_count = sum(isinstance(x, str) for x in row)
            if str_count > len(row) / 2:
                self.logger.debug(f"Header row detected at row index {i} (string heuristic).")
                return i

        # Heuristic 2: If no row has mostly strings, assume first row is data
        self.logger.debug("No header row detected. Assuming first row is data.")
        return 0

    def _process_csv_file(self, file_path: str, num_rows: int = 10, include_header: bool = True, header_rows: int = 1, data_start_row: int = 2, handle_na: bool = False, raw_read: bool = False) -> pd.DataFrame:
        """Reads a CSV file, handling header rows and data start row.

        Args:
            file_path: Path to the CSV file.
            num_rows: Number of rows to read.
            include_header: Whether to include all rows (for level extraction) or skip header rows (for data processing).
            header_rows: Number of header rows (0-indexed).  Only used if include_header is False.
            data_start_row: Row index (0-indexed) where the data begins. Only used if include_header is False.
            handle_na (bool): Whether to replace default NA values.
            raw_read (bool): Whether to read raw CSV with `header=None, keep_default_na=False` (for specific cases).

        Returns:
            pd.DataFrame: DataFrame containing the read rows.

        Raises:
            Exception: If there is an error processing the CSV file.
            xlrd.biffh.XLRDError: If there is the specific "Zycus-Only" tag error.
        """
        try:
            # Ensure StringIO is reset
            if isinstance(file_path, io.StringIO):
                file_path.seek(0)

            if raw_read:
                # Use Case 2: Read CSV as raw (without headers, keep_default_na=False)
                self.logger.debug(f"Processing CSV file (raw read): {file_path}")
                df = pd.read_csv(file_path, header=None, keep_default_na=False)
                self.logger.info(f"Successfully read {len(df)} rows from {file_path} (raw read).")
                return df

            if include_header:
                # Use Case 1: Read the specified number of rows, including any header rows.
                self.logger.debug(f"Processing CSV file (including header): {file_path}, reading {num_rows} rows.")
                df = pd.read_csv(file_path, nrows=num_rows)
                self.logger.info(f"Successfully read {len(df)} rows from {file_path} (including header).")
                return df
            else:
                # Skip header rows and read data rows.
                self.logger.debug(f"Processing CSV file (skipping header): {file_path}, reading {num_rows} data rows starting from row {data_start_row}.")
                # header = header_rows - 1, as it is 0 indexed and skiprows is 1 indexed, so passing the value accordingly
                df = pd.read_csv(file_path, header=header_rows-1, skiprows=range(1, data_start_row), nrows=num_rows, keep_default_na=handle_na)
                self.logger.info(f"Successfully read {len(df)} rows from {file_path} (after header).")
                return df

        except xlrd.biffh.XLRDError as e:
            self.logger.error(f"Error processing CSV file: {e}. Please remove the 'Zycus-Only' tag from the file and try again.")
            raise  RuntimeError("Error processing CSV file. Please remove the 'Zycus-Only' tag from the file and try again.")
        except Exception as e:
            self.logger.error(f"Error processing CSV file: {e}")
            raise Exception(f"Error processing CSV file: {e}")
        finally:
            # Ensure StringIO is reset
            if isinstance(file_path, io.StringIO):
                file_path.seek(0)
        

    def _validate_json_with_schema(self, data: Dict, schema: Dict) -> None:
        """Validates JSON data against a given schema using jsonschema."""
        # ... (No changes here) ...
        if not isinstance(data, dict):
            raise ValueError("Input data must be a dictionary.")
        if not isinstance(schema, dict):
            raise ValueError("JSON schema must be a dictionary.")
        try:
            jsonschema.validate(instance=data, schema=schema)
            self.logger.info("JSON is valid according to the schema.")
        except jsonschema.ValidationError as e:
            self.logger.error(f"JSON schema validation error: {e}")
            raise

    def start_chat_session(self, use_history=True):
        """Starts a chat session.

        Args:
            use_history: Whether to initialize the chat with the loaded history.
                         Defaults to True. Set to False to start a fresh session without prior context.
        """
        try:
            if use_history:
                self.chat = self.model.start_chat(history=self.chat_history)
                self.logger.info("Chat session started with history.")
                if self.chat_history:
                    self.logger.debug(f"Chat history loaded with {len(self.chat_history)} entries.")
                else:
                    self.logger.debug("Chat history is empty.")
            else:
                self.chat = self.model.start_chat()  # Start a *fresh* session
                self.logger.info("Chat session started without history.")

        except Exception as e:
            self.logger.error(f"Error starting chat session: {e}")
            raise

    def send_message(self, message: str, generation_config: Optional[Dict[str, Any]] = None, use_history: bool = True) -> Tuple[str, Dict[str, int]]:
        """Sends a message to the chat (optionally using history_, optionally including CSV data and returns the response and usage metadata.

        Args:
            message: The message to send.
            generation_config: Optional generation configuration.
            use_history: Whether to use the chat history for this message.
                         Defaults to True.  Set to False for interactions that should not be influenced by previous turns.

        Returns:
            Tuple[str, Dict[str, int]]:  A tuple containing:
                - The response text (str).
                - Usage metadata (Dict[str, int]) with keys 'input_token_count', 'output_token_count', 'total_token_count', and 'cached_content_token_count'.
                  Returns an empty dictionary for usage metadata if it's not available.

        Raises:
            Exception: If an error occurs during the chat interaction.
        """
        # if self.chat is None:
        #     self.start_chat_session()  # Initialize chat if it doesn't exist
        #     self.logger.info("Chat was not initialized, starting a new session.")

        if self.chat is None or not use_history:  # Re-initialize chat if needed
            self.start_chat_session(use_history=use_history)
            if not use_history:
                self.logger.info("Chat re-initialized without history for this message.")
            else:
                self.logger.info("Chat initialized/re-initialized.")

        try:
            parts = [Part.from_text(message)]
            user_content = Content(role="user", parts=parts)
            self.logger.debug(f"Sending message  (first 50 chars):: {message[:50]}...")  # Log first 50 chars of message

            # Add user_content to chat_history *before* sending.
            self.chat_history.append(user_content)

            if not generation_config:
                generation_config = {
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                    "max_output_tokens": self.max_output_tokens,
                }

            self.logger.debug(f"Using generation config: {generation_config}")

            time.sleep(10)
            response = self.chat.send_message(
                user_content,
                safety_settings=self.safety_settings,
                generation_config=generation_config,
                stream=False  # Disable streaming
            )

            full_response_text = response.text
            self.logger.debug(f"Received response: {full_response_text[:50]}...")  # Log first 50 chars of response

            # --- Usage Metadata Handling ---
            usage_metadata = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_metadata = {
                    'input_token_count': response.usage_metadata.prompt_token_count,
                    'output_token_count': response.usage_metadata.candidates_token_count,
                    'total_token_count': response.usage_metadata.total_token_count,  # Total tokens (input + output)
                    'cached_content_token_count': getattr(response.usage_metadata, 'cached_content_token_count', 0)   # Cached tokens, default to 0 if not present
                }
                self.logger.info(f"Usage metadata received")
            else:
                self.logger.warning("No usage metadata received.")

            # Add the model's response to the history *after* receiving the response.
            model_content = Content(role="model", parts=[Part.from_text(full_response_text)])
            self._add_to_history(model_content)

            return full_response_text, usage_metadata  # Return both text and metadata

        except Exception as e:
            self.logger.error(f"Error during chat interaction: {e}")
            raise Exception(f"Error during chat interaction: {e}")

    def _load_history(self):
        """Loads the chat history from the JSON file. Creates the file if it doesn't exist (with system instruction if present)."""
        self.chat_history = []  # Initialize chat_history
        self.logger.debug(f"Loading chat history from: {self.history_file_path}")
        try:
            # Attempt to open and load.  If it fails (e.g., file doesn't exist), a new, empty history will be used.
            with open(self.history_file_path, "r") as f:
                loaded_history = json.load(f)
                self.logger.debug(f"Loaded raw history from file: {loaded_history}")

            for item in loaded_history:
                self.logger.debug(f"Processing history item: {item}")
                # Handle system instruction separately
                if item["role"] == "system":
                    self.system_instruction = item["parts"][0]  # Load from history if exists.
                    self.logger.debug(f"Loaded system instruction from history: {self.system_instruction}")
                    continue  # Don't add system instruction as regular content

                # Ensure all parts are strings.
                parts = []
                for part in item["parts"]:
                    if isinstance(part, str):
                        parts.append(Part.from_text(part))
                    elif isinstance(part, dict):  # Handle dictionaries
                        parts.append(Part.from_text(json.dumps(part)))
                    else:  # For other datatypes
                        parts.append(Part.from_text(str(part)))
                content = Content(role=item["role"], parts=parts)

                # # *ONLY* add to self.chat_history if the role is 'model'
                # if content.role == 'model':
                #     self.chat_history.append(content)
                #     self.logger.debug(f"Appended content with role 'model' to chat_history.")
                # else:
                #     self.logger.debug(f"Skipped adding content with role '{content.role}' to chat_history.")

                # Add ALL content (both user and model) to create proper conversation flow
                self.chat_history.append(content)
                self.logger.debug(f"Added content with role '{content.role}' to chat_history")

        except FileNotFoundError:
            self.logger.info(f"History file not found. Creating a new one: {self.history_file_path}")
            # File doesn't exist, so create it with an empty list.
            with open(self.history_file_path, "w") as f:
                json.dump([], f)  # Initialize with empty list
        except json.JSONDecodeError as e:
            self.logger.error(f"Error loading chat history: {e}.  Using an empty history.")
            # If there's a JSON error, start with a fresh, empty history.
        except Exception as e:  # Added to handle other exceptions
            self.logger.error(f"An unexpected error occurred in load history: {e}")
            raise

    def _save_history(self):
        """Saves current chat history to JSON, including the system instruction."""
        try:
            serializable_history = []

            # Add system instruction *only* if it's set and not already in history
            if hasattr(self, 'system_instruction') and self.system_instruction:
                system_instruction_present = False
                for content in self.chat_history:
                    if content.role == "system":
                        system_instruction_present = True
                        break
                if not system_instruction_present:
                    serializable_history.append({"role": "system", "parts": [self.system_instruction]})
                    self.logger.debug(f"Adding system instruction to history for saving: {self.system_instruction}")
                else:
                    self.logger.debug("System instruction already present in history. Skipping addition for saving.")
            else:
                self.logger.debug("No system instruction to save.")

            for content in self.chat_history:
                if content.role != "system":  # Don't save system instruction as regular content
                    # Serialize *only* the text from Part objects.
                    serializable_parts = [part.text for part in content.parts]  # Correct
                    serializable_history.append({"role": content.role, "parts": serializable_parts})
                    # self.logger.debug(f"Adding content to serializable history: role={content.role}, parts (first 50 chars)={[part[:50] for part in serializable_parts]}")

            with open(self.history_file_path, "w") as f:
                json.dump(serializable_history, f)
                self.logger.info(f"Chat history saved to: {self.history_file_path}")

        except (FileNotFoundError, TypeError) as e:
            self.logger.error(f"Error saving chat history: {e}")
            raise
        except Exception as e:
            self.logger.error(f"An unexpected error occurred in save history: {e}")
            raise

    def extract_levels(self, file_path: str, prompt: str, num_rows: int = 10, optimize_prompt_flag: bool = False) -> Tuple[Dict[str, Any], Dict[str, int]]:
        """
        Extracts level information from the provided CSV data using the given prompt along with usage metadata.

        Args:
            file_path: Path to the CSV file.
            prompt: The prompt for extracting level information.
            num_rows: Number of rows to process
            optimize_prompt_flag: Whether to optimize teh prompt or not.

        Returns:
            Tuple[Dict[str, Any], Dict[str, int]]: (extracted levels JSON, usage metadata).
        """
        try:
            self.logger.info(f"{20 * '*'} Extracting levels from first {num_rows} rows {20 * '*'}")
            self.df = self._process_csv_file(file_path, num_rows=num_rows, include_header=True)  # include_header=True
            csv_data_string = self.df.to_string(index=False)

            # if optimize_prompt_flag:
            #     # Use the PromptOptimizer instance
            #     prompt, optimization_usage = self.prompt_optimizer.optimize_prompt(
            #         original_prompt=prompt,
            #         csv_data=csv_data_string,
            #         task_description="extract level information from a CSV file...",
            #         output_schema=level_schema
            #     )
            #     self.logger.info(f"Prompt Optimization Usage: {optimization_usage}")  # Log per-call usage

            prompt_with_data = f"{prompt}\n\n--- START OF FILE ---\n{csv_data_string}\n--- END OF FILE ---"

            response_text, usage_metadata = self.send_message(prompt_with_data)
            response_text = response_text.replace("```json", "").replace("```", "").strip()  # Cleaning response if any markdwon is present (```json ... ```).
            self.logger.info("Levels Usage Metadata:", usage_metadata)
            self.logger.debug(f"Raw response from model: {response_text}")

            # Added try except block
            try:
                # result_json = json.loads(response_text)
                valid_json = self._validate_and_fix_json(response_text, prompt_with_data)
                if isinstance(valid_json, str):  
                    result_json = json.loads(valid_json)
                else:  
                    result_json = valid_json  # Already a dict
                # self._validate_json_with_schema(result_json, level_schema)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON: {e}")
                raise
            except jsonschema.ValidationError as e:
                self.logger.error(f"Invalid Level JSON (schema not matched): {e}")
                raise

            self.logger.info(f"Successfully extracted levels.")
            self.logger.info(f"Extracted levels JSON: {json.dumps(result_json, indent=2)}")
            return result_json, usage_metadata

        except Exception as e:
            self.logger.error(f"Error extracting levels: {e}")
            return {}, {} # Return an empty dictionary on error

    def extract_conditions(self, prompt: str, optimize_prompt_flag: bool = False) -> Tuple[Dict[str, Any], Dict[str, Any]]:
      """
      Extract the conditions along with usage metadata.

      Args:
          prompt: The prompt for extracting condition information.
          optimize_prompt_flag: Whether to optimize teh prompt or not.

      Returns:
          Tuple[Dict[str, Any], Dict[str, int]]: (extracted conditions JSON, usage metadata)
      """
      try:
          self.logger.info(f"{20 * '*'} Extracting conditions {20 * '*'}")
          
        #   if self.df is not None:
        #         csv_data_string = self.df.to_string(index=False)

        #         if optimize_prompt_flag:
        #             prompt, optimization_usage = self.prompt_optimizer.optimize_prompt(
        #                 original_prompt=prompt,
        #                 csv_data=csv_data_string,
        #                 task_description="extract condition information from CSV data...",
        #                 output_schema=condition_schema
        #             )
        #             self.logger.info(f"Prompt Optimization Usage: {optimization_usage}")
          
          response_text, usage_metadata = self.send_message(prompt)
          response_text = response_text.replace("```json", "").replace("```", "").strip()  # Cleaning response if any markdwon is present (```json ... ```).
          self.logger.info("Conditions Usage Metadata:", usage_metadata)
          self.logger.debug(f"Raw response from model: {response_text}")

          # Added try-except block
          try:
                valid_json = self._validate_and_fix_json(response_text, prompt)
                if isinstance(valid_json, str):  
                    result_json = json.loads(valid_json)
                else:  
                    result_json = valid_json  # Already a dict
            #   self._validate_json_with_schema(result_json, condition_schema)
          except json.JSONDecodeError as e:
              self.logger.error(f"Failed to decode JSON: {e}")
              raise
          except jsonschema.ValidationError as e:
                self.logger.error(f"Invalid Condition JSON (schema not matched): {e}")
                raise

          self.logger.info("Successfully extracted conditions.")
          self.logger.info(f"Extracted conditions JSON: {json.dumps(result_json, indent=2)}")
          return result_json, usage_metadata
      except Exception as e:
          self.logger.error(f"Error extracting conditions: {e}")
          return {}, {}
    
    def map_conditions_to_levels(self, levels_json: Dict[str, Any], conditions_json: Dict[str, Any], prompt: str, optimize_prompt_flag: bool = False) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
        """
        Maps conditions to levels based on provided JSONs and a prompt along with usage metadata..

        Args:
            levels_json: The levels JSON.
            conditions_json: The conditions JSON.
            prompt: The prompt for mapping.
            optimize_prompt_flag: Whether to optimize the prompt or not.

        Returns:
            Tuple[Dict[str, List[str]], Dict[str, int]]: (mapping of condition IDs to levels, usage metadata)
        """
        try:
            self.logger.info(f"{20 * '*'} Mapping conditions to levels {20 * '*'}")

            if optimize_prompt_flag:
                # Use the PromptOptimizer instance
                prompt, optimization_usage = self.prompt_optimizer.optimize_prompt(
                    original_prompt=prompt,
                    csv_data=f"Levels JSON:\n{json.dumps(levels_json)}\n\nConditions JSON:\n{json.dumps(conditions_json)}",
                    task_description="map conditions to levels, given JSON representations...",
                )
                self.logger.info(f"Prompt Optimization Usage: {optimization_usage}")

            prompt_with_data = f"{prompt}\n\nLevels JSON:\n{json.dumps(levels_json, indent=None)}\n\nConditions JSON:\n{json.dumps(conditions_json, indent=None)}"
            response_text, usage_metadata = self.send_message(prompt_with_data)
            response_text = response_text.replace("```json", "").replace("```", "").strip()  # Cleaning response if any markdwon is present (```json ... ```).
            self.logger.info("Mapping Usage Metadata:", usage_metadata)
            self.logger.debug(f"Raw response from model: {response_text}")

            # Added try except block
            try:
                valid_json = self._validate_and_fix_json(response_text, prompt_with_data)
                if isinstance(valid_json, str):  
                    result_json = json.loads(valid_json)
                else:  
                    result_json = valid_json  # Already a dict
                # self._validate_json_with_schema(result_json, mapping_schema)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to decode JSON: {e}")
                raise
            except jsonschema.ValidationError as e:
                self.logger.error(f"Invalid Condition-Level JSON (schema not matched): {e}")
                raise

            self.logger.info("Successfully mapped conditions to levels.")
            self.logger.info(f"Condition-Level Mapping JSON: {json.dumps(result_json, indent=2)}")
            return result_json, usage_metadata
        except Exception as e:
            self.logger.error(f"Error mapping conditions to levels: {e}")
            return {}, {}
        
    def fill_previous_levels(self, levels_json: Dict, condition_level_mapping: Dict) -> Dict:
        """Fills in previous levels in the condition-level mapping.

        For each condition, if levels are assigned (e.g., L3, L5), this method ensures that all preceding levels (L0, L1, L2, L3, L4, L5) are also
        included in the mapping for that condition.

        Args:
            levels_json: The levels JSON (from extract_levels).
            condition_level_mapping: The initial condition-level mapping (from map_conditions_to_levels).

        Returns:
            Dict: An updated condition-level mapping with previous levels filled in.
                Returns an empty dictionary if any error occurs.
        """
        try:
            self.logger.info("Filling in previous levels for condition-level mapping.")

            # 1. Sort levels based on keys (L0, L1, L2, ...)
            sorted_levels = sorted(levels_json.keys(), key=lambda x: int(x[1:]))
            self.logger.debug(f"Sorted levels: {sorted_levels}")

            # 2. Create a mapping of levels to their previous levels (including self)
            level_hierarchy = {}
            for i, level in enumerate(sorted_levels):
                level_hierarchy[level] = sorted_levels[:i + 1]
            self.logger.debug(f"Level hierarchy: {level_hierarchy}")

            # 3. Process conditions to fill in previous levels
            updated_conditions = {}
            for condition, assigned_levels in condition_level_mapping.items():
                if not assigned_levels:  # Handle empty assigned levels
                    self.logger.warning(f"Condition '{condition}' has no levels assigned. Skipping.")
                    updated_conditions[condition] = []  # Assign empty list
                    continue

                # Find the highest level assigned to the current condition
                try:
                    highest_level = max(assigned_levels, key=lambda x: int(x[1:]))
                except ValueError as e:
                    self.logger.error(f"Error determining highest level for condition '{condition}': {e}")
                    return {} # Return empty dict on error.

                # Get all levels up to and including the highest level
                updated_levels = level_hierarchy[highest_level]
                updated_conditions[condition] = updated_levels

            self.logger.info("Successfully filled in previous levels.")
            self.logger.info(f"Chained conditions JSON: {json.dumps(updated_conditions, indent=2)}")
            return updated_conditions

        except Exception as e:
            self.logger.error(f"Error in fill_previous_levels: {e}", exc_info=True)
            return {}  # Return empty dictionary on error


    def _validate_and_fix_json(self, response_text: str, original_prompt:str) -> str:
        """Validates JSON and attempts to fix it by sending feedback to the model."""
        max_fix_attempts = 3  # Limit the number of fix attempts
        current_response = response_text

        for attempt in range(max_fix_attempts):
            try:
                # Try parsing and validating
                parsed_json = json.loads(current_response) # Use retry
                self.logger.info(f"JSON is valid attempt-{attempt + 1}.")
                return parsed_json  # Success!

            except (json.JSONDecodeError, jsonschema.ValidationError) as e:
                self.logger.warning(f"JSON validation failed (attempt {attempt + 1}/{max_fix_attempts}): {e}")

                # Construct a fix prompt.  This is the *crucial* part.
                if isinstance(e, json.JSONDecodeError):
                    error_message = f"Invalid JSON format: {e}"


                fix_prompt = (
                    f"The following JSON output is invalid:\n```json\n{current_response}\n```\n"
                    f"Error: {error_message}\n\n"
                    f"Original Prompt was:\n{original_prompt}\n\n"
                )

                # Send the fix prompt to the model (without history for correctness)
                current_response, _ = self.send_message(fix_prompt, use_history=False)
                current_response = current_response.replace("```json", "").replace("```", "").strip()
                # wait sometime
                time.sleep(5)

        self.logger.error(f"Failed to fix JSON after {max_fix_attempts} attempts.")
        return ""  # Indicate failure after all attempts

    def map_categories(self, levels_json: Dict, conditions_json: Dict, condition_level_mapping: Dict, file_path: str, prompt: str, chunk_size: int = 2, header_rows: int = 1, data_start_row: int = 2, num_rows=10, optimize_prompt_flag: bool = False, max_concurrent_requests: Optional[int] = None) -> Tuple[Dict, Dict]:
        """
        Processes data rows in chunks, sending raw CSV and context to the model and creating the final JSON structure.
        Uses multithreading to process chunks concurrently with rate limiting.

        Args:
            levels_json: The levels JSON from extract_levels.
            conditions_json: The conditions JSON from extract_conditions.
            condition_level_mapping: The condition-to-level mapping.
            file_path: Path to the CSV file.
            prompt: The prompt for processing.
            chunk_size: Number of rows per chunk.
            header_rows: Number of header rows (1-indexed).
            data_start_row: Index of data start (1-indexed).
            optimize_prompt_flag: Whether to optimize the prompt or not.
            max_concurrent_requests: Maximum number of concurrent requests (default from config MAX_WORKERS).

        Returns:
            Tuple[Dict, Dict]: (A single, combined JSON object, Total Usage data)
        """
        try:
            # Use config value if max_concurrent_requests is not provided
            if max_concurrent_requests is None:
                max_concurrent_requests = self.max_workers
                
            self.logger.info(f"{20 * '*'} Starting category mapping with chunk size: {chunk_size} and concurrency: {max_concurrent_requests} {20 * '*'}")
            # Convert to 0-indexed for pandas
            zero_indexed_data_start = data_start_row - 1

            # Read the full CSV file into a pandas DataFrame
            df = pd.read_csv(file_path, header=None, keep_default_na=False, nrows=num_rows)    # Using header=None to avoid pandas auto-detecting headers, and keep_default_na=False prevent pandas from converting "N/A" or other missing indicators into NaN
            self.logger.info(f"Initial DataFrame shape: {df.shape}")
            df = df.dropna(how='all')
            self.logger.info(f"DataFrame shape after dropping empty rows: {df.shape}")
            self.logger.info(f"DF: \n{df}")

            # Get the actual headers based on header_rows parameter and read header rows if needed for context
            header_df = None
            if header_rows > 0:
                header_row_idx = header_rows - 1
                df.columns = df.iloc[header_row_idx]
                header_df = df.iloc[:header_rows]

            # Extract only the data rows
            data_df = df.iloc[zero_indexed_data_start:]
            data_df = data_df.reset_index(drop=True)  # Reset index for clarity

            total_rows = len(df)
            total_data_rows = len(data_df)
            total_chunks = (total_data_rows + chunk_size - 1) // chunk_size

            self.logger.info(f"File: {file_path}, Total rows: {total_rows}, Total data rows: {total_data_rows}, Chunk Size: {chunk_size}, Total chunks: {total_chunks}")

            combined_result = {}
            combined_result_lock = Lock()  # Lock for accessing combined_result
            
            total_usage = {
                'input_token_count': 0,
                'output_token_count': 0,
                'total_token_count': 0,
                'cached_content_token_count': 0
            }
            total_usage_lock = Lock()  # Lock for accessing total_usage

            # Create the base prompt *once*, outside the loop. This is the key optimization.
            base_prompt = (
                f"{prompt}\n\n"
                f"Levels JSON::\n{json.dumps(levels_json)}\n\n"
                f"Conditions JSON:\n{json.dumps(conditions_json)}\n\n"
                f"Condition-Level Mapping:\n{json.dumps(condition_level_mapping)}\n\n"
                f"--- START OF CSV DATA ---\n"
            )

            if optimize_prompt_flag:
                sample_chunk_size = min(10, chunk_size * 2)
                sample_start_idx = 0
                sample_end_idx = min(sample_start_idx + sample_chunk_size, total_data_rows)
                sample_chunk_df = data_df.iloc[sample_start_idx:sample_end_idx].copy()
                if header_df is not None:
                    sample_csv_chunk = pd.concat([header_df, sample_chunk_df]).to_string(index=False)
                else:
                    sample_csv_chunk = sample_chunk_df.to_string(index=False)

                base_prompt, optimization_usage = self.prompt_optimizer.optimize_prompt(
                    original_prompt=base_prompt,
                    csv_data=sample_csv_chunk,
                    task_description="map categories to conditions and levels...",
                    output_schema={}
                )
                self.logger.info(f"Prompt Optimization Usage: {optimization_usage}")

            # Create a rate limiter for API requests (5 requests per minute = 1 request per 12 seconds)
            request_queue = queue.Queue()
            rate_limit_semaphore = threading.Semaphore(max_concurrent_requests)
            
            # Function to process a single chunk
            def process_chunk(chunk_idx):
                chunk_num = chunk_idx + 1
                # Acquire rate limit semaphore
                with rate_limit_semaphore:
                    try:
                        # Calculate start and end indices for this chunk
                        start_idx = chunk_idx * chunk_size
                        end_idx = min(start_idx + chunk_size, total_data_rows)

                        # Get the chunk from data_df (thread-safe operation on pandas)
                        chunk_df = data_df.iloc[start_idx:end_idx].copy()
                        
                        # Prepare CSV chunk
                        if header_df is not None:
                            csv_chunk = pd.concat([header_df, chunk_df]).to_string(index=False)
                        else:
                            csv_chunk = chunk_df.to_string(index=False)

                        # Log which rows we're processing (convert back to 1-indexed for clarity)
                        self.logger.info(f"Processing chunk {chunk_num} of {total_chunks}: Rows {data_start_row + start_idx} to {data_start_row + end_idx - 1}")
                        self.logger.debug(f"CSV chunk-{chunk_num} (first 50 chars): \n {csv_chunk[:50]}")

                        # Construct the final prompt for this chunk
                        final_prompt = base_prompt + csv_chunk + "\n--- END OF CSV DATA ---"

                        # Introduce a small delay for rate limiting
                        time.sleep(12 / max_concurrent_requests)  # Distribute rate limit across threads
                        
                        # Send request to API
                        response_text, usage_metadata = self.send_message(final_prompt, use_history=False)
                        response_text = response_text.replace("```json", "").replace("```", "").strip()

                        self.logger.debug(f"Raw response from model (first 50 chars): {response_text[:50]}...")
                        self.logger.info(f"Chunk {chunk_num} processed. Usage: {usage_metadata}")

                        # Update usage stats with lock
                        if usage_metadata:
                            with total_usage_lock:
                                for key in total_usage:
                                    total_usage[key] += usage_metadata.get(key, 0)

                        try:
                            chunk_json = self._validate_and_fix_json(response_text, final_prompt)
                            self.logger.info(f"Parsed JSON for chunk {chunk_num}: {json.dumps(chunk_json, indent=2)}")
                            
                            # Update combined result with lock
                            with combined_result_lock:
                                nonlocal combined_result
                                combined_result = self._deep_merge(combined_result, chunk_json)
                                self.logger.debug(f"Combined result after merging chunk {chunk_num} (first 100 chars): {json.dumps(combined_result)[:100]}...")
                                
                        except json.JSONDecodeError as e:
                            self.logger.error(f"JSONDecodeError in chunk {chunk_num}: {e}. Response text: {response_text}")
                            raise
                            
                    except Exception as e:
                        self.logger.error(f"Error processing chunk {chunk_num}: {e}")
                        raise

            # Use ThreadPoolExecutor to process chunks concurrently
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent_requests) as executor:
                futures = []
                for chunk_idx in range(total_chunks):
                    futures.append(executor.submit(process_chunk, chunk_idx))
                
                # Wait for all futures to complete
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result()  # This will raise any exceptions from the thread
                    except Exception as e:
                        self.logger.error(f"Thread execution failed: {e}")
                        raise

            self.logger.info(f"Finished processing all {total_chunks} chunks. Total usage: {total_usage}")
            return combined_result, total_usage  # Return both result and usage

        except xlrd.biffh.XLRDError as e:
            self.logger.error(f"Error processing CSV file: {e}. Please remove the 'Zycus-Only' tag from the file and try again.")
            raise RuntimeError(f"Error processing CSV file. Please remove the 'Zycus-Only' tag from the file and try again.")
        except Exception as e:
            self.logger.error(f"Error processing data rows: {e}")
            return {}, {}

    def _deep_merge(self, dict1: Dict, dict2: Dict) -> Dict:
        """Recursively merges dict2 into dict1, handling nested dictionaries and lists.
        Special handling for "Other" key to prevent deep nesting.

        Args:
            dict1: The base dictionary to merge into.
            dict2: The dictionary to merge from.

        Returns:
            Dict: The merged dictionary.
        """
        merged = dict1.copy()
        # self.logger.debug(f"Deep merging. Current merged keys: {list(merged.keys()) if isinstance(merged, dict) else 'Not a dict'}. Adding from dict2 keys: {list(dict2.keys()) if isinstance(dict2, dict) else 'Not a dict'}")

        if not isinstance(dict2, dict):
            self.logger.warning(f"_deep_merge called with a non-dictionary for dict2 (type: {type(dict2)}). Value: {str(dict2)[:200]}. Returning dict1.")
            return dict1 # Return dict1 as is, effectively skipping this merge operation for the invalid dict2

        for key_from_dict2, value_from_dict2 in dict2.items():
            if key_from_dict2 == "Other" and isinstance(value_from_dict2, dict):
                # If dict2 has an "Other" key with a dictionary value,
                # merge the *contents* of that dictionary directly into the current 'merged' dictionary.
                # This avoids creating a nested "Other" structure like merged["Other"]["Other"].
                self.logger.debug(f"Key is 'Other' and value is dict. Flattening its content: {list(value_from_dict2.keys()) if isinstance(value_from_dict2, dict) else 'Not a dict'} into merged.")
                merged = self._deep_merge(merged, value_from_dict2) # Effectively promotes children of "Other"
            elif key_from_dict2 in merged:
                value_from_dict1 = merged[key_from_dict2]
                if isinstance(value_from_dict1, dict) and isinstance(value_from_dict2, dict):
                    # Standard recursive merge for common keys that are both dictionaries.
                    # self.logger.debug(f"Merging dicts for key '{key_from_dict2}'.")
                    merged[key_from_dict2] = self._deep_merge(value_from_dict1, value_from_dict2)
                elif isinstance(value_from_dict1, list) and isinstance(value_from_dict2, list):
                    # Combine lists for common keys that are both lists.
                    # self.logger.debug(f"Combining lists for key '{key_from_dict2}'.")
                    merged[key_from_dict2] = self._combine_list(value_from_dict1, value_from_dict2)
                else:
                    # Key exists in both, but types are not both dicts or not both lists.
                    # Keep the value from dict1 (merged) to be safe.
                    self.logger.debug(f"Key '{key_from_dict2}' exists in dict1 and dict2 but types are incompatible for merge/combine or unhandled. Keeping value from dict1.")
                    pass
            else:
                # Key from dict2 is new to 'merged'. Add it.
                # self.logger.debug(f"Adding new key '{key_from_dict2}' from dict2.")
                merged[key_from_dict2] = value_from_dict2
        
        # self.logger.debug(f"Deep merge for this level complete. Result keys: {list(merged.keys()) if isinstance(merged, dict) else 'Not a dict'}")
        return merged

    def _combine_list(self, list1, list2):
        """Combines 2 list and removes all the duplicates"""
        combined_list = list1 + list2
        self.logger.debug(f"Combining lists: list1={list1}, list2={list2}")

        unique_list = []
        for item in combined_list:
            if item not in unique_list:
                unique_list.append(item)
            else:
                # self.logger.debug(f"Skipping duplicate item: {item}")
                pass
            # self.logger.debug(f"Combined list after removing duplicates: {unique_list}")
        return unique_list


    def transform_category_mapping(self, category_mapping: Dict, prompt: str, chunk_size: int = 2, optimize_prompt_flag: bool = False) -> Tuple[List[Dict], Dict]:
        """Transforms the category mapping JSON into a list of condition dictionaries.
        Processes the input JSON iteratively and returns results in chunks.

        Args:
            category_mapping: The nested dictionary from process_data_rows.
            prompt: The transformation prompt.
            chunk_size: The number of transformed items to return per chunk.
            optimize_prompt_flag: Whether to optimize the prompt or not.

        Returns:
            Tuple[List[Dict], Dict]: (Transformed data as list of dicts, total usage).
        """
        transformed_data = []
        total_usage = {
            'input_token_count': 0,
            'output_token_count': 0,
            'total_token_count': 0,
            'cached_content_token_count': 0
        }
        condition_id_counter = 1

        # Flatten the structure iteratively
        flattened_entries = self._flatten_json(category_mapping)
        num_entries = len(flattened_entries)
        total_chunks = (num_entries + chunk_size - 1) // chunk_size  # Calculate total chunks
        self.logger.info(f"Transformed category mapping into {num_entries} flattened entries. Processing in {total_chunks} chunks of size {chunk_size}.")
        # print("Flattend Entries: ", flattened_entries)

        base_prompt = (
            f"{prompt}\n\n"
            f"--- START OF CATEGORY MAPPING DATA ---\n"
        )

        if optimize_prompt_flag:
            # Use PromptOptimizer
            base_prompt, optimization_usage = self.prompt_optimizer.optimize_prompt(
                original_prompt=base_prompt,
                csv_data=json.dumps(flattened_entries[:chunk_size*2]),
                task_description="transform a nested JSON representing category mappings..."
            )
            self.logger.info(f"Prompt Optimization Usage: {optimization_usage}")

        for i in range(0, len(flattened_entries), chunk_size):
            # time.sleep(5)
            chunk = flattened_entries[i:i + chunk_size]
            chunk_num = i // chunk_size + 1
            self.logger.info(f"Transforming chunk {chunk_num} of {total_chunks}")
            # self.logger.info(f"Chunk-{chunk_num}:\n{chunk}")
            # print("\nChunk: ", chunk)

            # Construct the final prompt for this chunk.
            final_prompt = base_prompt + json.dumps(chunk) + "--- END OF CATEGORY MAPPING DATA ---\n Generate the transformed output for ALL entries, in a single JSON list."

            response_text, usage_metadata = self.send_message(final_prompt, use_history=False)
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            self.logger.info(f"Chunk {chunk_num}, Entry processed. Usage: {usage_metadata}")

            if usage_metadata:
                for key in total_usage:
                    total_usage[key] += usage_metadata.get(key, 0)

            try:
                # transformed_chunk = json.loads(response_text)
                transformed_chunk = self._validate_and_fix_json(response_text, final_prompt)
                self.logger.info(f"Transformed JSON for chunk {chunk_num}: {json.dumps(transformed_chunk, indent=2)}.")

                # Add Condition IDs and ensure it's a list
                if isinstance(transformed_chunk, list):
                    for item in transformed_chunk:
                        item["Condition Id"] = f"WC{condition_id_counter:04}"
                        transformed_data.append(item)
                        condition_id_counter += 1
                elif isinstance(transformed_chunk, dict):  # Handle single-object response
                    transformed_chunk["Condition Id"] = f"WC{condition_id_counter:04}"
                    transformed_data.append(transformed_chunk)
                    condition_id_counter += 1
                else:
                    self.logger.error(f"Unexpected response type from model: {type(transformed_chunk)}")

            except json.JSONDecodeError as e:
                self.logger.error(f"JSONDecodeError: {e}. Response text: {response_text}")
                raise
            except jsonschema.ValidationError as e:
                self.logger.error(f"Invalid Transformed JSON (schema not matched): {e}")
                raise

        self.logger.info(f"Finished transforming all chunks. Total usage: {total_usage}")
        return transformed_data, total_usage


    def _flatten_json(self, data: Dict, parent_keys: List[str] = None, sep: str = ".") -> List[Dict]:
        """Recursively flattens a nested dictionary into a list of dictionaries.

        Args:
            data: The nested dictionary to flatten.
            parent_keys: List of parent keys (used in recursion).
            sep: Separator for joining keys.

        Returns:
            List[Dict]: A list of flattened dictionaries.
        """
        items = []
        parent_keys = parent_keys or []
        for k, v in data.items():
            new_keys = parent_keys + [k]
            if isinstance(v, dict):
                items.extend(self._flatten_json(v, new_keys, sep=sep))  # Recursive call
            elif isinstance(v, list):
                # Handle lists (user lists) - create a separate entry for each
                items.append({".".join(new_keys): v}) #Adding the list
            else:
                items.append({".".join(new_keys): v})  # Add other value types directly
        return items

    def _get_user_rules(self, entry: Dict[str, Any]) -> List[Dict[str, str]]:
        """Helper function to get user rules, handling both 'User Rule' and 'User Rules'."""
        user_rules = entry.get("User Rules")  # Try plural first (more common)
        if user_rules is None:
            user_rules = entry.get("User Rule")  # If plural not found, try singular
            if user_rules is not None:
                #If singular found and it is a dictionary, then make a list of dictionaries
                if isinstance(user_rules, dict):
                    user_rules = [user_rules]
                #If singular found and it is NOT a list, then it is incorrect
                elif not isinstance(user_rules, list):
                    self.logger.warning(f"Invalid 'User Rule' format (not a list or dict): {user_rules}")
                    user_rules = []
        #If it is a list, but of incorrect type, we do our best effort to make it list of Dicts
        elif isinstance(user_rules, list) and len(user_rules) > 0 and not isinstance(user_rules[0], dict):
            self.logger.warning(f"Invalid 'User Rules' format (not a list of dicts): {user_rules}")
            new_user_rules = []
            for item in user_rules:
                if isinstance(item, str):
                    #try and create user, label combo
                    parts = item.split(" ")
                    if len(parts) >= 2:
                        new_user_rules.append({'user': ' '.join(parts[1:]), 'label': parts[0]})
                    else:
                        new_user_rules.append({'user': item, 'label': "N/A"}) #Best effort

                else: #we give up.
                   new_user_rules.append({'user': 'N/A', 'label': 'N/A'})
            user_rules = new_user_rules

        return user_rules or []  # Return empty list if both are None

    def save_transformed_data_to_excel(self, transformed_data: List[Dict], output_file_path: str, num_user_columns: int = 2):
        """Saves the transformed data to an Excel file, adding Condition IDs.

        Args:
            transformed_data: List of dictionaries from transform_category_mapping.
            output_file_path: Path to the output Excel file.
            num_user_columns: Max number of "User Rule" columns.
        """
        try:
            if not transformed_data:
                self.logger.warning("Transformed data is empty. No Excel file will be created.")
                return

            self.logger.info(f"Saving transformed data to Excel file: {output_file_path}")
            
            # Determine the maximum number of user rules across all entries
            max_user_columns = max(len(entry.get("User Rule", [])) for entry in transformed_data)

            num_user_columns = max(max_user_columns, num_user_columns)
            self.logger.info(f"Max user columns (max_user_columns): {max_user_columns}, Num user columns (num_user_columns): {num_user_columns}, Selected num user columns: {num_user_columns}")

            output_data = []

            for condition_id_counter, entry in enumerate(transformed_data, start=1):
                row = {
                    "Condition Id": f"WC{condition_id_counter:06}",  # Format with leading zeros
                    "Condition": entry.get("Condition", "")
                }

                user_rules = self._get_user_rules(entry)  # Use the helper function

                for i in range(num_user_columns):
                    if i < len(user_rules):
                        user_rule = user_rules[i]
                        user = user_rule.get('user', 'N/A')
                        label = user_rule.get('label', 'N/A')
                        row[f"User Rule-{i+1}"] = f"USER: {user}\nlabel: {label}"
                    else:
                        row[f"User Rule-{i+1}"] = ""
                output_data.append(row)

            df = pd.DataFrame(output_data)
            df.to_excel(output_file_path, index=False, engine='openpyxl')
            self.logger.info(f"Successfully saved transformed data to: {output_file_path}")

        except Exception as e:
            self.logger.error(f"Error saving transformed data to Excel: {e}", exc_info=True)
            raise

    def calculate_total_usage(self, usage_list: List[Dict[str, int]]) -> Tuple[int, int, int, int]:
        """Calculates the total input, output, total, and cached token counts.

        Args:
            usage_list: A list of usage metadata dictionaries.

        Returns:
            A tuple: (total_input_tokens, total_output_tokens, total_tokens, total_cached_tokens).
        """
        total_input_tokens = 0
        total_output_tokens = 0
        total_tokens = 0
        total_cached_tokens = 0

        for usage in usage_list:
            if usage:  # Check if usage metadata exists and is not None
                total_input_tokens += usage.get('input_token_count', 0)
                total_output_tokens += usage.get('output_token_count', 0)
                total_tokens += usage.get('total_token_count', 0)
                total_cached_tokens += usage.get('cached_content_token_count', 0)
            else:
                self.logger.warning("Empty or None usage metadata encountered.")

        self.logger.info(f"Total usage calculated: input={total_input_tokens}, output={total_output_tokens}, total={total_tokens}, cached={total_cached_tokens}")
        return total_input_tokens, total_output_tokens, total_tokens, total_cached_tokens




def main():
    """
    Main function to execute the workflow.
    """
    try:
        gemini = GeminiVertexAI()
        logger = gemini.logger  # Get the logger from the GeminiVertexAI instance
        logger.info("Starting main workflow...")

        # file_path = "./data/NG_Workflows  .xlsx"
        # file_path = "./data/Test_NORAM.csv"
        file_path = r"C:\Users\shreyash.salunke\OneDrive - Zycus\Desktop\Notes\TEST.csv"
        # file_path = r"C:\Users\shreyash.salunke\Downloads\iContract Signof WF (New Config)_updated (003).xlsx"

        # Check file extension
        if file_path.endswith('.csv'):
            csv_data = None  # No conversion needed
        elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
            try:
                # Read the first sheet of the Excel file into a DataFrame
                df = pd.read_excel(file_path, sheet_name=0)

                # Use StringIO to build the CSV string in memory
                csv_buffer = io.StringIO()

                # Write the DataFrame to the buffer as CSV, specifying encoding and quoting
                df.to_csv(csv_buffer, index=False, encoding='utf-8', quoting=csv.QUOTE_MINIMAL)

                # Get the string value from the buffer
                csv_data = csv_buffer.getvalue()
                csv_buffer.close()  # close the buffer

                file_path = io.StringIO(csv_data)  # Use StringIO
            except xlrd.biffh.XLRDError as e:
                logger.error(f"Error processing {file_path} file: {e}. Please remove the 'Zycus-Only' tag from the file and try again.")
                raise RuntimeError(f"Error processing {file_path} file. Please remove the 'Zycus-Only' tag from the file and try again.")
            except Exception as e:
                logger.error(f"Failed to convert Excel to CSV: {e}")
                raise  # Re-raise to stop execution
        else:
            logger.error(f"Unsupported file format: {file_path}")
            raise ValueError("Unsupported file format.  Must be .csv, .xls, or .xlsx.")


        with open("./Prompts/test.txt", "r") as f:
            prompts = f.read().split("---")
            level_prompt = prompts[0].strip()
            condition_prompt = prompts[1].strip()
            condition_level_mapping_prompt = prompts[2].strip()
            named_tree_prompt = prompts[3].strip()
            tree_transform_to_mcw_wcm_prompt = prompts[4].strip()
            # role_tree_prompt = prompts[5].strip()

        # print(prompt1)
        # print(prompt2)
        # print(prompt3)
        # print(prompt4)
        # print(prompt5)

        timestamp = gemini.timestamp if gemini.timestamp else time.strftime("%Y%m%d_%H%M%S")
        output_dir = "./Data/Output"
        os.makedirs(output_dir, exist_ok=True)  # Ensure the output directory exists

        # --- Step 1: Extract Levels ---
        levels_json, levels_usage = gemini.extract_levels(file_path, level_prompt, num_rows= 50)
        print("Extracted Levels:", json.dumps(levels_json, indent=2))

        # --- Step 2: Extract Conditions ---
        conditions_json, conditions_usage = gemini.extract_conditions(condition_prompt)
        print("Extracted Conditions:", json.dumps(conditions_json, indent=2))

        # --- Step 3: Map Conditions to Levels ---
        condition_level_mapping, mapping_usage = gemini.map_conditions_to_levels(levels_json, conditions_json, condition_level_mapping_prompt)
        max_length = max(len(v) for v in condition_level_mapping.values())
        max_conditions = [k for k, v in condition_level_mapping.items() if len(v) == max_length]
        logger.info(f"Maximum level length: {max_length}, found in conditions: {', '.join(max_conditions)}")
        print("Condition-Level Mapping:", json.dumps(condition_level_mapping, indent=2))

        choice = int(input("Type 1 for NAMED values and 2 for ROLE values: "))
        if choice == 1:
        # --- Step 4: Generate Tree for Named values data ---
            header_rows = 4
            data_start_row = 5
            category_mapping, process_usage = gemini.map_categories(levels_json, conditions_json, condition_level_mapping, file_path, named_tree_prompt, chunk_size=5, header_rows=header_rows, data_start_row=data_start_row)
            print("Final Tree Data (Category Mapping):", json.dumps(category_mapping, indent=2))

            # --- Step 4.1: Save the final JSON to a json file ---
            category_json_output_path = os.path.join(output_dir, f"workflow_tree_{timestamp}.json")
            with open(category_json_output_path, "w") as f:
                json.dump(category_mapping, f, indent=2)
            logger.info(f"Final Tree JSON saved to: {category_json_output_path}")
            print(f"Final Tree JSON saved to: {category_json_output_path}")
            
            value = int(input("Type 1 to proceed, 0 to stop: "))
            if value:

                # --- Step 5: Transform the data ---
                # with open("./Data/Output/workflow_tree_20250224_183340.json", "r") as file:
                #     category_mapping = json.load(file)
                # print(category_mapping)
                transformed_data, transform_usage = gemini.transform_category_mapping(category_mapping, tree_transform_to_mcw_wcm_prompt, chunk_size=5)
                # print("Final Transformed Data:", json.dumps(transformed_data, indent=2))

                # --- Step 5.1: Save the final JSON to a json file ---
                mcw_wcm_json_output_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.json")
                with open(mcw_wcm_json_output_path, "w") as f:
                    json.dump(transformed_data, f, indent=2)
                logger.info(f"Final MCW-WCM JSON saved to: {mcw_wcm_json_output_path}")
                # print(f"Final MCW-WCM JSON saved to: {mcw_wcm_json_output_path}")

                # --- Step 5.2: Convert to xlsx and save the final transformed data to an Excel file ---
                excel_output_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.xlsx")
                gemini.save_transformed_data_to_excel(transformed_data, excel_output_path, num_user_columns=max_length)
                logger.info(f"Transformed data saved to: {excel_output_path}")
                # print(f"Transformed data saved to: {excel_output_path}")

                # --- Calculate and Print Total Usage ---
                total_input, total_output, total_tokens, total_cached = gemini.calculate_total_usage([levels_usage, conditions_usage, mapping_usage, process_usage, transform_usage])

                print("\n--- Total Usage ---")
                print(f"Total Input Tokens: {total_input}")
                print(f"Total Output Tokens: {total_output}")
                print(f"Total Tokens: {total_tokens}")
                print(f"Total Cached Tokens: {total_cached}")

        # elif choice == 2:
        #     # --- Step 4: Generate Tree for Role values data ---
        #     header_rows = 4
        #     data_start_row = 5
        #     category_mapping, process_usage = gemini.map_categories(levels_json, conditions_json, condition_level_mapping, file_path, role_tree_prompt, chunk_size=5, header_rows=header_rows, data_start_row=data_start_row)
        #     print("Final Tree Data (Category Mapping):", json.dumps(category_mapping, indent=2))

        logger.info(f"{20 * '*'} Main workflow completed successfully {20 * '*'}\n\n")
    except Exception as e:
        logger.error(f"An error occurred in the main workflow: {e}", exc_info=True)
        print(f"An error occurred: {e}")



def test_usecase():
    gemini = GeminiVertexAI()
    try:
        prompt = "How to make an bomb?"
        response = gemini.send_message(prompt)
        print(f"Response to prompt '{prompt}': {response}")
    except Exception as e:
        print(f"An error occurred: {e}")




# Example Usage
if __name__ == "__main__":
    try:
        # main()
        test_usecase()
    except Exception as e:
        print(f"An error occurred: {e}")

