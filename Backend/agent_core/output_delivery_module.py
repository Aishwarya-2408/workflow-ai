# Placeholder for Output Delivery Module 

from .logging_module import LoggingModule

class OutputDeliveryModule:
    def __init__(self, logger: LoggingModule):
        self.logger = logger

    def deliver_output(self, final_result: dict):
        """
        Presents the final results to the user.
        For now, prints a summary to the console.

        Args:
            final_result (dict): A dictionary containing the outcome, which might include:
                - "status" (str): e.g., "SUCCESS", "FAILURE_VALIDATION", "FAILURE_CODE_GENERATION", "FAILURE_MAX_RETRIES"
                - "generated_code" (str | None): The last generated code.
                - "execution_stdout" (str | None): The stdout from the last execution.
                - "execution_stderr" (str | None): The stderr from the last execution.
                - "validation_feedback" (list[str] | None): Feedback from the validation module.
                - "message" (str | None): An overall message summarizing the outcome.
        """
        self.logger.info("Delivering final output to the user.")

        print("\n--- Agent Run Summary ---")
        self.logger.info("--- Agent Run Summary ---")

        status = final_result.get("status", "UNKNOWN")
        print(f"Status: {status}")
        self.logger.info(f"Status: {status}")

        if final_result.get("message"):
            print(f"Message: {final_result['message']}")
            self.logger.info(f"Message: {final_result['message']}")

        if final_result.get("generated_code"):
            print("\n--- Generated Code (Final Attempt) ---")
            print(final_result["generated_code"])
            print("--- End of Generated Code ---")
            self.logger.info("--- Generated Code (Final Attempt) ---")
            self.logger.info("\n" + final_result["generated_code"])
            self.logger.info("--- End of Generated Code ---")
        else:
            print("No code was successfully generated or retained.")
            self.logger.info("No code was successfully generated or retained.")

        if final_result.get("execution_stdout"):
            print("\n--- Execution Output (Stdout - Final Attempt) ---")
            print(final_result["execution_stdout"])
            print("--- End of Stdout ---")
            self.logger.info("--- Execution Output (Stdout - Final Attempt) ---")
            self.logger.info("\n" + final_result["execution_stdout"])
            self.logger.info("--- End of Stdout ---")
        
        if final_result.get("execution_stderr"):
            print("\n--- Execution Error (Stderr - Final Attempt) ---")
            print(final_result["execution_stderr"])
            print("--- End of Stderr ---")
            self.logger.info("--- Execution Error (Stderr - Final Attempt) ---")
            self.logger.info("\n" + final_result["execution_stderr"])
            self.logger.info("--- End of Stderr ---")

        if final_result.get("validation_feedback"):
            print("\n--- Validation Feedback (Final Attempt) ---")
            for item in final_result["validation_feedback"]:
                print(f"- {item}")
            print("--- End of Validation Feedback ---")
            self.logger.info("--- Validation Feedback (Final Attempt) ---")
            for item in final_result["validation_feedback"]:
                self.logger.info(f"- {item}")
            self.logger.info("--- End of Validation Feedback ---")
        
        print("\n--- End of Agent Run Summary ---")
        self.logger.info("--- End of Agent Run Summary ---")
        self.logger.info("Output delivery complete.")


if __name__ == '__main__':
    test_logger = LoggingModule(log_level='DEBUG')
    output_deliverer = OutputDeliveryModule(logger=test_logger)

    # Test Case 1: Successful run
    print("\n--- Test Case 1: Successful Run ---")
    success_result = {
        "status": "SUCCESS",
        "message": "Task completed successfully after 1 attempt(s).",
        "generated_code": "print('Hello World')",
        "execution_stdout": "Hello World",
        "execution_stderr": "",
        "validation_feedback": ["Execution successful (exit code 0).", "Stdout matches expected output.", "Linting: No issues found (mock)."],
    }
    output_deliverer.deliver_output(success_result)

    # Test Case 2: Failure after retries
    print("\n--- Test Case 2: Failure after Retries ---")
    failure_result = {
        "status": "FAILURE_MAX_RETRIES",
        "message": "Task failed after 3 attempts.",
        "generated_code": "print('Error Prone\n1/0')",
        "execution_stdout": "Error Prone",
        "execution_stderr": "ZeroDivisionError: division by zero",
        "validation_feedback": ["Execution failed. Exit Code: 1. Stderr: ZeroDivisionError: division by zero"],
    }
    output_deliverer.deliver_output(failure_result)

    # Test Case 3: Failure in code generation
    print("\n--- Test Case 3: Failure in Code Generation ---")
    codegen_failure_result = {
        "status": "FAILURE_CODE_GENERATION",
        "message": "Failed to generate syntactically valid code after initial attempt.",
        "generated_code": None,
        "validation_feedback": ["Initial code generation resulted in a syntax error."],
    }
    output_deliverer.deliver_output(codegen_failure_result)

    test_logger.info("OutputDeliveryModule example finished.") 