# Prepare One-Shot

You are now in one-shot implementation mode. You MUST:

## Step 1: Acknowledge
Respond with exactly:
```
Ready for one-shot implementation. Please provide your implementation request.
```

## Step 2: Wait for User Input
Wait for the user to provide their implementation request.

## Step 3: Execute One-Shot Implementation
When the user provides their request, execute WITHOUT asking for confirmation:

### Planning Phase (Internal - DO NOT OUTPUT)
- Research the codebase using parallel searches
- Create an internal implementation plan
- Identify all tasks and dependencies
- Structure for maximum parallelization

### Issue Creation Phase
Create a GitHub issue with your planning findings:
1. Title: Clear, action-oriented summary of what needs to be done
2. Body must include:
   - **Problem**: What needs to be solved/implemented (synthesized, not user's direct text)
   - **Context**: Current state of the codebase relevant to this change
   - **Proposed Solution**: Technical approach based on your research
   - **Implementation Plan**: High-level tasks that need to be completed
   - **Acceptance Criteria**: What defines this issue as complete
   - **Technical Details**: Any specific considerations, dependencies, or constraints discovered during planning

The issue should be self-contained - someone reading it should understand exactly what needs to be done without any additional context.

### Implementation Phase
1. Create semantic branch using format: `<type>/<description>`
   - `feat/` - New features
   - `fix/` - Bug fixes
   - `docs/` - Documentation changes
   - `style/` - Code style changes
   - `refactor/` - Code refactoring
   - `test/` - Test additions or changes
   - `chore/` - Maintenance tasks

2. Implement changes using parallel subtasks:
   - Use the Task tool to execute multiple independent tasks simultaneously
   - Group tasks that have no dependencies for parallel execution
   - Execute all subtasks with maximum parallelization
   - Make atomic, focused commits for each completed subtask
   - Run tests and linting after implementation
   - Fix any failures before proceeding

### PR Creation Phase
1. Push branch to remote
2. Create PR with this exact format:

```markdown
## What
- [Concise description of changes]

## Why
- [Brief explanation of the reason]

## Changes
- [Bullet points of key changes]

Closes #[issue-number]
```

### CI Monitoring & Conflict Resolution Phase
After creating the PR:
1. Monitor PR status for both CI and merge conflicts:
   - Check CI status using `gh pr checks` (use Bash tool with appropriate timeout based on expected CI duration)
   - Check merge status using `gh pr view --json mergeable,mergeStateStatus`
   
2. Handle merge conflicts if detected:
   - Pull latest changes from target branch
   - Resolve conflicts automatically by understanding the intent of both changes
   - Commit conflict resolution
   - Push to update PR
   
3. If CI is still running, continue monitoring with appropriate intervals

4. If CI fails:
   - Analyze the failure logs using `gh pr checks --fail-only`
   - Determine if failure is transient (timeout, network issue) or code-related
   - For transient failures: Trigger retry using `gh run rerun --failed`
   - For code failures: 
     - Fix the issues locally
     - Commit and push fixes
     - Continue monitoring CI
     
5. Repeat monitoring for both CI and conflicts until:
   - CI passes AND no merge conflicts exist
   - Maximum retry attempts reached for transient failures (3 attempts)

IMPORTANT: When using the Bash tool for CI monitoring commands, always specify an appropriate timeout parameter based on the expected CI job duration to avoid premature timeouts

## Critical Rules
- **NO planning output** - Keep all planning internal
- **NO confirmations** - Execute the entire workflow automatically
- **Minimal PR** - Keep PR description under 10 lines
- **Smart timeouts** - Set appropriate timeout parameter when calling Bash tool based on expected duration
- **Fix until green** - Continue fixing and monitoring until CI passes
- **One continuous flow** - Complete everything without stopping