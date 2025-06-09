import csv
import os
import json
import time
import io
from typing import Dict, Tuple
import pandas as pd
import xlrd
from pandas.errors import EmptyDataError
from GenAI import GeminiVertexAI
from utility import get_logger

class GenAIApp:
    def __init__(self, config_path="config/workflows.json", timestamp = None):
        self.logger = get_logger()
        self.config_path = config_path
        self.config = self.load_config(config_path)
        self.gemini = GeminiVertexAI(timestamp=timestamp)
        self.results = {}
        self.usage_data = []

    def normalize_path(self, path: str) -> str:
        """Convert Windows path to Unix-style path"""
        return path.replace('\\', '/')

    def load_config(self, config_path: str = None) -> dict:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Optional path to override the default config path
            
        Returns:
            dict: The loaded configuration
        """
        try:
            path_to_use = config_path or self.config_path
            if not os.path.exists(path_to_use):
                raise FileNotFoundError(f"Configuration file not found: {path_to_use}")
                
            with open(path_to_use, 'r') as f:
                config = json.load(f)
                # Normalize all file paths in the config
                for workflow in config.values():
                    if 'file_path' in workflow:
                        workflow['file_path'] = self.normalize_path(workflow['file_path'])
                    if 'prompt_file' in workflow:
                        workflow['prompt_file'] = self.normalize_path(workflow['prompt_file'])
                
                self.logger.info(f"Successfully loaded configuration from {path_to_use}")
                self.config = config
                return config
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing configuration file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            raise

    def display_usage_stats(self, usage_data: list, optimization_usage: Dict[str, int]):
        total_input, total_output, total_tokens, total_cached = self.gemini.calculate_total_usage(usage_data)
        
        self.logger.info(f"Usage stats - Input: {total_input}, Output: {total_output}, Total: {total_tokens}, Cached: {total_cached}")
        self.logger.info(f"Optimization Usage stats - Input: {optimization_usage.get('input_token_count', 0)}, Output: {optimization_usage.get('output_token_count', 0)}, Total: {optimization_usage.get('total_token_count', 0)}, Cached: {optimization_usage.get('cached_content_token_count', 0)}")

    def run_workflow(self, use_case: str, stage: str = None) -> Dict:
        """
        Executes the workflow based on the specified use case and stage.
        Returns the result of the stage execution.
        """
        try:
            self.logger.info(f"Starting workflow for use case: {use_case}")

            # Reload config to get latest changes
            self.load_config()

            workflow_config = self.config.get(use_case)
            if not workflow_config:
                raise ValueError(f"No configuration found for use case: {use_case}")

            file_path = workflow_config.get("file_path")
            if not file_path:
                raise ValueError("File path is not specified in the configuration.")
                
            # Process file based on extension
            if file_path.endswith('.csv'):
                csv_data = None  # No conversion needed
            elif file_path.endswith('.xlsx') or file_path.endswith('.xls'):
                try:
                    print(workflow_config.get("sheet_name"))
                    if workflow_config.get("sheet_name") == "":
                        df = pd.read_excel(file_path, sheet_name=0)
                    else:
                        df = pd.read_excel(file_path, sheet_name=workflow_config.get("sheet_name"))
                    print(type(df))
                    print(df.head())
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False, encoding='utf-8', quoting=csv.QUOTE_MINIMAL)
                    csv_data = csv_buffer.getvalue()
                    csv_buffer.close()
                    file_path = io.StringIO(csv_data)
                except xlrd.biffh.XLRDError as e:
                    self.logger.error(f"Error processing {file_path} file: {e}. Please remove the 'Zycus-Only' tag from the file and try again.")
                    raise RuntimeError(f"Error processing {file_path} file. Please remove the 'Zycus-Only' tag from the file and try again.")
                except Exception as e:
                    self.logger.error(f"Failed to convert Excel to CSV: {e}")
                    raise
            else:
                self.logger.error(f"Unsupported file format: {file_path}")
                raise ValueError("Unsupported file format. Must be .csv, .xls, or .xlsx.")

            # Load prompts if not already loaded
            if not hasattr(self, 'prompts'):
                prompt_file_path = workflow_config.get("prompt_file")
                prompts_list = workflow_config.get("prompts", [])
                if not prompt_file_path or len(prompts_list) == 0:
                    raise ValueError("Prompt file path or the prompts list is not specified in the configuration.")
                self.prompts = self.load_prompts(prompt_file_path, prompts_list)

            timestamp = self.gemini.timestamp if self.gemini.timestamp else time.strftime("%Y%m%d_%H%M%S")
            output_dir = "./Data/Output"
            os.makedirs(output_dir, exist_ok=True)

            optimize_prompt = workflow_config.get("optimize_prompt", False)
            stage_result = {}
            stage_usage = {}

            # Execute the specified stage
            if stage == "extract_levels" and workflow_config.get("extract_levels", False):
                if "level_prompt" not in self.prompts:
                    raise ValueError("Level prompt required but not found in prompt file")
                num_rows = workflow_config.get("num_rows", 50)
                levels_json, levels_usage = self.gemini.extract_levels(file_path, self.prompts["level_prompt"], num_rows=num_rows, optimize_prompt_flag=optimize_prompt)
                self.results['levels'] = levels_json
                self.usage_data.append(levels_usage)
                stage_result = levels_json
                stage_usage = levels_usage

            elif stage == "extract_conditions" and workflow_config.get("extract_conditions", False):
                if "condition_prompt" not in self.prompts:
                    raise ValueError("Condition prompt required but not found in prompt file")
                conditions_json, conditions_usage = self.gemini.extract_conditions(self.prompts["condition_prompt"], optimize_prompt_flag=optimize_prompt)
                self.results['conditions'] = conditions_json
                self.usage_data.append(conditions_usage)
                stage_result = conditions_json
                stage_usage = conditions_usage

            elif stage == "map_conditions_to_levels" and workflow_config.get("map_conditions_to_levels", False):
                if "condition_level_mapping_prompt" not in self.prompts:
                    raise ValueError("Condition-level mapping prompt required but not found in prompt file")
                if not self.results.get('levels') or not self.results.get('conditions'):
                    raise ValueError("Levels and conditions must be extracted first")
                mappings, mapping_usage = self.gemini.map_conditions_to_levels(
                    self.results['levels'],
                    self.results['conditions'],
                    self.prompts["condition_level_mapping_prompt"],
                    optimize_prompt_flag=optimize_prompt
                )

                chaining = workflow_config.get("chaining", False)
                if chaining:
                    mappings = self.gemini.fill_previous_levels(self.results['levels'], mappings)

                self.results['max_length'] = max(len(v) for v in mappings.values())
                max_conditions = [k for k, v in mappings.items() if len(v) == self.results['max_length']]
                self.results['mappings'] = mappings
                self.usage_data.append(mapping_usage)
                stage_result = mappings
                stage_usage = mapping_usage

            elif stage == "map_categories" and workflow_config.get("map_categories", False):
                if "named_tree_prompt" not in self.prompts:
                    raise ValueError("Named tree prompt required but not found in prompt file")
                if not all(k in self.results for k in ['levels', 'conditions', 'mappings']):
                    raise ValueError("Previous stages must be completed first")
                header_rows = workflow_config.get("header_rows", 4)
                data_start_row = workflow_config.get("data_start_row", 5)
                chunk_size = workflow_config.get("tree_chunk_size", 5)
                num_rows = workflow_config.get("num_rows", 50)
                category_mapping, process_usage = self.gemini.map_categories(
                    self.results['levels'],
                    self.results['conditions'],
                    self.results['mappings'],
                    file_path,
                    self.prompts["named_tree_prompt"],
                    chunk_size=chunk_size,
                    header_rows=header_rows,
                    data_start_row=data_start_row,
                    num_rows=num_rows,
                    optimize_prompt_flag=optimize_prompt
                )
                self.results['category_mapping'] = category_mapping
                self.usage_data.append(process_usage)
                stage_result = category_mapping
                stage_usage = process_usage

                category_mapping_json_output_path = os.path.join(output_dir, f"workflow_tree_{timestamp}.json")
                with open(category_mapping_json_output_path, "w") as f:
                    json.dump(category_mapping, f, indent=2)

            elif stage == "transform" and workflow_config.get("transform_category_mapping", False):
                if "tree_transform_to_mcw_wcm_prompt" not in self.prompts:
                    raise ValueError("Tree transform prompt required but not found in prompt file")
                if not self.results.get('category_mapping'):
                    raise ValueError("Category mapping must be completed first")
                chunk_size = workflow_config.get("transfrom_chunk_size", 5)
                transformed_data, transform_usage = self.gemini.transform_category_mapping(
                    self.results['category_mapping'],
                    self.prompts["tree_transform_to_mcw_wcm_prompt"],
                    chunk_size=chunk_size,
                    optimize_prompt_flag=optimize_prompt
                )
                self.results['transformed_data'] = transformed_data
                self.usage_data.append(transform_usage)
                stage_result = transformed_data
                stage_usage = transform_usage

                mcw_wcm_json_output_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.json")
                with open(mcw_wcm_json_output_path, "w") as f:
                    json.dump(transformed_data, f, indent=2)

                excel_output_path = os.path.join(output_dir, f"workflow_mcw_wcm_{timestamp}.xlsx")
                self.gemini.save_transformed_data_to_excel(transformed_data, excel_output_path, num_user_columns=self.results['max_length'])

            # Log usage statistics
            total_optimization_usage = self.gemini.prompt_optimizer.get_total_optimization_usage()
            self.display_usage_stats([stage_usage], total_optimization_usage)

            return stage_result
        except Exception as e:
            self.logger.error(f"An error occurred in the workflow for use case '{use_case}': {e}", exc_info=True)
            raise

    def load_prompts(self, prompt_file_path: str, prompts_list: list) -> dict:
        try:
            possible_prompts = [
                "level_prompt",
                "condition_prompt",
                "condition_level_mapping_prompt",
                "named_tree_prompt",
                "tree_transform_to_mcw_wcm_prompt",
                "role_tree_prompt",
                "file_info_prompt",
                "wcm_prompt"
            ]
            
            for prompt_name in prompts_list:
                if prompt_name not in possible_prompts:
                    raise ValueError(f"Invalid prompt name '{prompt_name}' found in workflow configuration.")

            self.logger.info(f"Fetching prompts from: {prompt_file_path}")

            with open(prompt_file_path, "r", encoding="utf-8") as f:
                extracted_prompts = [p.strip() for p in f.read().split("---") if p.strip()]

            if len(prompts_list) > len(extracted_prompts):
                raise ValueError(f"Not enough prompts in {prompt_file_path} to match 'prompts' list.")

            loaded_prompts = {key: extracted_prompts[i] for i, key in enumerate(prompts_list)}
            return loaded_prompts

        except Exception as e:
            self.logger.error(f"Error loading prompts: {e}")
            raise

if __name__ == "__main__":
    try:
        app = GenAIApp()
        app.execute()
    except Exception as e:
        print(f"An error occurred in GenAIApp: {e}")
