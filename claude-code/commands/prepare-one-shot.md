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
- **CRITICAL**: Structure plan to maximize parallel execution
- Group all independent tasks for simultaneous execution via Task tool

### Issue Creation Phase
Create a GitHub issue with your planning findings using `gh issue create`:
1. Title: Clear, action-oriented summary of what needs to be done
2. Body must be VERBOSE and include:
   - **Problem**: Specific technical problem with code references
   - **Current State**: 
     - Exact files and line numbers that need changes
     - Current implementation details with code snippets
     - Specific functions/classes/modules affected
   - **Proposed Changes**:
     - File-by-file breakdown of modifications needed
     - New files to create with their purpose
     - Functions to add/modify/remove with signatures
     - Specific code patterns to implement
   - **Implementation Tasks** (with file paths):
     - Task 1: Create `path/to/file.ts` with XYZ functionality
     - Task 2: Modify `existingFile.ts:45-67` to add ABC method
     - Task 3: Update `config.json` to include new settings
   - **Technical Specifications**:
     - API endpoints with routes and payloads
     - Database schema changes with field types
     - Dependencies to add with versions
     - Configuration changes needed
   - **Testing Requirements**:
     - Specific test files to create/update
     - Test cases that must pass
     - Performance benchmarks if applicable
   - **Acceptance Criteria**:
     - Concrete, measurable outcomes
     - Specific commands that should work
     - Expected behavior with examples

Include code blocks, file paths, line numbers, and concrete implementation details. NO vague descriptions.

IMPORTANT: Only use `gh` CLI for all GitHub interactions (issues, PRs, checks). Never use fetch, curl, or web requests as repos may be private.

### Implementation Phase
1. Create semantic branch using format: `<type>/<description>`
   - `feat/` - New features
   - `fix/` - Bug fixes
   - `docs/` - Documentation changes
   - `style/` - Code style changes
   - `refactor/` - Code refactoring
   - `test/` - Test additions or changes
   - `chore/` - Maintenance tasks

2. **CRITICAL - PARALLEL IMPLEMENTATION REQUIRED**:
   - **MUST use the Task tool** to execute multiple independent tasks simultaneously
   - **NEVER execute tasks sequentially** unless there are explicit dependencies
   - **ALWAYS group independent tasks** for parallel execution
   - **MAXIMIZE parallelization** - if 5 tasks can run independently, launch ALL 5 at once
   - Example: If implementing a feature that needs:
     - Database schema changes
     - API endpoint creation
     - Frontend component updates
     - Test file creation
     - Documentation updates
   - ALL of these should be launched as parallel Task invocations in a single message
   
3. For each parallel task group:
   - Make atomic, focused commits for each completed subtask
   - Run tests and linting after implementation
   - Fix any failures before proceeding
   
**FAILURE TO USE PARALLEL TASKS WILL RESULT IN INEFFICIENT IMPLEMENTATION**

### PR Creation Phase
1. Push branch to remote
2. Create PR using `gh pr create` with this exact format:

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
- **PARALLEL EXECUTION MANDATORY** - MUST use Task tool for parallel implementation
- **Minimal PR** - Keep PR description under 10 lines
- **Smart timeouts** - Set appropriate timeout parameter when calling Bash tool based on expected duration
- **Fix until green** - Continue fixing and monitoring until CI passes
- **One continuous flow** - Complete everything without stopping
- **GitHub via gh only** - All GitHub interactions MUST use `gh` CLI, never use curl/fetch/web requests