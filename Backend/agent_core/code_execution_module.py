import subprocess
import os
import sys
import threading
import io
import site
import logging
import re # For critical error patterns
from typing import List, Dict, Any

class CodeExecutionModule:
    def __init__(self, logger, timeout_seconds: int = 60):
        self.logger = logger.get_logger() if hasattr(logger, 'get_logger') else logger
        self.timeout_seconds = timeout_seconds
        # Define critical error patterns that should halt retries
        self.critical_error_patterns = [
            re.compile(r"ModuleNotFoundError"),
            re.compile(r"FileNotFoundError"),
            re.compile(r"Permission denied"),
            re.compile(r"SyntaxError"), # Unrecoverable syntax errors
            re.compile(r"IndentationError"), # Unrecoverable indentation errors
            re.compile(r"AttributeError: module '.*?' has no attribute '.*?'"),
            re.compile(r"TypeError: 'NoneType' object is not callable"),
            re.compile(r"BrokenPipeError")
        ]

    def _install_packages(self, packages: List[str]) -> bool:
        if not packages:
            return True
        self.logger.info(f"Attempting to install required packages: {', '.join(packages)}")
        try:
            # Ensure pip is run with the same Python interpreter
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "--no-input"] + packages,
                capture_output=True,
                text=True,
                check=True,
                timeout=300 # Longer timeout for package installation
            )
            self.logger.info(f"pip install stdout:\n{result.stdout}")
            if result.stderr:
                self.logger.warning(f"pip install stderr:\n{result.stderr}")
            self.logger.info(f"Successfully installed packages: {', '.join(packages)}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install packages: {e}", exc_info=True)
            self.logger.error(f"pip install stdout:\n{e.stdout}")
            self.logger.error(f"pip install stderr:\n{e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            self.logger.error(f"Package installation timed out after 300 seconds for packages: {', '.join(packages)}")
            return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during package installation: {e}", exc_info=True)
            return False

    def execute_code(self, code_string: str, required_packages: List[str] = None, output_dir: str = None) -> Dict[str, Any]:
        temp_script_path = "generated_script.py"
        output_result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "error": None
        }

        # Handle required packages
        if required_packages:
            if not self._install_packages(required_packages):
                output_result["error"] = "Failed to install required packages."
                output_result["stderr"] = "Failed to install required packages for generated code."
                return output_result

        # Save code to a temporary file
        try:
            with open(temp_script_path, "w", encoding="utf-8") as f:
                f.write(code_string)
        except Exception as e:
            self.logger.error(f"Failed to write generated code to temp file: {e}", exc_info=True)
            output_result["error"] = f"Failed to write generated code: {e}"
            return output_result

        # Prepare environment for execution
        env = os.environ.copy()
        # Ensure that the current directory is in PYTHONPATH for local imports
        current_dir = os.path.abspath(os.path.dirname(temp_script_path))
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{current_dir}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = current_dir

        # Add the output_dir to the environment if provided, so the generated code can use it
        if output_dir:
            env['AGENT_OUTPUT_DIR'] = output_dir
            self.logger.info(f"Set AGENT_OUTPUT_DIR environment variable to: {output_dir}")

        # Execute the code using subprocess
        try:
            # sys.executable ensures the correct Python interpreter is used
            process = subprocess.run(
                [sys.executable, temp_script_path],
                capture_output=True,
                text=True,
                check=False, # Do not raise CalledProcessError for non-zero exit codes
                timeout=self.timeout_seconds,
                env=env # Pass the modified environment variables
            )

            output_result["stdout"] = process.stdout
            output_result["stderr"] = process.stderr
            output_result["exit_code"] = process.returncode

            if process.returncode == 0:
                output_result["success"] = True
                self.logger.info("Code executed successfully.")
            else:
                output_result["error"] = f"Code execution failed with exit code {process.returncode}."
                self.logger.error(f"Code execution failed. Exit code: {process.returncode}")
                self.logger.error(f"STDOUT:\n{process.stdout}")
                self.logger.error(f"STDERR:\n{process.stderr}")

        except subprocess.TimeoutExpired:
            self.logger.error(f"Code execution timed out after {self.timeout_seconds} seconds.")
            output_result["error"] = f"Execution timed out after {self.timeout_seconds} seconds."
            output_result["stderr"] = "Execution timed out."
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during code execution: {e}", exc_info=True)
            output_result["error"] = f"Unexpected execution error: {e}"
            output_result["stderr"] = f"Unexpected execution error: {e}"
        finally:
            # Clean up the temporary script file
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
        return output_result 