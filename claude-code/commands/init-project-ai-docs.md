# Init Project AI Docs

## Overview
This command initializes top-level AI documentation for the entire project.  It should provide an executive summary of the project, and a high-level overview of the project structure. If any of the files already exist, you should read them, and update them with the new information if there is significant changes. It creates the foundational structure and project-wide documentation. The bulk of component-specific documentation is handled by the `init-component-ai-docs` command, which is typically called automatically by the `init-ai-docs` script.

## Arguments
Arguments are passed as `project-root=/path/to/project` in `$ARGUMENTS`.

Expected format: `project-root=/absolute/path/to/project/root`


**Parsing Instructions:**
Extract the project-root value from `$ARGUMENTS`. The format will be `project-root=/path/to/project`. Parse this to get the absolute path to use throughout the command. If the project-root is not provided, use the current directory.

**Command Arguments:** `$ARGUMENTS`

## Tasks

### TASK 1: Setup Directory Structure
Create the foundational directory structure:
- Create symbolic link from `./llms` to `.cursor` 
- Create symbolic link from `./.roo` to `.cursor`
- Ensure `.cursor/rules/` directory exists

### TASK 2: Create Project-Level Rules
Create high-level cursor rules that apply to the entire project:

1. **Project Architecture** (`.cursor/rules/project_architecture.mdc`):
   - Overall project structure and organization
   - Main technologies and frameworks used
   - Build systems and tooling
   - Deployment patterns

2. **Code Standards** (`.cursor/rules/code_standards.mdc`):
   - Language-specific coding conventions
   - Naming conventions
   - File organization patterns
   - Documentation standards

3. **Development Workflow** (`.cursor/rules/development_workflow.mdc`):
   - Git workflow and branching strategy
   - Testing requirements and patterns
   - CI/CD pipeline expectations
   - Code review guidelines

### TASK 3: Update Root CLAUDE.md
Create the content of `./CLAUDE.md` with a project overview that references the main rules:

```markdown
# {{ PROJECT_NAME }}

{{ PROJECT_DESCRIPTION }}

## Project Structure
Claude MUST read the `.cursor/rules/project_architecture.mdc` file before making any structural changes to the project.

## Code Standards  
Claude MUST read the `.cursor/rules/code_standards.mdc` file before writing any code in this project.

## Development Workflow
Claude MUST read the `.cursor/rules/development_workflow.mdc` file before making changes to build, test, or deployment configurations.

## Component Documentation
Individual components have their own CLAUDE.md files with component-specific rules. Always check for and read component-level documentation when working on specific parts of the codebase.
```


## Rules
- The rules should be in the Cursor Rules format.
- The rules should be in the current project.
- Rules should be adequately scoped to the area of the codebase.

## Docs
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