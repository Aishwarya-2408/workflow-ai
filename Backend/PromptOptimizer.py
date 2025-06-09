# prompt_optimizer.py
import json
import logging
import time
from typing import Dict, Any, Tuple, Optional

from vertexai.generative_models import GenerativeModel, Part, Content
from vertexai.generative_models import HarmCategory, HarmBlockThreshold
import vertexai
import os


class PromptOptimizer:
    """
    Optimizes prompts using a dedicated language model, and tracks usage.
    """

    def __init__(self, logger, config):  # Removed gemini_instance
        """
        Initializes the PromptOptimizer.

        Args:
            logger: The logger instance to use.
            config: The configparser instance.
        """
        self.logger = logger
        self.config = config  # Store the config
        self.optimizer_model = None  # Initialize optimizer_model
        self._initialize_optimizer_model()  # Initialize the model
        self.total_optimization_usage = {
            'input_token_count': 0,
            'output_token_count': 0,
            'total_token_count': 0,
            'cached_content_token_count': 0
        }

    def _initialize_optimizer_model(self):
        """Initializes the dedicated GenerativeModel."""
        try:
            optimizer_config = self.config["GEMINI_OPTIMIZER"]
            vertexai.init(project=optimizer_config.get("PROJECT_ID"), location=optimizer_config.get("LOCATION", "us-central1"))
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = optimizer_config.get("GOOGLE_APPLICATION_CREDENTIALS")
            self.optimizer_model = GenerativeModel(model_name=optimizer_config.get("MODEL_NAME"))
            self.logger.info(f"Initialized dedicated GenerativeModel for optimization: {optimizer_config.get('MODEL_NAME')}")
        except Exception as e:
            self.logger.error(f"Error initializing optimizer model: {e}")
            raise

    def _send_message_optimizer(self, message: str) -> Tuple[str, Dict[str, int]]:
        """Sends a message to the optimizer model."""
        if self.optimizer_model is None:
            raise RuntimeError("Optimizer model is not initialized.")

        try:
            safety_settings = {
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
            }
            response = self.optimizer_model.generate_content(
                [Content(role="user", parts=[Part.from_text(message)])],
                generation_config={
                    "temperature": float(self.config["GEMINI_OPTIMIZER"].get("TEMPERATURE")),
                    "top_p": float(self.config["GEMINI_OPTIMIZER"].get("TOP_P")),
                    "top_k": int(self.config["GEMINI_OPTIMIZER"].get("TOP_K")),
                    "max_output_tokens": int(self.config["GEMINI_OPTIMIZER"].get("MAX_OUTPUT_TOKENS", '8192')),
                },
                safety_settings =safety_settings,  
            )
            usage_metadata = {}
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage_metadata = {
                    'input_token_count': response.usage_metadata.prompt_token_count,
                    'output_token_count': response.usage_metadata.candidates_token_count,
                    'total_token_count': response.usage_metadata.total_token_count,
                    'cached_content_token_count': getattr(response.usage_metadata, 'cached_content_token_count', 0),
                }
            return response.text, usage_metadata

        except Exception as e:
            self.logger.error(f"Error during optimizer model interaction: {e}")
            raise

    def get_total_optimization_usage(self) -> Dict[str, int]:
        """Returns total optimization usage."""
        return self.total_optimization_usage

    def optimize_prompt(self, original_prompt: str, csv_data: str, task_description: str, output_schema: Dict, optimization_prompt_template: str = None, max_optimization_attempts: int = 3) -> Tuple[str, Dict[str, int]]:
        """Optimizes a prompt using the dedicated model."""
        self.logger.info(f"Optimizing prompt for: {task_description}")

        if optimization_prompt_template is None:
            optimization_prompt_template = """
            You are a prompt engineering expert. Improve the following prompt:

            Original Prompt:
            ```text
            {original_prompt}
            ```

            CSV Data:
            ```csv
            {csv_data}
            ```

            Output Schema:
            ```json
            {output_schema}
            ```
            Return ONLY the improved prompt.
            """

        best_prompt = original_prompt
        best_usage_for_call = {}

        for attempt in range(1, max_optimization_attempts + 1):
            time.sleep(5)
            formatted_prompt = optimization_prompt_template.format(
                original_prompt=original_prompt,
                csv_data=csv_data,
                output_schema=json.dumps(output_schema, indent=2),
                task_description=task_description
            )
            try:
                optimized_prompt, usage_metadata = self._send_message_optimizer(formatted_prompt)
                optimized_prompt = optimized_prompt.strip().replace("```text", "").replace("```", "").strip()

                if usage_metadata:
                    for key in self.total_optimization_usage:
                        self.total_optimization_usage[key] += usage_metadata.get(key, 0)
                    best_usage_for_call = usage_metadata

                if optimized_prompt:
                    best_prompt = optimized_prompt
                    break
            except Exception as e:
                self.logger.error(f"Optimization attempt {attempt} failed: {e}", exc_info=True)


        self.logger.info(f"Optimized Prompt: {best_prompt}")
        return best_prompt, best_usage_for_call