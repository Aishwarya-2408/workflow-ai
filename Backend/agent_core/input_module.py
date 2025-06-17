# Placeholder for Input Module 

import os
from .logging_module import LoggingModule

class InputModule:
    def __init__(self, logger: LoggingModule):
        self.logger = logger

    def get_user_instructions(self, instruction_file_path: str) -> str:
        """Reads natural language instructions from the specified file."""
        self.logger.info(f"Attempting to read user instructions from file: {instruction_file_path}")
        if not instruction_file_path:
            self.logger.error("No instruction file path provided.")
            return ""
        
        resolved_path = instruction_file_path
        if not os.path.isabs(resolved_path):
            # Assuming if not absolute, it's relative to the workspace root.
            # This is a common assumption, but could be made more robust
            # if the workspace root is explicitly passed around.
            resolved_path = os.path.abspath(resolved_path)
            self.logger.info(f"Instruction file path resolved to: {resolved_path}")

        if not os.path.exists(resolved_path):
            self.logger.error(f"Instruction file not found at: {resolved_path}")
            return ""
        if not os.path.isfile(resolved_path):
            self.logger.error(f"Instruction path exists but is not a file: {resolved_path}")
            return ""

        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                instructions = f.read()
            self.logger.info(f"Successfully read instructions from: {resolved_path}")
            if not instructions.strip():
                self.logger.warning(f"Instruction file {resolved_path} is empty or contains only whitespace.")
            return instructions
        except Exception as e:
            self.logger.error(f"Error reading instruction file {resolved_path}: {e}", exc_info=True)
            return ""

    def get_file_paths(self, prompt: str = None, file_paths: str = None):
        """
        Returns a list of file paths for context. If file_paths is provided, use it; otherwise, prompt the user.
        Accepts blank, 'none', or 'None' as no input.
        """
        if file_paths is not None:
            cleaned = file_paths.strip().lower()
            if cleaned in ('', 'none'):
                return []
            # Split by comma and strip whitespace
            return [p.strip() for p in file_paths.split(',') if p.strip()]


if __name__ == '__main__':
    # Example Usage
    test_logger = LoggingModule(log_level='DEBUG')
    input_module = InputModule(logger=test_logger)

    # --- Testing User Instructions from file ---
    print("\n--- Testing User Instructions from file ---")
    dummy_instructions_file = "test_instructions.txt"
    
    # Test Case 1: File exists and has content
    with open(dummy_instructions_file, "w") as f:
        f.write("Process the data and generate a report.")
    instructions1 = input_module.get_user_instructions(dummy_instructions_file)
    print(f"Captured Instructions (from file): {instructions1}")
    assert instructions1 == "Process the data and generate a report."
    os.remove(dummy_instructions_file)

    # Test Case 2: File does not exist
    instructions2 = input_module.get_user_instructions("non_existent_instructions.txt")
    print(f"Captured Instructions (non-existent file): '{instructions2}'")
    assert instructions2 == ""

    # Test Case 3: File is empty
    with open(dummy_instructions_file, "w") as f:
        f.write("")
    instructions3 = input_module.get_user_instructions(dummy_instructions_file)
    print(f"Captured Instructions (empty file): '{instructions3}'")
    assert instructions3 == "" # Or check for whitespace only if that's the behavior
    os.remove(dummy_instructions_file)
    
    # Test Case 4: No file path provided (should return empty and log error)
    instructions4 = input_module.get_user_instructions("")
    print(f"Captured Instructions (no file path): '{instructions4}'")
    assert instructions4 == ""

    # print("\n--- Testing File Paths (remains unchanged, uses input()) ---")
    # # Create dummy files for testing
    # with open("test_file1.txt", "w") as f:
    #     f.write("test1")
    # with open("test_file2.log", "w") as f:
    #     f.write("test2")
    
    # # file_paths = input_module.get_file_paths("Enter test file paths (e.g., test_file1.txt, non_existent.txt, test_file2.log): ")
    # # print(f"Captured and Validated File Paths: {file_paths}")

    # # # Clean up dummy files
    # # if os.path.exists("test_file1.txt"): os.remove("test_file1.txt")
    # # if os.path.exists("test_file2.log"): os.remove("test_file2.log")

    test_logger.info("InputModule example finished. Note: get_file_paths() input() calls were skipped in this automated test.") 