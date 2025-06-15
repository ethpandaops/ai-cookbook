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
        self.summary_file = f"feedback_loop_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        self.iterations_summary = []
        
    def test_condition(self):
        """Test if the goal has been achieved."""
        try:
            # [CUSTOM TEST LOGIC BASED ON USER'S ASSERTION]
            # Examples:
            # - Run tests: subprocess.run(["pytest"], check=True)
            # - Check output: result = subprocess.run(["./myapp"], capture_output=True)
            # - Verify file: assert Path("output.txt").exists()
            # - Custom check: return check_custom_condition()
            
            # Store test details for summary
            self.current_test_result = {
                "passed": False,
                "reason": "Test condition not met",
                "details": ""
            }
            
            # Return True if success, False if not there yet
            return False
        except Exception as e:
            self.log(f"Test failed: {e}")
            self.current_test_result = {
                "passed": False,
                "reason": "Exception during test",
                "details": str(e)
            }
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
- Start your response with "ANALYSIS:" followed by a brief explanation of what's wrong
- Then use "CHANGES:" followed by what you're going to change
'''
        
        # Store for summary
        self.current_claude_analysis = ""
        self.current_changes_made = []
        
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
            
        # Parse Claude's response and extract summary info
        try:
            full_response = []
            for line in stdout.strip().split('\n'):
                if line.strip():
                    data = json.loads(line)
                    if data.get("type") == "text":
                        text = data.get('text', '')
                        full_response.append(text)
                        self.log(f"Claude: {text[:200]}...")
            
            # Extract analysis and changes from response
            response_text = '\n'.join(full_response)
            if "ANALYSIS:" in response_text:
                analysis_start = response_text.find("ANALYSIS:") + 9
                analysis_end = response_text.find("CHANGES:") if "CHANGES:" in response_text else len(response_text)
                self.current_claude_analysis = response_text[analysis_start:analysis_end].strip()[:200]
            
            if "CHANGES:" in response_text:
                changes_start = response_text.find("CHANGES:") + 8
                self.current_changes_made = response_text[changes_start:].strip()[:200].split('\n')[:3]
                
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
    
    def save_iteration_summary(self):
        """Save summary of current iteration."""
        summary = {
            "iteration": self.iteration,
            "test_result": self.current_test_result,
            "claude_analysis": self.current_claude_analysis,
            "changes_made": self.current_changes_made
        }
        self.iterations_summary.append(summary)
    
    def write_final_summary(self, success):
        """Write concise summary of all iterations."""
        with open(self.summary_file, "w") as f:
            f.write(f"# Feedback Loop Summary\n\n")
            f.write(f"**Goal**: {self.goal}\n")
            f.write(f"**Result**: {'✓ SUCCESS' if success else '✗ FAILED'}\n")
            f.write(f"**Total Iterations**: {self.iteration}\n")
            f.write(f"**Duration**: {(datetime.now() - self.start_time).total_seconds():.1f}s\n\n")
            
            f.write("## Iteration Details\n\n")
            
            for summary in self.iterations_summary:
                f.write(f"### Iteration {summary['iteration']}\n")
                f.write(f"**What Failed**: {summary['test_result']['reason']}")
                if summary['test_result']['details']:
                    f.write(f" - {summary['test_result']['details'][:100]}")
                f.write("\n")
                
                if summary['claude_analysis']:
                    f.write(f"**Claude's Analysis**: {summary['claude_analysis']}\n")
                
                if summary['changes_made']:
                    f.write(f"**Changes Made**: ")
                    if len(summary['changes_made']) == 1:
                        f.write(summary['changes_made'][0])
                    else:
                        f.write("\n")
                        for change in summary['changes_made'][:3]:
                            if change.strip():
                                f.write(f"- {change.strip()}\n")
                f.write("\n")
            
            if success:
                f.write("## Success\n")
                f.write("The goal was achieved in the final iteration.\n")
            
        self.log(f"Summary written to: {self.summary_file}")
    
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
                self.current_test_result = {"passed": True, "reason": "Goal achieved", "details": ""}
                self.save_iteration_summary()
                self.write_final_summary(True)
                return True
            
            # Get context and call Claude
            self.log("Condition not met. Gathering context...")
            context = self.get_context()
            
            self.log("Calling Claude for assistance...")
            if not self.call_claude(context):
                self.log("Failed to get Claude's help. Retrying...")
                self.current_claude_analysis = "Failed to get Claude response"
                self.current_changes_made = ["No changes - Claude call failed"]
            
            # Save iteration summary
            self.save_iteration_summary()
            
            # Wait for changes to take effect
            self.log("Waiting for changes to take effect...")
            time.sleep(5)
        
        self.log(f"\n✗ Max iterations ({self.max_iterations}) reached without success.")
        self.write_final_summary(False)
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
    
    if result.returncode != 0:
        # Extract first failing test for summary
        lines = result.stdout.split('\n')
        failing_test = next((line for line in lines if 'FAIL' in line), 'Tests failed')
        self.current_test_result = {
            "passed": False,
            "reason": "Tests failed",
            "details": failing_test[:100]
        }
        return False
    
    self.current_test_result = {"passed": True, "reason": "All tests passing", "details": ""}
    return True
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
        
        if rps < 1000:
            self.current_test_result = {
                "passed": False,
                "reason": "Performance below target",
                "details": f"{rps} req/s (need 1000+)"
            }
            return False
        
        self.current_test_result = {"passed": True, "reason": "Performance target met", "details": f"{rps} req/s"}
        return True
    
    self.current_test_result = {"passed": False, "reason": "Could not parse performance metrics", "details": ""}
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

### 8. Summary Output

The feedback loop creates a concise summary file (`feedback_loop_summary_[timestamp].md`) that shows:
- Overall result and duration
- For each iteration:
  - What failed (with specific error/reason)
  - Claude's analysis of the problem
  - What changes were made

Example summary:
```markdown
# Feedback Loop Summary

**Goal**: Make all tests pass
**Result**: ✓ SUCCESS
**Total Iterations**: 3
**Duration**: 245.3s

## Iteration Details

### Iteration 1
**What Failed**: Tests failed - TestUserAuth failing: expected 200, got 401
**Claude's Analysis**: The authentication middleware is not properly configured...
**Changes Made**: Added JWT token validation to auth middleware

### Iteration 2
**What Failed**: Tests failed - TestDatabase connection timeout
**Claude's Analysis**: Database connection pool settings are too restrictive...
**Changes Made**: Increased connection pool size and timeout values
...
```

### 9. Cleanup

The script is designed to be temporary. After success:
- Review the summary file for a concise overview of what was done
- Check the detailed log file if you need more information
- Delete `feedback_loop_temp.py` 
- Keep or delete logs/summaries as needed

Remember: This is a throwaway script for a single task. Each new goal gets a fresh implementation tailored to its specific needs.