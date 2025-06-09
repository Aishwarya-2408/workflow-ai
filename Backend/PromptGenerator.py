import configparser
import os
import time
import pandas as pd
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Part,
    Content,
    GenerationConfig,
)
from vertexai.generative_models import HarmCategory, HarmBlockThreshold
from typing import Dict, Any, Optional, List, Tuple

# Assuming utility exists as in the original code
# If not, replace with standard Python logging
try:
    from utility import get_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    get_logger = logging.getLogger

# --- Helper Class for Vertex AI Interaction ---
class _VertexAIHelper:
    """Internal helper class to manage Vertex AI API calls."""

    def __init__(self, config_file_path: str = "configuration.ini"):
        self.logger = get_logger()
        self.config_file_path = config_file_path
        self.config = configparser.ConfigParser()
        self.model = None
        self.generation_config = None
        self.safety_settings = None

        self.logger.info(f"Initializing _VertexAIHelper with config: {config_file_path}")
        try:
            if not os.path.exists(self.config_file_path):
                self.logger.error(f"Config file not found: {self.config_file_path}")
                raise FileNotFoundError(f"Config file not found: {self.config_file_path}")

            self.config.read(self.config_file_path)
            self._validate_config()
            self._load_config()
            self._initialize_model()
            self.logger.info("_VertexAIHelper initialized successfully.")

        except (FileNotFoundError, ValueError, configparser.Error) as e:
            self.logger.error(f"Initialization error for _VertexAIHelper: {e}")
            raise

    def _validate_config(self):
        self.logger.debug("Validating _VertexAIHelper configuration...")
        if not self.config.has_section("GEMINI"):
            raise ValueError("Missing required section in config file: GEMINI")

        required_keys = [
            "GOOGLE_APPLICATION_CREDENTIALS", "MODEL_NAME", "TEMPERATURE",
            "TOP_P", "TOP_K", "PROJECT_ID"
        ]
        for key in required_keys:
            if not self.config.has_option("GEMINI", key):
                raise ValueError(f"Missing required key '{key}' in section 'GEMINI'")

        creds_path = self.config.get("GEMINI", "GOOGLE_APPLICATION_CREDENTIALS")
        if not os.path.exists(creds_path):
            raise ValueError(f"GOOGLE_APPLICATION_CREDENTIALS file not found: {creds_path}")
        self.logger.debug("Configuration validation successful.")

    def _load_config(self):
        try:
            gemini_config = self.config["GEMINI"]
            self.logger.debug("Loading configuration from GEMINI section.")

            # Set environment variable for credentials
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gemini_config.get("GOOGLE_APPLICATION_CREDENTIALS")

            self.project_id = gemini_config.get("PROJECT_ID")
            self.location = gemini_config.get("LOCATION", "us-central1") # Default location
            self.model_name = gemini_config.get("MODEL_NAME")

            self.generation_config = GenerationConfig(
                temperature=float(gemini_config.get("TEMPERATURE")),
                top_p=float(gemini_config.get("TOP_P")),
                top_k=int(gemini_config.get("TOP_K")),
                max_output_tokens=int(gemini_config.get("MAX_OUTPUT_TOKENS", 8192)) # Default max tokens
            )
            self.safety_settings = self._get_safety_settings()

            self.logger.info(f"Loaded config: project={self.project_id}, location={self.location}, model={self.model_name}")

        except (ValueError, KeyError, configparser.Error) as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise

    def _get_safety_settings(self) -> Dict[HarmCategory, HarmBlockThreshold]:
        """Processes and returns the safety settings from configuration.ini."""
        safety_settings = {}
        if self.config.has_section("SAFETY_SETTINGS"):
            self.logger.debug("Processing safety settings...")
            for key, value in self.config.items("SAFETY_SETTINGS"):
                try:
                    harm_category = HarmCategory[key.upper()]
                    harm_threshold = HarmBlockThreshold[value.upper()]
                    safety_settings[harm_category] = harm_threshold
                except KeyError:
                    self.logger.warning(f"Invalid safety setting: {key}={value}. Skipping.")
        else:
            self.logger.warning("No SAFETY_SETTINGS section found. Using defaults.")

        # Apply defaults if section missing or empty
        defaults = {
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            # HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE, # Often BLOCK_NONE
        }
        for category, threshold in defaults.items():
            if category not in safety_settings:
                 safety_settings[category] = threshold

        self.logger.debug(f"Final safety settings: {safety_settings}")
        return safety_settings

    def _initialize_model(self):
        try:
            vertexai.init(project=self.project_id, location=self.location)
            self.logger.info(f"Initialized Vertex AI SDK for project: {self.project_id} in {self.location}")
            # System instruction can be added here if needed for the generator specifically
            self.model = GenerativeModel(self.model_name)
            self.logger.info(f"GenerativeModel initialized with model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Error initializing Vertex AI model: {e}")
            raise

    def send_single_prompt(self, prompt: str) -> str:
        """Sends a single prompt to the Vertex AI model and returns the text response."""
        if not self.model:
            self.logger.error("Model not initialized.")
            raise RuntimeError("Vertex AI Model is not initialized.")

        self.logger.info("Sending prompt to Vertex AI...")
        self.logger.debug(f"Prompt (first 100 chars): {prompt[:100]}...")

        try:
            # Use generate_content for single-turn requests
            response = self.model.generate_content(
                contents=[prompt], # Prompt should be part of the contents list
                generation_config=self.generation_config,
                safety_settings=self.safety_settings,
                stream=False,
            )

            self.logger.info("Received response from Vertex AI.")
            # Basic check if response has text
            if response and response.candidates and response.candidates[0].content.parts:
                 response_text = response.candidates[0].content.parts[0].text
                 self.logger.debug(f"Response text (first 100 chars): {response_text[:100]}...")
                 return response_text
            else:
                 self.logger.warning("Received an empty or unexpected response structure from Vertex AI.")
                 return "" # Return empty string for unexpected response

        except Exception as e:
            self.logger.error(f"Error during Vertex AI API call: {e}")
            # Consider more specific error handling based on potential API errors
            raise RuntimeError(f"Failed to get response from Vertex AI: {e}")


