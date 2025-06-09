from .logging_module import LoggingModule
import os # Added for path operations

class InstructionProcessingModule:
    def __init__(self, logger: LoggingModule):
        self.logger = logger

    def _read_file_content(self, file_path: str) -> tuple[str | None, str | None]:
        """
        Reads the content of a single file if it's a text file.
        If it's an Excel file, returns a special marker and the path.
        Returns: (content, error_message)
        """
        file_extension = os.path.splitext(file_path)[1].lower()
        
        if file_extension in ['.xlsx', '.xls']:
            self.logger.info(f"Identified Excel file: {file_path}. Will instruct AI to process it.")
            # Instead of reading content, return a marker and the path for the AI to handle.
            # This marker will be used to build a specific instruction in the prompt.
            return f"EXCEL_FILE_MARKER:{file_path}", None
        else:
            # Try to read as a text file
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.logger.info(f"Successfully read text content from: {file_path}")
                return content, None
            except FileNotFoundError:
                self.logger.error(f"File not found: {file_path}")
                return None, f"File not found: {file_path}"
            except UnicodeDecodeError as ude:
                self.logger.error(f"Unicode decode error for {file_path}: {ude}. Marking as non-text.")
                return f"NON_TEXT_FILE_MARKER:{file_path}", f"Could not decode as text: {file_path}"
            except Exception as e:
                self.logger.error(f"Error reading file {file_path}: {e}")
                return None, f"Error reading file {file_path}: {e}"

    def process_instructions(self, instructions: str, file_paths: list[str] | None = None) -> dict:
        """
        Parses user instructions, reads content from provided files, 
        and prepares a structured prompt for the code generation module.
        """
        self.logger.info("Starting instruction processing.")
        self.logger.debug(f"Raw instructions: {instructions}")
        self.logger.debug(f"File paths: {file_paths}")

        file_context_str = ""
        excel_file_instructions = []
        other_file_errors = []

        if file_paths:
            for path in file_paths:
                content, error = self._read_file_content(path)
                if error:
                    # If there was an error (e.g., file not found, or non-text file that wasn't Excel)
                    # We'll log it and potentially add this error to the prompt for AI awareness
                    self.logger.warning(f"Skipping content for {path} due to error: {error}")
                    other_file_errors.append(f"Note: Could not directly read file '{os.path.basename(path)}'. Error: {error}")
                    continue
                
                if content and content.startswith("EXCEL_FILE_MARKER:"):
                    excel_file_path = content.split(":", 1)[1]
                    excel_file_instructions.append(
                        f"- An Excel file is provided at path: '{excel_file_path}'. Your generated Python code MUST use a library like pandas to read this file. "
                        f"The code should handle potential errors during file reading (e.g., file not found, incorrect format for pandas, corrupted file) gracefully. "
                        f"If an error occurs reading the Excel file, print a clear error message to standard error (stderr) and exit with a non-zero status code."
                    )
                elif content and content.startswith("NON_TEXT_FILE_MARKER:"):
                    # For other non-text files we couldn't decode
                    file_context_str += f"\n--- Note on {os.path.basename(path)} ---\n"
                    file_context_str += f"The file '{path}' could not be read as plain text. If relevant to the task, your code might need to handle it or ask for clarification.\n"
                    file_context_str += f"--- End of Note on {os.path.basename(path)} ---\n"
                elif content:
                    file_context_str += f"\n--- Content of {os.path.basename(path)} ---\n{content}\n--- End of {os.path.basename(path)} ---\n"
        
        if not instructions and not file_context_str and not excel_file_instructions:
            self.logger.warning("No instructions or file context provided. Cannot generate a meaningful prompt.")
            return {"prompt": "", "error": "No input provided for processing."}

        prompt = f"User Instructions: {instructions}\n"

        if excel_file_instructions:
            prompt += "\nMandatory Excel File Processing Instructions:\n"
            prompt += "\n".join(excel_file_instructions)
            prompt += "\nRemember to import necessary libraries (like pandas and openpyxl) for Excel handling in your generated Python code.\n"

        if file_context_str:
            prompt += f"\nRelevant Text File Contexts:\n{file_context_str}"
        
        if other_file_errors:
            prompt += "\nNotes on File Access:\n" + "\n".join(other_file_errors) + "\n"

        prompt += "\n\nTask: Based on ALL the instructions, file processing requirements, and text contexts above, generate the required Python code. "
        prompt += "The code should be robust. If critical errors occur (like being unable to read a required input file), print a descriptive error message to stderr and exit with a non-zero status code. "
        prompt += "Ensure your code is complete, handles file operations, performs calculations/transformations, and produces specified outputs."

        self.logger.info("Instruction processing complete. Prompt prepared.")
        self.logger.debug(f"Generated prompt (first 200 chars): {prompt[:200]}...")
        
        return {"prompt": prompt, "error": None}

