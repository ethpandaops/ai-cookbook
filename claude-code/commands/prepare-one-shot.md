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
```

## Critical Rules
- **NO planning output** - Keep all planning internal
- **NO confirmations** - Execute the entire workflow automatically
- **Minimal PR** - Keep PR description under 10 lines
- **Fix before PR** - All tests must pass before creating PR
- **One continuous flow** - Complete everything without stopping