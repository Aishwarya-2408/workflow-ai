# Placeholder for Output Delivery Module 

from .logging_module import LoggingModule
import os # Added for path operations in validation logic

class OutputDeliveryModule:
    def __init__(self, logger: LoggingModule):
        self.logger = logger

    def process_and_deliver_output(
        self, 
        final_result: dict, # This will now be the main agent's result dict
        execution_result: dict, 
        expected_stdout: str | None = None, 
        test_cases: list[dict] | None = None # Placeholder for future dynamic test cases
    ) -> dict:
        """
        Processes the raw execution results, performs basic validation (success/stdout check),
        and prepares/delivers the final output to the user.

        Args:
            final_result (dict): The main agent's overall result dictionary (will be updated with feedback).
            execution_result (dict): The raw result from the CodeExecutionModule.
            expected_stdout (str | None): The expected standard output for comparison.
            test_cases (list[dict] | None): Placeholder for dynamic test cases.

        Returns:
            dict: An updated final_result dictionary with feedback and a consolidated status.
        """
        self.logger.info("Output processing and delivery initiated.")
        self.logger.debug(f"Raw execution result for processing: {execution_result}")

        # --- Basic Execution Validation Logic (moved from OutputValidationModule) ---
        execution_passed = True # Assume pass, prove failure
        execution_feedback = []

        # 1. Check execution success (from the stricter CodeExecutionModule)
        if not execution_result.get("success", False):
            execution_passed = False
            exec_error = execution_result.get('error', "Execution reported failure with no specific error message.")
            feedback = f"Execution failed. Detail: {exec_error}"
            if execution_result.get('exit_code', 0) != 0:
                feedback += f" Exit Code: {execution_result.get('exit_code')}."
            if execution_result.get('stderr'):
                 feedback += f" Stderr: {execution_result.get('stderr')}."
            # Avoid duplicating stdout if it's already in the error message from CodeExecutionModule
            elif execution_result.get('stdout') and execution_result.get('stdout') not in exec_error:
                 feedback += f" Stdout: {execution_result.get('stdout')}."
            execution_feedback.append(feedback)
            self.logger.warning(f"Execution check failed during output processing: {feedback}")
        else:
            execution_feedback.append("Execution reported success (exit code 0, no stderr, no detected error patterns in stdout).")
            self.logger.info("Execution was reported as successful by CodeExecutionModule during output processing.")

        # 2. Compare stdout if expected_stdout is provided AND execution was initially considered successful
        if execution_passed and expected_stdout is not None:
            actual_stdout = execution_result.get("stdout", "")
            if actual_stdout == expected_stdout:
                feedback = f"Stdout matches expected output."
                execution_feedback.append(feedback)
                self.logger.info(feedback)
            else:
                execution_passed = False
                feedback = f"Stdout mismatch. Expected: '{expected_stdout}', Got: '{actual_stdout}'"
                execution_feedback.append(feedback)
                self.logger.warning(f"Execution check failed during output processing: {feedback}")
        
        # 3. Dynamic Test Case Execution (Placeholder)
        if test_cases:
            self.logger.info(f"Processing {len(test_cases)} dynamic test cases (placeholder). This does not affect main agent execution result.")
            execution_feedback.append(f"Dynamic test cases processed (placeholder - {len(test_cases)} cases). This does not affect main agent execution result.")
        
        final_status_message_from_delivery = f"Execution result (from output module): {'Passed' if execution_passed else 'Failed'}"
        self.logger.info(final_status_message_from_delivery)
        execution_feedback.insert(0, final_status_message_from_delivery) # Add overall status as first feedback item

        # Update final_result with consolidated feedback and status
        final_result["execution_feedback"] = execution_feedback
        # Only override final_result status if this module detected a failure, otherwise keep original agent status
        if not execution_passed and final_result.get("status") == "SUCCESS": # Prevent overriding actual agent failures
            final_result["status"] = "FAILURE_EXECUTION" # More specific status
            final_result["message"] = final_status_message_from_delivery # Update main message too

        # --- Existing Output Delivery Logic ---
        self.logger.info("--- Agent Run Summary ---")

        status = final_result.get("status", "UNKNOWN")
        self.logger.info(f"Status: {status}")

        if final_result.get("message"):
            print(f"Message: {final_result['message']}")
            self.logger.info(f"Message: {final_result['message']}")

        if final_result.get("generated_code"):
            self.logger.info("--- Generated Code ---")
            self.logger.info("\n" + final_result["generated_code"])
            self.logger.info("--- End of Generated Code ---")
        else:
            print("No code was successfully generated or retained.")
            self.logger.info("No code was successfully generated or retained.")

        if final_result.get("execution_stdout"):
            self.logger.info("--- Execution Output (Stdout) ---")
            self.logger.info("\n" + final_result["execution_stdout"])
            self.logger.info("--- End of Stdout ---")
        
        if final_result.get("execution_stderr"):
            self.logger.info("--- Execution Error (Stderr) ---")
            self.logger.info("\n" + final_result["execution_stderr"])
            self.logger.info("--- End of Stderr ---")

        if final_result.get("execution_feedback"):
            self.logger.info("--- Execution Feedback ---")
            for item in final_result["execution_feedback"]:
                self.logger.info(f"- {item}")
            self.logger.info("--- End of Execution Feedback ---")
        
        self.logger.info("--- End of Agent Run Summary ---")
        self.logger.info("Output delivery complete.")
        
        return final_result # Return the updated result for further use if needed in MainAgent