if __name__ == '__main__':
    # Example Usage
    test_logger = LoggingModule(log_level='DEBUG')
    instruction_processor = InstructionProcessingModule(logger=test_logger)

    # Test case 1: Instructions only
    print("--- Test Case 1: Instructions Only ---")
    user_instr_1 = "Create a Python function that adds two numbers."
    result_1 = instruction_processor.process_instructions(user_instr_1)
    # print(f"Prompt 1: {result_1['prompt']}")
    assert "User Instructions: Create a Python function that adds two numbers." in result_1['prompt']

    # Test case 2: Instructions and a (dummy) text file
    print("\n--- Test Case 2: Instructions and Text File ---")
    user_instr_2 = "Refactor the code in the provided file to be more efficient."
    dummy_text_file_path = "dummy_script.py"
    with open(dummy_text_file_path, "w") as f:
        f.write("def old_function():\n    return 1+1")
    result_2 = instruction_processor.process_instructions(user_instr_2, [dummy_text_file_path])
    # print(f"Prompt 2 (snippet): {result_2['prompt'][:300]}...")
    assert f"Content of {os.path.basename(dummy_text_file_path)}" in result_2['prompt']
    assert "def old_function():" in result_2['prompt']
    os.remove(dummy_text_file_path)

    # Test case 3: Instructions and a (dummy) Excel file
    print("\n--- Test Case 3: Instructions and Excel File ---")
    user_instr_3 = "Analyze the data in the excel sheet Input.xlsx and output results to output.xlsx"
    dummy_excel_file_path = "Input.xlsx" # Use the actual name from your log for testing this part
    result_3 = instruction_processor.process_instructions(user_instr_3, [dummy_excel_file_path])
    # print(f"Prompt 3: {result_3['prompt']}")
    assert f"An Excel file is provided at path: '{dummy_excel_file_path}'" in result_3['prompt']
    assert "handle potential errors during file reading" in result_3['prompt']
    assert "print a clear error message to standard error (stderr) and exit with a non-zero status code" in result_3['prompt']

    # Test case 4: File not found
    print("\n--- Test Case 4: File Not Found ---")
    user_instr_4 = "Process missing_file.txt"
    result_4 = instruction_processor.process_instructions(user_instr_4, ["missing_file.txt"])
    # print(f"Prompt 4: {result_4['prompt']}")
    assert "Could not directly read file 'missing_file.txt'" in result_4['prompt']

    # Test case 5: Non-text (binary like) file that is not Excel
    print("\n--- Test Case 5: Non-text/Binary File (not Excel) ---")
    user_instr_5 = "Check this binary_file.dat"
    dummy_binary_file_path = "binary_file.dat"
    with open(dummy_binary_file_path, "wb") as f: # write some bytes that are not utf-8
        f.write(b'\xff\xfe\x00\x01')
    result_5 = instruction_processor.process_instructions(user_instr_5, [dummy_binary_file_path])
    # print(f"Prompt 5 (snippet): {result_5['prompt'][:300]}...")
    assert f"The file '{dummy_binary_file_path}' could not be read as plain text" in result_5['prompt']
    os.remove(dummy_binary_file_path)

    test_logger.info("InstructionProcessingModule example finished.") 