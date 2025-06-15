# Create Feedback Loop

This command instructs Claude to create a temporary, single-use feedback loop for iterating on a specific change until a success condition is met. The feedback loop is throwaway and designed for one-off tasks.

## Usage

Simply tell Claude what change you want to make, and Claude will:
1. Ask you how to verify the change succeeded (if not obvious)
2. Create a minimal Python script to manage the feedback loop
3. Run iterations until the assertion passes or max attempts reached

## Examples

```
"Create a feedback loop to make all tests pass"
"I want the server to handle 1000 concurrent connections - create a feedback loop"
"Make a feedback loop that ensures the README has proper formatting"
```

## Implementation Instructions for Claude

When this command is invoked, follow these steps:

**CRITICAL**: When running the feedback loop script with the Bash tool, you MUST set an appropriate timeout. The default 2-minute timeout is almost never sufficient for feedback loops. Calculate the timeout based on the task complexity and number of iterations.

### 1. Understand the Goal
Ask the user clarifying questions if needed:
- What specific change or improvement do they want?
- How can we programmatically verify success?
- Are there any constraints or areas to focus on?
- What's the maximum time/iterations they're comfortable with?

### 2. Create the Feedback Loop Script

Create a single Python file `feedback_loop_temp.py` with this structure:

```python
#!/usr/bin/env python3
"""
Temporary feedback loop for: [USER'S GOAL]
This script will iterate with Claude until the assertion passes.
"""

import subprocess
import json
import sys
import time
import os
from datetime import datetime
from pathlib import Path

class FeedbackLoop:
    def __init__(self):
        self.goal = "[USER'S GOAL]"
        self.max_iterations = 5
        self.iteration = 0
        self.start_time = datetime.now()
        self.log_file = f"feedback_loop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
    def test_condition(self):
        """Test if the goal has been achieved."""
        try:
            # [CUSTOM TEST LOGIC BASED ON USER'S ASSERTION]
            # Examples:
            # - Run tests: subprocess.run(["pytest"], check=True)
            # - Check output: result = subprocess.run(["./myapp"], capture_output=True)
            # - Verify file: assert Path("output.txt").exists()
            # - Custom check: return check_custom_condition()
            
            # Return True if success, False if not there yet
            return False
        except Exception as e:
            self.log(f"Test failed: {e}")
            return False
    
    def get_context(self):
        """Gather context for Claude about the current state."""
        context = {
            "goal": self.goal,
            "iteration": self.iteration,
            "test_output": self.last_test_output,
            "relevant_files": self.get_relevant_files(),
            "error_details": self.last_error
        }
        
        # [ADD CUSTOM CONTEXT GATHERING]
        # Examples:
        # - Git diff: subprocess.run(["git", "diff"])
        # - Log files: Path("app.log").read_text()[-1000:]
        # - System state: current metrics, etc.
        
        return context
    
    def get_relevant_files(self):
        """Identify files Claude should focus on."""
        # [CUSTOMIZE BASED ON USER'S TASK]
        # Return list of file paths or patterns
        return []
    
    def call_claude(self, context):
        """Call Claude with the current context."""
        prompt = f'''
Goal: {self.goal}

Current iteration: {self.iteration}/{self.max_iterations}

The test condition is currently failing. Here's the context:
{json.dumps(context, indent=2)}

Please analyze the situation and make the necessary changes to achieve the goal.
Focus on: {self.get_relevant_files()}

Important:
- Make minimal, targeted changes
- Explain your reasoning briefly
- Focus on making the test pass
'''
        
        # Call Claude CLI
        cmd = ["claude", "--json"]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=prompt)
        
        if process.returncode != 0:
            self.log(f"Claude call failed: {stderr}")
            return False
            
        # Parse Claude's response
        try:
            for line in stdout.strip().split('\n'):
                if line.strip():
                    data = json.loads(line)
                    if data.get("type") == "text":
                        self.log(f"Claude: {data.get('text', '')[:200]}...")
        except json.JSONDecodeError:
            self.log("Failed to parse Claude response")
            
        return True
    
    def log(self, message):
        """Log to file and console."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, "a") as f:
            f.write(log_entry + "\n")
    
    def run(self):
        """Main feedback loop."""
        self.log(f"Starting feedback loop for: {self.goal}")
        
        while self.iteration < self.max_iterations:
            self.iteration += 1
            self.log(f"\n--- Iteration {self.iteration} ---")
            
            # Test current state
            self.log("Testing condition...")
            if self.test_condition():
                self.log("✓ Success! Goal achieved.")
                return True
            
            # Get context and call Claude
            self.log("Condition not met. Gathering context...")
            context = self.get_context()
            
            self.log("Calling Claude for assistance...")
            if not self.call_claude(context):
                self.log("Failed to get Claude's help. Retrying...")
                continue
            
            # Wait for changes to take effect
            self.log("Waiting for changes to take effect...")
            time.sleep(5)
        
        self.log(f"\n✗ Max iterations ({self.max_iterations}) reached without success.")
        return False
    
    def cleanup(self):
        """Clean up temporary files if needed."""
        # Add any cleanup logic here
        pass

if __name__ == "__main__":
    loop = FeedbackLoop()
    try:
        success = loop.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        loop.log("\nInterrupted by user")
        sys.exit(130)
    finally:
        loop.cleanup()
```