if __name__ == '__main__':
    test_logger = LoggingModule(log_level='DEBUG')
    output_deliverer = OutputDeliveryModule(logger=test_logger)

    # Test Case 1: Successful run (matches expected stdout)
    print("\n--- Test Case 1: Successful Run (matches expected stdout) ---")
    test_final_result_1 = {"status": "SUCCESS", "message": "Initial message."}
    exec_res1 = {"stdout": "Hello", "stderr": "", "exit_code": 0, "success": True, "error": None}
    updated_final_result_1 = output_deliverer.process_and_deliver_output(test_final_result_1, exec_res1, expected_stdout="Hello")
    print(f"Updated Final Result 1: {updated_final_result_1}")
    assert updated_final_result_1["status"] == "SUCCESS"
    assert "Execution result (from output module): Passed" in updated_final_result_1["execution_feedback"]

    # Test Case 2: Successful execution, but stdout mismatch (should fail within this module)
    print("\n--- Test Case 2: Successful Execution, Stdout Mismatch (Output Module Fail) ---")
    test_final_result_2 = {"status": "SUCCESS", "message": "Initial message.", "generated_code": "print('Hi')"}
    exec_res2 = {"stdout": "Hi", "stderr": "", "exit_code": 0, "success": True, "error": None}
    updated_final_result_2 = output_deliverer.process_and_deliver_output(test_final_result_2, exec_res2, expected_stdout="Hello")
    print(f"Updated Final Result 2: {updated_final_result_2}")
    assert updated_final_result_2["status"] == "FAILURE_EXECUTION"
    assert "Stdout mismatch" in updated_final_result_2["execution_feedback"][2]

    # Test Case 3: Execution failed from CodeExecutionModule directly (e.g. stderr populated)
    print("\n--- Test Case 3: Execution Failed (from CodeExecutionModule) ---")
    test_final_result_3 = {"status": "SUCCESS", "message": "Initial message.", "generated_code": "1/0"}
    exec_res3 = {"stdout": "", "stderr": "Error: Something went wrong", "exit_code": 1, "success": False, "error": "Error: Something went wrong"}
    updated_final_result_3 = output_deliverer.process_and_deliver_output(test_final_result_3, exec_res3)
    print(f"Updated Final Result 3: {updated_final_result_3}")
    assert updated_final_result_3["status"] == "FAILURE_EXECUTION"
    assert "Execution failed. Detail: Error: Something went wrong" in updated_final_result_3["execution_feedback"][1]

    # Test Case 4: Agent failed prior to execution (e.g. code generation failed)
    print("\n--- Test Case 4: Agent Failed Prior to Execution ---")
    test_final_result_4 = {
        "status": "FAILURE_CODE_GENERATION",
        "message": "Code generation failed.",
        "generated_code": None,
        "execution_stdout": None,
        "execution_stderr": "Error: Bad generation",
        "execution_feedback": ["Code generation failed feedback."] # Pre-existing feedback
    }
    # When execution_result is not available, the method should handle it gracefully.
    # We simulate this by passing a minimal execution_result or None as appropriate for the real call.
    # For this test, we don't want to overwrite the FAILURE_CODE_GENERATION status.
    updated_final_result_4 = output_deliverer.process_and_deliver_output(test_final_result_4, {}, expected_stdout=None)
    print(f"Updated Final Result 4: {updated_final_result_4}")
    assert updated_final_result_4["status"] == "FAILURE_CODE_GENERATION" # Status should not be overridden by this module if it's already a failure
    assert "Code generation failed feedback." in updated_final_result_4["execution_feedback"]


    test_logger.info("OutputDeliveryModule consolidated example finished.") 