# --- Main Prompt Generator Class ---
class PromptGenerator:
    """
    Generates multi-stage prompt files for workflow standardization
    using Vertex AI, based on user instructions and sample data.
    """
    DEFAULT_OUTPUT_DIR = "./GeneratedPrompt"
    EXAMPLE_PROMPT_FILES = [
        "danone_with_chain_prompt.txt",
        "mufg_fs_with_chain_prompt.txt",
        "mufg_iContract_with_chain_prompt.txt",
        "mufg_qs_publish_with_chain_prompt.txt",
        "rlc_with_chain_prompt.txt",
        "rest_with_chain_prompt.txt",
    ]

    def __init__(
        self,
        project_name: str,
        user_instructions: str,
        dataframe: Optional[pd.DataFrame] = None, # Make dataframe optional
        config_file_path: str = "configuration.ini",
        example_prompt_dir: str = "./", # Directory containing example txt files
    ):
        """
        Initializes the PromptGenerator.

        Args:
            project_name: Name of the project (used for output filename).
            user_instructions: Natural language instructions from the user.
            dataframe: Optional Pandas DataFrame containing sample data for context.
            config_file_path: Path to the Vertex AI configuration file.
            example_prompt_dir: Directory where example prompt .txt files are located.
        """
        self.logger = get_logger()
        if not project_name:
            raise ValueError("Project name cannot be empty.")
        if not user_instructions:
            raise ValueError("User instructions cannot be empty.")

        self.project_name = project_name
        self.user_instructions = user_instructions
        self.dataframe = dataframe
        self.output_dir = self.DEFAULT_OUTPUT_DIR
        self.example_prompt_dir = example_prompt_dir

        self.logger.info(f"Initializing PromptGenerator for project: {self.project_name}")
        self.logger.info(f"Looking for example prompts in: {os.path.abspath(self.example_prompt_dir)}")

        # Ensure output directory exists
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            self.logger.info(f"Output directory set to: {self.output_dir}")
        except OSError as e:
            self.logger.error(f"Failed to create output directory {self.output_dir}: {e}")
            raise

        # Initialize Vertex AI helper
        self.ai_helper = _VertexAIHelper(config_file_path)

        # Load example prompts
        self.example_prompts = self._load_example_prompts()
        if not self.example_prompts:
            self.logger.warning(f"No example prompt files found in {self.example_prompt_dir}. Prompt generation quality may be affected.")


    def _load_example_prompts(self) -> Dict[str, str]:
        """Loads content from specified example prompt files."""
        loaded_prompts = {}
        self.logger.info(f"Loading example prompts from: {self.example_prompt_dir}")
        for filename in self.EXAMPLE_PROMPT_FILES:
            filepath = os.path.join(self.example_prompt_dir, filename)
            try:
                if os.path.exists(filepath):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        loaded_prompts[filename] = f.read()
                    self.logger.debug(f"Successfully loaded example prompt: {filename}")
                else:
                    self.logger.warning(f"Example prompt file not found: {os.path.abspath(filepath)}")
            except Exception as e:
                self.logger.error(f"Failed to read example prompt file {filepath}: {e}")
        return loaded_prompts

    def _prepare_context(self, max_rows: int = 50) -> str:
        """Prepares the data context string from the DataFrame."""
        if self.dataframe is None or self.dataframe.empty:
            self.logger.info("No DataFrame provided or DataFrame is empty. No data context will be used.")
            return "N/A - No sample data provided."

        self.logger.info(f"Preparing data context string from DataFrame (max {max_rows} rows).")
        # Select top rows and convert to string
        context_df = self.dataframe.head(max_rows)
        try:
            # Using to_string for better visual representation in the prompt
            context_string = context_df.to_string(index=False, na_rep='N/A')
            self.logger.debug(f"Data context string generated (first 100 chars): {context_string[:100]}...")
            return context_string
        except Exception as e:
            self.logger.error(f"Failed to convert DataFrame to string: {e}")
            return "Error: Failed to generate data context string."

    def _construct_master_prompt(self, data_context_string: str) -> str:
        """Constructs the main prompt to be sent to the LLM."""
        self.logger.info("Constructing the master prompt for the LLM.")

        example_section = "\n\n".join(
            f"--- START OF EXAMPLE ({filename}) ---\n{content}\n--- END OF EXAMPLE ({filename}) ---"
            for filename, content in self.example_prompts.items()
        )

        # This is the core instruction prompt for the LLM
        master_prompt = f"""
You are an AI assistant specialized in generating structured prompt files for a workflow standardization application.
This application processes tabular data (like from Excel sheets) in four distinct stages. Each stage requires a specific prompt.
Your task is to generate a single text output containing exactly four prompts, separated by '---'.

**Objective:** Create a prompt file tailored to the user's specific needs described below, using their sample data for context regarding column names, data types, and structure. The generated prompts should follow the style, structure, and level of detail demonstrated in the provided examples, but the *content* must be specific to the current user's request.

**User Instructions:**
{self.user_instructions}

**Sample Data Context (representative rows):**
--- START OF DATA ---
{data_context_string}
--- END OF DATA ---

**Examples of Prompt File Structures (from other projects for style reference ONLY):**
{example_section}

**Your Task:**
1.  Carefully analyze the **User Instructions** and the **Sample Data Context**.
2.  Identify the key elements needed for each of the four processing stages (typically: Level Extraction, Condition Extraction, Condition-Level Mapping, Hierarchical JSON Generation).
3.  Generate four distinct prompts based *only* on the **User Instructions** and **Sample Data Context**.
4.  Ensure the prompts use the actual column names and reflect the logic described in the User Instructions.
5.  Format the output as a single block of text, with each of the four generated prompts separated by a line containing only '---'.
6.  **CRITICAL:** Do NOT include any introductory text, concluding remarks, or explanations outside of the four prompts themselves. The output must start directly with the first prompt and end directly after the fourth prompt.

Generate the four prompts now:
"""
        self.logger.debug("Master prompt constructed.")
        return master_prompt.strip() # Remove leading/trailing whitespace

    def generate_prompt_file(self) -> str:
        """
        Generates the multi-stage prompt file and saves it.

        Returns:
            The path to the generated prompt file.

        Raises:
            RuntimeError: If prompt generation fails.
        """
        self.logger.info(f"Starting prompt file generation for project: {self.project_name}")

        # 1. Prepare data context
        data_context = self._prepare_context()

        # 2. Construct the master prompt
        master_prompt = self._construct_master_prompt(data_context)

        # 3. Send prompt to Vertex AI
        try:
            generated_prompts_text = self.ai_helper.send_single_prompt(master_prompt)
            # Basic validation: Check if the separator exists
            if '---' not in generated_prompts_text:
                 self.logger.warning("Generated text does not contain the '---' separator. The LLM might not have followed instructions correctly.")
                 # Decide if you want to raise an error or proceed cautiously
                 # raise RuntimeError("Generated prompt text format is invalid (missing '---').")

            # Optional: Clean up potential markdown code fences if the model adds them
            generated_prompts_text = generated_prompts_text.strip()
            if generated_prompts_text.startswith("```") and generated_prompts_text.endswith("```"):
                generated_prompts_text = generated_prompts_text[3:-3].strip()


        except Exception as e:
            self.logger.error(f"Failed to generate prompts via Vertex AI: {e}")
            raise RuntimeError(f"Prompt generation failed: {e}")

        # 4. Save the generated prompts
        output_filename = f"{self.project_name}_prompt.txt"
        output_filepath = os.path.join(self.output_dir, output_filename)

        try:
            with open(output_filepath, 'w', encoding='utf-8') as f:
                f.write(generated_prompts_text)
            self.logger.info(f"Successfully generated and saved prompt file: {output_filepath}")
            return output_filepath
        except IOError as e:
            self.logger.error(f"Failed to save generated prompt file to {output_filepath}: {e}")
            raise RuntimeError(f"Failed to save prompt file: {e}")

