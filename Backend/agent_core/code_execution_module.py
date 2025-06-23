import subprocess
import tempfile
import os
import sys
import re # For detecting error patterns in stdout
from .logging_module import LoggingModule
import shutil
import venv

class CodeExecutionModule:
    def __init__(self, logger: LoggingModule, timeout_seconds: int = 10):
        self.logger = logger
        self.timeout_seconds = timeout_seconds
        # Common error patterns to check in stdout if stderr is empty and exit code is 0
        self.stdout_error_patterns = [
            re.compile(r"error:", re.IGNORECASE),
            re.compile(r"exception:", re.IGNORECASE),
            re.compile(r"traceback \(most recent call last\):", re.IGNORECASE),
            re.compile(r"failed to", re.IGNORECASE),
            re.compile(r"can't find", re.IGNORECASE), # For errors like "Can't find workbook"
            re.compile(r"could not process", re.IGNORECASE),
            re.compile(r"invalid file", re.IGNORECASE),
            re.compile(r"unexpected error occurred", re.IGNORECASE), # From your log
            re.compile(r"no module named", re.IGNORECASE), # To catch ModuleNotFoundError in stdout if stderr isn't used
        ]
        
        # Critical error patterns that should halt retries (for main agent compatibility)
        # Note: Warnings are NOT included here as they should not halt execution
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
        
        # Warning patterns that should be ignored (not treated as errors)
        self.warning_patterns = [
            re.compile(r"^Warning:", re.MULTILINE | re.IGNORECASE),
            re.compile(r"UserWarning:", re.IGNORECASE),
            re.compile(r"DeprecationWarning:", re.IGNORECASE),
            re.compile(r"FutureWarning:", re.IGNORECASE),
            re.compile(r"RuntimeWarning:", re.IGNORECASE),
        ]

    def _is_only_warnings(self, stderr_text: str) -> bool:
        """
        Check if stderr contains only warnings and no actual errors.
        Returns True if stderr is empty or contains only warnings.
        """
        if not stderr_text or not stderr_text.strip():
            return True
        
        # Split stderr into lines and check each non-empty line
        lines = [line.strip() for line in stderr_text.split('\n') if line.strip()]
        
        for line in lines:
            # Check if this line contains warning keywords (more flexible matching)
            is_warning_line = (
                'warning:' in line.lower() or
                'userwarning:' in line.lower() or
                'deprecationwarning:' in line.lower() or
                'futurewarning:' in line.lower() or
                'runtimewarning:' in line.lower() or
                line.startswith('Warning:') or
                # Handle the specific format from your logs
                'Warning: No code found for cleaned name' in line or
                'Original condition retained.' in line
            )
            
            if not is_warning_line:
                # Check if it's an actual error pattern
                is_error_line = any(pattern.search(line) for pattern in self.critical_error_patterns)
                if is_error_line:
                    return False
                # If it's neither a clear warning nor a clear error, be conservative
                # Allow empty lines or lines that look like continuation of warnings
                if line and not any(keyword in line.lower() for keyword in ['warning', 'note:', 'info:', 'debug:']):
                    return False
        
        return True

    def _install_packages(self, pip_executable: str, packages: list[str]) -> bool:
        """Installs a list of packages using the specified pip executable."""
        if not packages:
            self.logger.info("No packages to install.")
            return True

        self.logger.info(f"Installing required packages: {packages}")
        try:
            # Use --disable-pip-version-check to speed up installation
            # Use --upgrade to ensure latest version or upgrade existing
            # Use -q for quieter output, but not too quiet to hide errors
            # Removed check=True so that a non-zero exit code doesn't raise an exception immediately.
            # We will check the return code manually.
            result = subprocess.run(
                [pip_executable, "install", "--disable-pip-version-check", "--upgrade"] + packages,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=self.timeout_seconds + 60 # Give installation more time than execution
            )
            self.logger.info(f"Pip install:\n{result.stdout}")
            if result.stderr:
                 self.logger.warning(f"Pip install:\n{result.stderr}") # Warnings are common

            # Check the return code to determine if installation was successful for the batch
            if result.returncode != 0:
                self.logger.error(f"Pip install failed for packages {packages} with exit code {result.returncode}. See stderr above.")
                return False # Indicate failure
            else:
                 self.logger.info(f"Packages installed successfully: {packages}")
                 return True # Indicate success
        except subprocess.TimeoutExpired:
             self.logger.error(f"Pip install timed out after {self.timeout_seconds + 60} seconds while installing {packages}.")
             # The subprocess might still be running. Need to handle this.
             # In a simple implementation, we might just log and return False.
             # For robustness, could try to kill the process.
             return False
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during package installation: {e}", exc_info=True)
            return False

    def execute_code(self, code_string: str, required_packages=None, python_version=None, output_dir: str = None) -> dict:
        """
        Executes the provided Python code string in a sandboxed virtual environment.
        Installs specified required packages, runs the code, and cleans up the environment.
        """
        self.logger.info("Starting code execution in isolated virtual environment.")
        if not code_string or not code_string.strip():
            self.logger.error("No code provided to execute.")
            return {"stdout": "", "stderr": "Error: No code provided.", "exit_code": -1, "success": False, "error": "No code provided"}

        venv_dir = None
        temp_file_path = None
        process = None
        try:
            # Determine the project root directory
            script_dir = os.path.dirname(os.path.abspath(__file__))
            # Assuming code_execution_module.py is in agent_core, the project root is one level up
            project_root = os.path.dirname(script_dir)
            temp_base_dir = os.path.join(project_root, "temp_env")

            # Ensure the temp base directory exists
            os.makedirs(temp_base_dir, exist_ok=True)
            self.logger.debug(f"Ensured temporary base directory exists at: {temp_base_dir}")

            # 1. Create temp directory for venv inside the project's temp folder
            venv_dir = tempfile.mkdtemp(prefix="agent_venv_", dir=temp_base_dir)
            self.logger.info(f"Created virtual environment directory inside project temp: {venv_dir}")

            # 2. Create venv with specified python version
            python_exe = python_version or sys.executable
            self.logger.info(f"Using Python executable: {python_exe}")
            # Add --without-pip to potentially speed up venv creation if we install separately
            # However, we need pip, so let's keep it simple and just create normally.
            subprocess.check_call([python_exe, "-m", "venv", venv_dir])
            self.logger.info(f"Virtual environment created at: {venv_dir}")

            # 3. Install required packages if provided
            packages_to_install = required_packages if isinstance(required_packages, list) else []

            pip_exe = os.path.join(venv_dir, "Scripts" if os.name == "nt" else "bin", "pip")
            if packages_to_install and not self._install_packages(pip_exe, packages_to_install):
                # If package installation fails, we cannot proceed
                return {"stdout": "", "stderr": "Error: Failed to install required packages.", "exit_code": -1, "success": False, "error": "Failed to install required packages"}

            # 4. Write code to temp file
            # The generated code file will be placed inside the venv_dir automatically
            with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.py', encoding='utf-8', dir=venv_dir) as tf:
                tf.write(code_string)
                temp_file_path = tf.name
            self.logger.info(f"Generated code written to temporary file: {temp_file_path}")

            # 5. Run code using venv's python
            python_bin = os.path.join(venv_dir, "Scripts" if os.name == "nt" else "bin", "python")
            command = [python_bin, temp_file_path]
            self.logger.debug(f"Executing command: {' '.join(command)}")
            
            # Set PYTHONPATH to include the workspace root so the agent's own modules can be imported
            # This is important if the generated code needs to import other parts of your project.
            # workspace_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            env = os.environ.copy()
            # Prepend workspace root to PYTHONPATH - This is important for the generated code
            # to be able to import other modules from the agent_core directory if needed.
            env['PYTHONPATH'] = os.pathsep.join([project_root] + env.get('PYTHONPATH', '').split(os.pathsep))
            self.logger.debug(f"Setting PYTHONPATH for execution: {env['PYTHONPATH']}")

            # Add the output_dir to the environment if provided, so the generated code can use it
            if output_dir:
                env['AGENT_OUTPUT_DIR'] = output_dir
                self.logger.info(f"Set AGENT_OUTPUT_DIR environment variable to: {output_dir}")

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=env, # Pass the modified environment
            )
            stdout, stderr = process.communicate(timeout=self.timeout_seconds)
            exit_code = process.returncode
            self.logger.info(f"Code execution finished. Exit code: {exit_code}")
            actual_stdout = stdout.strip()
            actual_stderr = stderr.strip()
            if actual_stdout:
                self.logger.debug(f"Stdout:\n{actual_stdout}")
            if actual_stderr:
                self.logger.error(f"Stderr:\n{actual_stderr}")
            
            # Determine success with improved warning handling
            success = False
            error_message = None
            if exit_code == 0:
                if actual_stderr:
                    # Check if stderr contains only warnings
                    if self._is_only_warnings(actual_stderr):
                        self.logger.info(f"Execution had exit code 0 with warnings in stderr (ignoring warnings).")
                        # Continue to check stdout for errors, but don't fail due to warnings
                        stdout_has_error = False
                        for pattern in self.stdout_error_patterns:
                            if pattern.search(actual_stdout):
                                self.logger.warning(f"Execution had exit code 0 with warnings, but stdout matches error pattern: '{pattern.pattern}'. Considered a failure.")
                                error_message = f"Error pattern found in stdout: {actual_stdout[:200]}..."
                                stdout_has_error = True
                                break
                        if not stdout_has_error:
                            success = True
                    else:
                        self.logger.warning(f"Execution had exit code 0 but produced stderr with actual errors. Considered a failure.")
                    error_message = actual_stderr
                else:
                    stdout_has_error = False
                    for pattern in self.stdout_error_patterns:
                        if pattern.search(actual_stdout):
                            self.logger.warning(f"Execution had exit code 0 and no stderr, but stdout matches error pattern: '{pattern.pattern}'. Considered a failure.")
                            error_message = f"Error pattern found in stdout: {actual_stdout[:200]}..."
                            stdout_has_error = True
                            break
                    if not stdout_has_error:
                        success = True
            else:
                error_message = actual_stderr or f"Execution failed with exit code {exit_code} and no specific error message on stderr."
                if not actual_stderr and actual_stdout:
                    error_message += f" Stdout was: {actual_stdout[:200]}..."
            if not success and error_message is None:
                 error_message = f"Execution failed with exit code {exit_code}."
                 if actual_stderr: error_message += f" Stderr: {actual_stderr}"
                 if actual_stdout: error_message += f" Stdout: {actual_stdout[:200]}..."
            return {
                "stdout": actual_stdout, 
                "stderr": actual_stderr, 
                "exit_code": exit_code, 
                "success": success,
                "error": error_message
            }
        except subprocess.TimeoutExpired:
            self.logger.error(f"Code execution timed out after {self.timeout_seconds} seconds.")
            if process and process.poll() is None:
                process.kill()
                process.communicate()
            return {
                "stdout": "", 
                "stderr": f"Error: Execution timed out after {self.timeout_seconds} seconds.", 
                "exit_code": -1,
                "success": False,
                "error": f"Execution timed out after {self.timeout_seconds} seconds."
            }
        except FileNotFoundError:
            self.logger.error(f"Python interpreter not found at {python_exe}")
            return {"stdout": "", "stderr": "Error: Python interpreter not found.", "exit_code": -1, "success": False, "error": "Python interpreter not found"}
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during code execution: {e}", exc_info=True)
            return {"stdout": "", "stderr": f"Error: An unexpected error occurred: {e}", "exit_code": -1, "success": False, "error": str(e)}
        finally:
            # Clean up temporary files and directories
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    self.logger.info(f"Temporary file {temp_file_path} deleted.")
                except Exception as e:
                    self.logger.warning(f"Could not delete temporary file {temp_file_path}: {e}")
            # Only attempt to delete the venv directory if it was successfully created
            if venv_dir and os.path.exists(venv_dir):
                try:
                    # On Windows, shutil.rmtree might fail if files are still in use.
                    # A small delay or retry might help, but for simplicity, just log if it fails.
                    shutil.rmtree(venv_dir)
                    self.logger.info(f"Virtual environment directory {venv_dir} deleted.")
                except Exception as e:
                    self.logger.warning(f"Could not delete virtual environment directory {venv_dir}: {e}")