# init-ai-docs

The `init-ai-docs` script initializes comprehensive AI documentation for a project and all its components. It is intended to be run in another project, and will create a hierarchical documentation structure with centralized cursor rules and component-specific CLAUDE.md files. The intention is to provide a once-defined structure that is compatible with majority AI Code tools like Cursor, Roo Code, and Claude Code.

*You should be using Claude Max for care-free use of Claude Code with this script. If you aren't using Claude Max, consider contacting your mortgage broker to refinance the house -- you're going to need it.*

## Overview

The script performs two main functions:

1. **Project-level initialization**: Creates centralized cursor rules and project CLAUDE.md
2. **Component-level initialization**: Creates CLAUDE.md files in each component directory that reference the project rules

## Usage

### Basic Usage

Initialize documentation for the current directory:

```bash
init-ai-docs
```

### Specify Project Directory

Initialize documentation for a specific project:

```bash
init-ai-docs /path/to/project
```

### Preview Mode

See what will be created without executing:

```bash
init-ai-docs --dry-run
```

### Verbose Output

Get detailed execution information:

```bash
init-ai-docs --verbose
```

## Options

| Option | Description |
|--------|-------------|
| `--dry-run`, `-n` | Show what would be done without executing |
| `--verbose`, `-v` | Enable verbose output |
| `--help`, `-h` | Show help message |

## What Gets Created

### Project Root Structure

```
project-root/
├── CLAUDE.md                    # Main project documentation entry point
├── .cursor/
│   └── rules/
│       ├── project_architecture.mdc    # Project structure and technologies
│       ├── code_standards.mdc          # Coding conventions and standards
│       └── development_workflow.mdc    # Git workflow and CI/CD patterns
├── llms/ -> .cursor (symlink)
└── .roo/ -> .cursor (symlink)
```

### Component Structure

Each component directory gets:

```
component-directory/
└── CLAUDE.md                    # Component-specific documentation
```

The component CLAUDE.md files reference the project root rules and provide component-specific context.

## Planning Phase

Before creating any files, the script shows a comprehensive plan:

1. **Project scan**: Discovers all directories containing code files
2. **Tree visualization**: Shows exactly what files will be created
3. **Summary statistics**: Displays counts and estimates
4. **User confirmation**: Asks for approval before proceeding

Example plan output:

```
📋 Documentation Plan
==================

🎯 Project Root:
   ├── CLAUDE.md
   ├── .cursor/
   │   └── rules/
   │       ├── project_architecture.mdc
   │       ├── code_standards.mdc
   │       └── development_workflow.mdc
   ├── llms/ -> .cursor (symlink)
   └── .roo/ -> .cursor (symlink)

📦 Components (68 directories):
   ├── pkg/coordinator/
   │   └── CLAUDE.md
   ├── pkg/handlers/
   │   └── CLAUDE.md
   └── ... (continues for all components)

📊 Summary:
   • Will create 1 project root with .cursor/rules/ structure
   • Will create CLAUDE.md in 68 component directories
   • Each component CLAUDE.md references project root rules
```

## Progress Display

During execution, the script shows:
- Animated spinner progress indicators
- Live timer for each component
- Clean completion status

```
📦 Processing: pkg/coordinator              ⠋ 02:15
📦 Completed: pkg/coordinator               ✅ 02:34
```

## Component Discovery

The script automatically finds components by:

1. **Scanning for code files**: Looks for common programming language extensions:
   - Go: `*.go`
   - TypeScript/JavaScript: `*.ts`, `*.js`
   - Python: `*.py`
   - Rust: `*.rs`
   - Java: `*.java`
   - C/C++: `*.c`, `*.cpp`, `*.h`

2. **Filtering directories**: Skips build artifacts and dependencies:
   - Hidden directories (`.git`, `.cache`, etc.)
   - Package managers (`node_modules`, `vendor`)
   - Build outputs (`build`, `dist`, `target`)

3. **Requiring files**: Only processes directories that contain actual files (not just subdirectories)

## Architecture

### Hierarchical Documentation

- **Project root**: Contains centralized rules that apply to the entire project
- **Components**: Reference project rules and add component-specific guidance
- **Composable**: Rules are designed to work together without duplication

### Cursor Rules Integration

The generated `.cursor/rules/*.mdc` files integrate with Cursor IDE to provide:
- Persistent context across AI completions
- Domain-specific knowledge encoding
- Automated workflow guidance
- Consistent coding standards

### Command Integration

Uses two specialized Claude Code commands:
- `ethpandaops/init-project-ai-docs`: Handles project-level documentation
- `ethpandaops/init-component-ai-docs`: Handles component-level documentation

## Examples

### Monorepo Initialization

For a large monorepo with multiple services:

```bash
cd my-monorepo
init-ai-docs --dry-run    # Preview the plan
init-ai-docs              # Confirm and execute
```

### Single Service

For a focused service or library:

```bash
init-ai-docs /path/to/service
```

### CI/CD Integration

In automated environments:

```bash
# Skip interactive confirmation in CI
echo "y" | init-ai-docs
```

## Troubleshooting

### Command Not Found

If `init-ai-docs` command is not found:

```bash
# Re-run setup
./setup.sh

# Or restart your terminal to reload PATH
```

### Permission Issues

If you encounter permission errors:

```bash
# Make sure the script is executable
chmod +x scripts/init-ai-docs

# Check PATH includes the scripts directory
echo $PATH | grep -q "ai-cookbook/scripts"
```
