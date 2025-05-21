# Init Component AI Docs

## Overview
This command initializes AI documentation for a specific component/directory within a project. It analyzes the local codebase to create component-specific rules and documentation while referencing the project-wide rules.

## Important Notes
- Claude MUST NOT alter the parent component rules.
- Claude MUST NOT repeat rules from the parent component.
- Claude MUST NOT add rules that are not specific to this component.
- Claude MUST keep the rules focused and concise.
- Claude MUST NOT touch any files outside of the component directory.
- Claude MUST ONLY alter the following files:
  - $component-dir/CURSOR.mdc
  - $component-dir/CLAUDE.md
  - $PROJECT_ROOT/.cursor/rules/$component-dir/$component.mdc which is a symbolic link to $COMPONENT_DIR/CURSOR.mdc

## Arguments
Arguments are passed as key=value pairs in `$ARGUMENTS`.

Expected format: `project-root=../path/to/project,component-dir=.`

**Parsing Instructions:**
Extract values from `$ARGUMENTS`:
- `project-root`: The relative path to the project root directory (from the component's perspective)
- `component-dir`: The component directory being processed (typically `.` since claude runs from component dir)

Parse these from the comma-separated key=value format in `$ARGUMENTS`. If the project-root is not provided, you MUST exit with an error.

**Working Directory:**
Claude will be executed from the component directory, so:
- `component-dir` will typically be `.` (current directory)
- `project-root` will be a relative path like `..` or `../..` 
- All generated documentation should use relative paths (like `./CURSOR.mdc`)

**Path Handling Rules:**
- Use relative paths for all file operations and documentation
- NEVER include absolute paths like `/Users/username/...` in generated documentation files
- All paths in generated files should be relative to the component directory

**Command Arguments:** `$ARGUMENTS`

## Tasks

### TASK 0: Echo the arguments
Echo the arguments to the console.

### TASK 1: Analyze Component Codebase
Analyze the current component directory to understand the HIGH-LEVEL strategic patterns only:
- Claude MUST NOT review any files outside of the current directory. That includes any files in subdirectories. Only analyze files in the current directory.
- What this component's PRIMARY PURPOSE is (one clear sentence)
- What KEY INTEGRATION PATTERNS it uses (e.g. "supports multiple execution clients", "implements retry logic", "uses event-driven architecture")
- What IMPORTANT CONSTRAINTS or DESIGN DECISIONS apply (e.g. "stateless design", "concurrent operations", "backwards compatibility required")
- DO NOT enumerate every file, function, or feature - focus on the architectural essence

### TASK 2: Analyze Parent Component Rules
Analyze ONLY the direct parent component rules in the path from project root to current component. 

**IMPORTANT - Direct Path Only:**
- Start at the project root (.cursor/rules/)
- Follow ONLY the direct path to the current component directory
- Do NOT read rules from sibling directories or unrelated components
- Only read rules from directories that are direct ancestors in the path

**Example:** For component at `backend/services/auth/`:
- ✅ Read: Project root `.cursor/rules/`
- ✅ Read: `backend/CURSOR.mdc` (if exists)
- ✅ Read: `backend/services/CURSOR.mdc` (if exists)
- ❌ Don't read: `frontend/CURSOR.mdc` (sibling)
- ❌ Don't read: `backend/handlers/CURSOR.mdc` (sibling)
- ❌ Don't read: `backend/services/user/CURSOR.mdc` (sibling)

This ensures you have knowledge of parent rules without polluting context with unrelated component rules.

### TASK 3: Create a component-specific cursor rules file.
Based on the analysis, create a SLIM, focused cursor rules file. Using your knowledge of the parent component rules, only add rules that are specific and unique to this component. Keep this concise - focus on the 2-3 most important strategic patterns that someone working on this component needs to know.

This file will live in ./CURSOR.mdc

**IMPORTANT: Include glob patterns for auto-attachment**
The MDC file MUST include appropriate glob patterns in the frontmatter to automatically attach these rules when relevant files are being worked on.

Example frontmatter:
```yaml
---
description: [COMPONENT_NAME] - [ONE SENTENCE PURPOSE]
globs: 
  - "*.go"
  - "**/*_test.go"
alwaysApply: false
---
```

**Content Guidelines - Keep it SLIM:**
- **Primary Purpose**: One clear sentence about what this component does
- **Key Integration Pattern**: The main architectural approach (e.g. "Supports multiple Ethereum execution clients via adapter pattern")
- **Important Constraints**: 1-2 critical design decisions or limitations
- **DO NOT include**: Exhaustive lists, detailed file structures, comprehensive feature catalogs
- **Target**: 10-20 lines of actual guidance, not documentation

**Example - What we WANT:**
```
Execution client connector that supports multiple Ethereum clients via adapter pattern.
- Use ClientAdapter interface for all client implementations
- Maintain connection pooling for high-throughput operations
- Always include retry logic with exponential backoff
```

**Example - What we DON'T want:**
```
This component includes the following files:
- client.go - defines the main client struct
- adapters/ - contains adapters for Geth, Besu, Nethermind, Erigon
- pool.go - implements connection pooling
- retry.go - implements retry logic
- config.go - handles configuration
... [exhaustive file listing]
```

### TASK 4: Create Component CLAUDE.md
Create a MINIMAL `./CLAUDE.md` file in the current directory:

**IMPORTANT**: The CLAUDE.md file must use relative paths, not absolute paths. Keep this file extremely minimal - just the component name, one-sentence purpose, and reference to the CURSOR.mdc file.

### TASK 5: Create a symbolic link to the CURSOR.mdc file in the project root
Create a symbolic link to the CURSOR.mdc file in the project root. This is so that the project root .cursor/rules/ directory can read the component's CURSOR.mdc file.

**Template:**
```markdown
# {{ COMPONENT_NAME }}

{{ ONE_SENTENCE_PURPOSE }}

## Architecture  
Claude MUST read the `./CURSOR.mdc` file before making any changes to this component.
```

## Cursor Rules Docs
```
Cursor Rules are stored in .cursor/rules/$file.mdc. Large language models do not retain memory between completions. Rules solve this by providing persistent, reusable context at the prompt level. When a rule is applied, its contents are included at the start of the model context. This gives the AI consistent guidance whether it is generating code, interpreting edits, or helping with a workflow
​
Use project rules to:
- Encode domain-specific knowledge about the codebase
- Automate project-specific workflows or templates
- Standardize style or architecture decisions

### Rule structure
Each rule file is written in MDC (.mdc), a lightweight format that supports metadata and content in a single file. Rules supports the following types:

Rule Type - Description
Always - Always included in the model context
Auto Attached - Included when files matching a glob pattern are referenced
Agent Requested - Rule is available to the AI, which decides whether to include it. Must provide a description
Manual - Only included when explicitly mentioned using @ruleName
​
Example MDC rule
#######
---
description: RPC Service boilerplate
globs: 
alwaysApply: false
---

- Use our internal RPC pattern when defining services
- Always use snake_case for service names.

@service-template.ts
########

## Nested rules
You can organize rules by placing them in .cursor/rules directories throughout your project structure. Perfect for organizing domain-specific rules closer to their relevant code. This is particularly useful in monorepos or projects with distinct components that need their own specific guidance. For example:

project/
  .cursor/rules/        # Project-wide rules
  backend/
    server/
      .cursor/rules/    # Backend-specific rules
  frontend/
    .cursor/rules/      # Frontend-specific rules

## Best practices
Good rules are focused, actionable, and scoped.

- Keep rules concise. Under 500 lines is a good target
- Split large concepts into multiple, composable rules
- Provide concrete examples or referenced files when helpful
- Avoid vague guidance. Write rules the way you would write a clear internal doc
- Reuse rules when you find yourself repeating prompts in chat

```