### 3. Customize the Script

Based on the user's requirements, modify:

1. **test_condition()**: Implement the specific assertion
   - Exit code checks: `subprocess.run(cmd, check=True)`
   - Output validation: Check stdout contains expected text
   - File existence: Verify files are created/modified
   - API calls: Test endpoints return expected results
   - Performance: Measure and compare metrics

2. **get_context()**: Add relevant information
   - Error messages and stack traces
   - Recent changes (git diff)
   - Log file excerpts
   - System state/metrics

3. **get_relevant_files()**: Specify focus areas
   - Source files to modify
   - Test files to fix
   - Configuration files

### 4. Example Implementations

#### Example 1: Make Tests Pass
```python
def test_condition(self):
    result = subprocess.run(["go", "test", "./..."], capture_output=True, text=True)
    self.last_test_output = result.stdout + result.stderr
    self.last_error = result.stderr
    return result.returncode == 0
```

#### Example 2: Performance Goal
```python
def test_condition(self):
    # Run performance test
    result = subprocess.run(["./load-test.sh"], capture_output=True, text=True)
    
    # Parse output for metrics
    import re
    match = re.search(r"Requests/sec:\s+(\d+)", result.stdout)
    if match:
        rps = int(match.group(1))
        self.last_test_output = f"Current: {rps} req/s (target: 1000)"
        return rps >= 1000
    return False
```

#### Example 3: File Format Validation
```python
def test_condition(self):
    # Check markdown formatting
    result = subprocess.run(["markdownlint", "README.md"], capture_output=True)
    self.last_test_output = result.stdout.decode()
    return result.returncode == 0
```

### 5. Run and Monitor

After creating the script:

1. Make it executable: `chmod +x feedback_loop_temp.py`
2. Run it with an appropriate timeout: 
   - **IMPORTANT**: Set a custom timeout based on the complexity of the task
   - The default 2-minute timeout is insufficient for feedback loops
   - Calculate timeout as: `(max_iterations × estimated_time_per_iteration) + buffer`
   - Example: For 5 iterations with ~3 minutes each, use 20 minutes (1200000ms)
   ```bash
   # Run with 20-minute timeout for complex tasks
   ./feedback_loop_temp.py  # Use Bash tool with timeout=1200000
   
   # For simpler tasks, 10 minutes might suffice
   ./feedback_loop_temp.py  # Use Bash tool with timeout=600000
   ```
3. Monitor the output and log file
4. The script will iterate until success or max attempts

### 6. Important Patterns

When implementing the feedback loop:

1. **Start Simple**: Basic assertion first, add complexity if needed
2. **Clear Feedback**: Ensure test output clearly shows what's wrong
3. **Focused Context**: Only include relevant information for Claude
4. **Safety Bounds**: Set reasonable iteration limits
5. **Logging**: Keep detailed logs for debugging

### 7. Quick Templates

For common scenarios, use these templates:

**Command Success**:
```python
def test_condition(self):
    return subprocess.run(self.test_command.split(), capture_output=True).returncode == 0
```

**Output Contains**:
```python
def test_condition(self):
    result = subprocess.run(self.test_command.split(), capture_output=True, text=True)
    return self.expected_output in result.stdout
```

**File Exists**:
```python
def test_condition(self):
    return Path(self.target_file).exists() and Path(self.target_file).stat().st_size > 0
```

**JSON Validation**:
```python
def test_condition(self):
    try:
        with open(self.json_file) as f:
            data = json.load(f)
        return self.validate_json_structure(data)
    except:
        return False
```

### 8. Cleanup

The script is designed to be temporary. After success:
- Review the log file for the solution path
- Delete `feedback_loop_temp.py` 
- Keep or delete logs as needed

Remember: This is a throwaway script for a single task. Each new goal gets a fresh implementation tailored to its specific needs.