# --- Example Usage ---
if __name__ == "__main__":
    print("Starting Prompt Generator Utility Example...")

    # 1. Define User Inputs
    project = "SampleProject_DanoneStyle"
    instructions = """
    Generate prompts for a Danone-like approval workflow.
    The data contains procurement information with Regions (NORAM, EMEA), Direct/Indirect classification,
    Categories (like 'PACKAGING MATERIALS - Packaging', 'RAW MATERIALS - FOOD'), SubCategories (like 'BRICKS', 'BIG BAGS'),
    and user details (email, name).

    The goal is to create a hierarchical JSON output mapping these levels to approval conditions based on contract values and durations.
    - Stage 1: Extract the approval levels (L0, L1, L2, etc.) with descriptions based on roles like 'C&P CBU Director', 'VP Procurement', etc. L0 is lowest.
    - Stage 2: Extract unique conditions like 'Yearly contract value: 0-3 million', 'All contracts >5M and >2Y', 'All contracts >5Y'. Handle ranges and combined criteria.
    - Stage 3: Map the extracted conditions to the appropriate levels (e.g., condition1 maps to L0, condition2 maps to L1 and L2). Be careful with combined conditions.
    - Stage 4: Generate the final hierarchical JSON: Region -> Direct/Indirect -> Category -> SubCategory -> {condition_description: [ {user: email, label: name}, ... ]}. Use 'N/A' for missing data. Ensure correct JSON syntax, especially commas in user arrays. Chaining is enabled (higher levels include lower level approvers implicitly based on mapping).
    Use the provided sample data for column names and context.
    """

    # 2. Create Sample DataFrame (or load from Excel)
    # In a real scenario, load this from the user's Excel file:
    # df = pd.read_excel("path/to/user_file.xlsx", sheet_name="Sheet1")
    data = {
        'Region': ['NORAM', 'NORAM', 'EMEA', 'NORAM', 'EMEA'],
        'Direct/Indirect': ['Direct', 'Direct', 'Indirect', 'Direct', 'Direct'],
        'Category': ['PACKAGING MATERIALS - Packaging', 'PACKAGING MATERIALS - Packaging', 'SERVICES - IT', 'RAW MATERIALS - FOOD', 'RAW MATERIALS - FOOD'],
        'SubCategory': ['BRICKS', 'BIG BAGS', 'Software Licensing', 'Milk Powder', 'Sugar'],
        'Approver L0 Email': ['user0_l0@danone.com', 'user0_l0@danone.com', 'user0_l0_emea@danone.com', 'user0_l0@danone.com', 'user0_l0_emea@danone.com'],
        'Approver L0 Name': ['C&P CBU Director A', 'C&P CBU Director B', 'C&P CBU Director C', 'C&P CBU Director D', 'C&P CBU Director E'],
        'Approver L1 Email': ['user1_l1@danone.com', 'user1_l1@danone.com', 'user1_l1_emea@danone.com', 'user1_l1@danone.com', 'user1_l1_emea@danone.com'],
        'Approver L1 Name': ['VP Procurement Ops 1', 'VP Procurement Ops 2', 'VP Procurement Ops 3', 'VP Procurement Ops 4', 'VP Procurement Ops 5'],
        'Approver L2 Email': ['user2_l2@danone.com', 'user2_l2@danone.com', 'user2_l2_emea@danone.com', 'user2_l2@danone.com', 'user2_l2_emea@danone.com'],
        'Approver L2 Name': ['CPO', 'CPO', 'CPO EMEA', 'CPO', 'CPO EMEA'],
        'Contract Value Yearly (M)': [2.5, 6, 0.5, 15, 30],
        'Contract Duration (Y)': [1, 3, 1, 4, 6]
    }
    sample_df = pd.DataFrame(data)
    print("\nSample DataFrame created:")
    print(sample_df.head())

    # 3. Ensure configuration.ini and example prompts exist
    # Make sure 'configuration.ini' is in the same directory or provide the correct path.
    # Make sure the example .txt files (danone_with_chain_prompt.txt, etc.) are in the current directory (or specify example_prompt_dir).
    config_path = "configuration.ini"
    example_dir = "./prompts - Copy" # Assuming example prompts are in the current directory

    if not os.path.exists(config_path):
        print(f"\nERROR: Configuration file '{config_path}' not found. Please create it.")
        exit()
    # Check for at least one example prompt file
    if not any(os.path.exists(os.path.join(example_dir, fname)) for fname in PromptGenerator.EXAMPLE_PROMPT_FILES):
         print(f"\nWARNING: No example prompt files found in '{example_dir}'. Proceeding without examples.")


    # 4. Instantiate and Run the Generator
    try:
        print(f"\nInstantiating PromptGenerator for project '{project}'...")
        generator = PromptGenerator(
            project_name=project,
            user_instructions=instructions,
            dataframe=sample_df,
            config_file_path=config_path,
            example_prompt_dir=example_dir
        )

        print("\nGenerating prompt file...")
        generated_file_path = generator.generate_prompt_file()
        print(f"\nPrompt file generation complete. File saved to: {generated_file_path}")

        # Optional: Print the content of the generated file
        # with open(generated_file_path, 'r') as f:
        #     print("\n--- Content of Generated File ---")
        #     print(f.read())
        #     print("--- End of File Content ---")

    except (ValueError, FileNotFoundError, RuntimeError, configparser.Error, Exception) as e:
        print(f"\nAn error occurred: {e}")
    except ImportError as e:
         print(f"\nImport Error: {e}. Make sure necessary libraries (pandas, google-cloud-aiplatform) are installed.")