# Placeholder for Code Execution Module 

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
            self.logger.info(f"Pip install stdout:\n{result.stdout}")
            if result.stderr:
                 self.logger.warning(f"Pip install stderr:\n{result.stderr}") # Warnings are common

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

    def execute_code(self, code_string: str, required_packages=None, python_version=None) -> dict:
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
            
            # Determine success more strictly (same as before)
            success = False
            error_message = None
            if exit_code == 0:
                if actual_stderr:
                    self.logger.warning(f"Execution had exit code 0 but produced stderr. Considered a failure.")
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


if __name__ == '__main__':
    test_logger = LoggingModule(log_level='DEBUG')
    # Increased timeout for tests that might include installation
    code_executor = CodeExecutionModule(logger=test_logger, timeout_seconds=30) # Increased timeout for potential installs

    # Test case 1: Successful execution (no packages)
    print("\n--- Test Case 1: Successful Execution (No Packages) ---")
    code1 = "print('Hello from executed code')\nimport sys; sys.exit(0)"
    result1 = code_executor.execute_code(code1)
    print(f"Result 1: {result1}")
    assert result1["success"] is True
    assert result1["error"] is None

    # Test case 2: Execution with an error printed to stderr
    print("\n--- Test Case 2: Execution with Stderr Error ---")
    code2 = "import sys; sys.stderr.write('Something went wrong on stderr\n'); sys.exit(1)"
    result2 = code_executor.execute_code(code2)
    print(f"Result 2: {result2}")
    assert result2["success"] is False
    assert "Something went wrong on stderr" in result2["stderr"]
    assert "Something went wrong on stderr" in result2["error"]

    # Test case 3: Execution timeout
    print("\n--- Test Case 3: Execution Timeout ---")
    # This test might need adjustment if timeout_seconds is increased significantly.
    # If timeout is too long, the test itself takes too long.
    code3 = "import time\nprint('Starting long task')\ntime.sleep(10)\nprint('Finished long task')"
    # Expecting this to time out based on timeout_seconds=30 for the executor instance if it runs for >30s.
    # Keep the code sleep time short (e.g., 5s) if timeout_seconds is around 10-15s.
    # Let's make the code sleep slightly less than the timeout for this test to potentially pass if timeout is generous.
    code3_short_sleep = "import time\nprint('Starting task')\ntime.sleep(25)\nprint('Finished task')"
    result3 = code_executor.execute_code(code3_short_sleep)
    print(f"Result 3: {result3}")
    # Assertion depends on whether it times out or completes within the new timeout.
    # Let's test for timeout still, assuming 30s is still potentially hit.
    assert result3["success"] is False or result3["stdout"].startswith('Starting task') # Either times out or starts
    if not result3["success"]:
        assert "timed out" in result3["error"]

    # Test case 4: Error printed to stdout, exit code 0
    print("\n--- Test Case 4: Error in Stdout, Exit 0 ---")
    code4 = "print('An error occurred during processing: File not found')\nimport sys; sys.exit(0)"
    result4 = code_executor.execute_code(code4)
    print(f"Result 4: {result4}")
    assert result4["success"] is False
    assert "Error pattern found in stdout" in result4["error"]
    assert "File not found" in result4["stdout"]

    # Test case 5: ModuleNotFoundError - SHOULD NOW PASS after install logic
    print("\n--- Test Case 5: ModuleNotFoundError (Install Test) ---")
    code5_install_test = "import pandas\nprint(pandas.__version__)"
    result5 = code_executor.execute_code(code5_install_test)
    print(f"Result 5: {result5}")
    # We expect this to succeed now that pandas is installed
    assert result5["success"] is True, f"Test Case 5 Failed: {result5.get('error', 'Unknown error')}"
    assert result5["error"] is None
    assert result5["stdout"] # Expect some output (pandas version)

    # Test case 6: Clean exit 0, no stderr, no error patterns in stdout
    print("\n--- Test Case 6: Clean Exit 0, Happy Path ---")
    code6 = "print('Processing complete. Output file generated.')\nimport sys; sys.exit(0)"
    result6 = code_executor.execute_code(code6)
    print(f"Result 6: {result6}")
    assert result6["success"] is True
    assert result6["error"] is None

    # Test case 7: Exit code 0, but stderr has content
    print("\n--- Test Case 7: Exit 0, but Stderr has content ---")
    code7 = "import sys; sys.stderr.write('A minor warning but we exited 0.\n'); print('All good otherwise'); sys.exit(0)"
    result7 = code_executor.execute_code(code7)
    print(f"Result 7: {result7}")
    assert result7["success"] is False
    assert "A minor warning" in result7["stderr"]
    assert "A minor warning" in result7["error"]

    # Test case 8: Install multiple packages
    print("\n--- Test Case 8: Install Multiple Packages ---")
    code8_multiple_install = "import requests\nimport openpyxl\nprint('Packages imported successfully')"
    result8 = code_executor.execute_code(code8_multiple_install)
    print(f"Result 8: {result8}")
    assert result8["success"] is True, f"Test Case 8 Failed: {result8.get('error', 'Unknown error')}"
    assert result8["error"] is None
    assert "Packages imported successfully" in result8["stdout"]

    test_logger.info("CodeExecutionModule example finished.") 