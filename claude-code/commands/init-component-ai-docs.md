# Init Component AI Docs

## Overview
This command initializes AI documentation for a specific component/directory within a project. It analyzes the local codebase to create component-specific rules and documentation while referencing the project-wide rules.

## Important Notes
- Claude MUST NOT alter the parent component rules.
- Claude MUST NOT repeat rules from the parent component.
- Claude MUST NOT add rules that are not specific to this component.
- Claude MUST NOT add rules that are not relevant to this component.
- Claude MUST NOT touch any files outside of the component directory.
- Claude MUST ONLY alter the following files:
  - $PROJECT_ROOT/$component-dir/CURSOR.mdc
  - $PROJECT_ROOT/$component-dir/CLAUDE.md
  - $PROJECT_ROOT/.cursor/rules/$component-dir/$component.mdc which is a symbolic link to $PROJECT_ROOT/$component-dir/CURSOR.mdc

## Arguments
Arguments are passed as key=value pairs in `$ARGUMENTS`.

Expected format: `project-root=/path/to/project,component-dir=/path/to/component`

**Parsing Instructions:**
Extract values from `$ARGUMENTS`:
- `project-root`: The absolute path to the project root directory
- `component-dir`: The absolute path to the component directory being processed

Parse these from the comma-separated key=value format in `$ARGUMENTS`. If the project-root is not provided, you MUST exit with an error.

**Command Arguments:** `$ARGUMENTS`

## Tasks

### TASK 0: Echo the arguments
Echo the arguments to the console.

### TASK 1: Analyze Component Codebase
Analyze the current component directory to understand:
- What this component does (purpose and functionality)
- File structure and organization patterns
- Key technologies, frameworks, and dependencies used
- Interfaces and APIs exposed or consumed
- Testing patterns and strategies
- Any unique patterns or conventions specific to this component

### TASK 2: Analyze Parent Component Rules
Analyze the parent component rules recursively, adding them to your context for later use. To do thie effectively, you should start at the project root, and work your way down to the component directory.

### TASK 3: Create a component-specific cursor rules file.
Based on the analysis, create a focused cursor rules file for this component. Using your knowledge of the parent component rules, only add rules that are specific and unique to this component. These rules should be concise, composable, and focused. Only add rules are are relevent, and DO NOT REPEAT RULES FROM THE PARENT COMPONENT. The rules file must correctly define _when_ the agent should use the rules, and _what_ the rules are for.

This file will live in $PROJECT_ROOT/$component-dir/CURSOR.mdc

1. **Component Architecture**
   - Component purpose and responsibilities
   - Internal structure and organization
   - Dependencies and interfaces
   - Key design patterns used

2. **Component Patterns**
   - Coding patterns specific to this component
   - Error handling approaches
   - Logging and monitoring patterns
   - Performance considerations

3. **Component Testing** (if tests exist):
   - Testing approach and frameworks used
   - Test organization and naming conventions
   - Mocking and fixture patterns
   - Test data management

### TASK 3: Create Component CLAUDE.md
Create a `./CLAUDE.md` file at $PROJECT_ROOT/$component-dir/CLAUDE.md that serves as the entry point for this component:

```markdown
# {{ COMPONENT_NAME }}

{{ COMPONENT_DESCRIPTION }}

##  Architecture  
Claude MUST read the `$PROJECT_ROOT/$component-dir/CURSOR.mdc` file before making any changes to this component.
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