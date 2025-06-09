# Placeholder for Feedback & Iteration Control Module 

from .logging_module import LoggingModule

class FeedbackControlModule:
    def __init__(self, logger: LoggingModule, max_retries: int = 3):
        self.logger = logger
        self.max_retries = max_retries

    def prepare_for_retry(self, original_prompt: str, validation_feedback: list[str], current_retry_attempt: int) -> dict:
        """
        Analyzes validation failures and refines the prompt for a retry attempt.
        Checks if retry limits have been exceeded.
        
        Args:
            original_prompt: The prompt that led to the last failed attempt.
            validation_feedback: A list of feedback strings from the OutputValidationModule.
            current_retry_attempt: The number of retries already attempted for this task.

        Returns:
            A dictionary containing:
            - "should_retry" (bool): Whether another attempt should be made.
            - "refined_prompt" (str | None): The new prompt with error context, or None if no retry.
            - "next_retry_attempt" (int): The updated retry attempt count.
        """
        self.logger.info(f"Feedback control: Analyzing failure for retry attempt {current_retry_attempt + 1}.")

        if current_retry_attempt >= self.max_retries:
            self.logger.warning(f"Maximum retry limit ({self.max_retries}) reached. No more retries.")
            return {"should_retry": False, "refined_prompt": None, "next_retry_attempt": current_retry_attempt}

        # Refine the prompt by adding the validation feedback
        feedback_summary = "\n".join(validation_feedback)
        refined_prompt = (
            f"{original_prompt}\n\n"
            f"--- Previous Attempt Feedback ---\n"
            f"The previous attempt to generate and run code based on the above instructions failed with the following issues:\n"
            f"{feedback_summary}\n"
            f"Please analyze this feedback and provide a corrected version of the code.\n"
            f"--- End of Feedback ---"
        )
        
        self.logger.info("Prompt refined with error feedback for next attempt.")
        self.logger.info(f"Refined prompt: {refined_prompt}")
        
        return {"should_retry": True, "refined_prompt": refined_prompt, "next_retry_attempt": current_retry_attempt + 1}

if __name__ == '__main__':
    test_logger = LoggingModule(log_level='DEBUG')
    feedback_controller = FeedbackControlModule(logger=test_logger, max_retries=2)

    original_prompt = "Create a function to add two numbers."
    
    # Test Case 1: First failure, should retry
    print("--- Test Case 1: First Failure ---")
    feedback1 = ["Execution failed: ZeroDivisionError", "Stdout mismatch"]    
    retry_attempt1 = 0
    result1 = feedback_controller.prepare_for_retry(original_prompt, feedback1, retry_attempt1)
    print(f"Result 1: Should retry? {result1['should_retry']}, Next attempt: {result1['next_retry_attempt']}")
    print(f"Refined Prompt 1 (snippet):\n{result1['refined_prompt'][:200]}...")
    assert result1["should_retry"] is True
    assert "ZeroDivisionError" in result1["refined_prompt"]
    assert result1["next_retry_attempt"] == 1

    # Test Case 2: Second failure (max_retries = 2, so this is the last attempt)
    print("\n--- Test Case 2: Second Failure (reaching max_retries) ---")
    feedback2 = ["Syntax error in generated code"]    
    retry_attempt2 = 1 # This was the first retry, so current_retry_attempt is 1
    result2 = feedback_controller.prepare_for_retry(result1['refined_prompt'], feedback2, retry_attempt2)
    print(f"Result 2: Should retry? {result2['should_retry']}, Next attempt: {result2['next_retry_attempt']}")
    print(f"Refined Prompt 2 (snippet):\n{result2['refined_prompt'][:200]}...")
    assert result2["should_retry"] is True # Still true because current_retry_attempt (1) < max_retries (2)
    assert "Syntax error" in result2["refined_prompt"]
    assert result2["next_retry_attempt"] == 2

    # Test Case 3: Third failure (exceeds max_retries = 2)
    print("\n--- Test Case 3: Third Failure (exceeding max_retries) ---")
    feedback3 = ["Another error"]    
    retry_attempt3 = 2 # This was the second retry, so current_retry_attempt is 2
    result3 = feedback_controller.prepare_for_retry(result2['refined_prompt'], feedback3, retry_attempt3)
    print(f"Result 3: Should retry? {result3['should_retry']}, Next attempt: {result3['next_retry_attempt']}")
    assert result3["should_retry"] is False
    assert result3["refined_prompt"] is None
    assert result3["next_retry_attempt"] == 2 # Stays at max_retries
    
    test_logger.info("FeedbackControlModule example finished.") 