# Init Component AI Docs

## Overview
This command initializes AI documentation for a specific component/directory within a project. It analyzes the local codebase to create component-specific rules and documentation while referencing the project-wide rules.

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

### TASK 1: Analyze Component Codebase
Analyze the current component directory to understand:
- What this component does (purpose and functionality)
- File structure and organization patterns
- Key technologies, frameworks, and dependencies used
- Interfaces and APIs exposed or consumed
- Testing patterns and strategies
- Any unique patterns or conventions specific to this component

### TASK 2: Create Component-Specific Rules
Based on the analysis, create focused cursor rules for this component:

1. **Component Architecture** (`.cursor/rules/component_architecture.mdc`):
   - Component purpose and responsibilities
   - Internal structure and organization
   - Dependencies and interfaces
   - Key design patterns used

2. **Component Patterns** (`.cursor/rules/component_patterns.mdc`):
   - Coding patterns specific to this component
   - Error handling approaches
   - Logging and monitoring patterns
   - Performance considerations

3. **Component Testing** (`.cursor/rules/component_testing.mdc`) - (if tests exist):
   - Testing approach and frameworks used
   - Test organization and naming conventions
   - Mocking and fixture patterns
   - Test data management

### TASK 3: Create Component CLAUDE.md
Create a `./CLAUDE.md` file that serves as the entry point for this component:

```markdown
# {{ COMPONENT_NAME }}

{{ COMPONENT_DESCRIPTION }}

## Project Context
Claude MUST read the project-wide rules from `{{ PROJECT_ROOT }}/.cursor/rules/` before making any changes. The project root is: {{ PROJECT_ROOT }}

## Component Architecture  
Claude MUST read the `.cursor/rules/component_architecture.mdc` file before making any changes to this component.

## Component Patterns
Claude MUST read the `.cursor/rules/component_patterns.mdc` file before writing code in this component.

{{ IF_TESTS_EXIST }}
## Testing
Claude MUST read the `.cursor/rules/component_testing.mdc` file before writing or modifying tests.
{{ END_IF }}

## Important Notes
- Always reference the project root documentation at {{ PROJECT_ROOT }}/CLAUDE.md for project-wide context
- Follow the component-specific patterns and conventions documented in the rules above
- When in doubt, prefer the component-specific rules over generic patterns
```

### TASK 5: Reference Project Rules
Ensure the component documentation properly references and doesn't duplicate project-level rules. The component rules should be additive and specific, not repetitive of project-wide standards.
