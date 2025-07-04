# 🐼 ethPandaOps AI Cookbook 🍳

A centralized repository for AI documentation, commands, and tools used by the ethPandaOps team.

![image](./images/wok.png)

## 📋 Overview

This repository serves as a shared resource for the ethPandaOps team to store and maintain:
- Claude Code commands and workflows
- Shared scripts and utilities
- Team conventions and best practices

## 🚀 Quick Start

1. Clone this repository:
   ```bash
   git clone https://github.com/ethpandaops/ai-cookbook.git
   cd ai-cookbook
   ```

2. Run the installer to set up all tools:
   ```bash
   ./setup.sh
   ```

3. Install recommended tools (fastest option):
   ```bash
   ai-cookbook recommended
   ```
   This installs the team's recommended configuration automatically.

4. Or launch the interactive installer for custom selection:
   ```bash
   ai-cookbook
   ```
   Use arrow keys to navigate, Enter to select components, and 'q' to quit.

5. To update everything, simply run:
   ```bash
   git pull
   ai-cookbook recommended
   ```

## ✨ Features

### Claude Commands
Commands for Claude Code that automate complex development workflows.

### Code Standards
Automatic code style enforcement that Claude applies when working with certain languages.

### Hooks
Behind-the-scenes automation that runs before/after Claude Code operations.

### Scripts
Shared utilities available in your PATH.

### Recommended Configuration
The team maintains a curated set of recommended tools in `recommended-tools.yaml`. This ensures everyone has a consistent, optimal setup for AI-assisted development.

## 🛠️ Installation

### Recommended Installation (Fastest)
```bash
# Clone and install
git clone https://github.com/ethpandaops/ai-cookbook.git
cd ai-cookbook
./setup.sh

# Install team's recommended configuration
ai-cookbook recommended
```

### Custom Installation
```bash
# Clone and install
git clone https://github.com/ethpandaops/ai-cookbook.git
cd ai-cookbook
./setup.sh

# Launch interactive installer for custom selection
ai-cookbook
```

### Interactive Interface
The installer provides an intuitive interface with:
- **Component Selection**: Choose Commands, Code Standards, Hooks, or Scripts
- **Individual Management**: Install/uninstall specific items within each component
- **Visual Status**: See what's installed with color-coded indicators
- **Detailed Information**: Press 'd' for details about selected items
- **Batch Operations**: Install/uninstall all items in a category

### Navigation
- **Arrow Keys**: Navigate through components and items
- **Enter**: Install/uninstall selected item or open component submenu
- **d**: Toggle details view
- **a**: Install all items in current category
- **r**: Remove all items in current category
- **m**: Change mode (for hooks: global vs local)
- **q**: Go back or quit

## 📁 Repository Structure

```
├── claude-code/
│   ├── commands/              # Claude Code commands for the team
│   ├── code-standards/        # Team coding standards for Claude
│   └── hooks/                 # Claude Code hooks
├── docs/                      # Team documentation
├── scripts/                   # Shared scripts and utilities
├── src/                       # Installer source code
│   └── ai_cookbook/          # Main installer package
│       ├── installers/       # Component-specific installers
│       ├── config/          # Configuration and settings
│       └── utils/           # Shared utilities
├── setup.sh                  # Quick installer script
└── README.md                 # This file
```

## 🎮 Usage

### Getting Started
After installation, Claude Code commands are immediately available. Start any Claude Code session and reference commands by name.

### ⚡ Recommended Tools Command
The fastest way to get up and running with the team's standard configuration:

```bash
# Install all recommended tools automatically
ai-cookbook recommended

# Skip confirmation prompts for automation
ai-cookbook recommended --yes

# Install individual tools with the interactive installer
ai-cookbook
```

This command:
- ✅ Installs all team-recommended tools (commands, code standards, hooks, scripts)
- 🔒 Only removes Claude tools it knows are ethPandaOps-managed for safety

The recommended configuration is defined in `recommended-tools.yaml` and maintained by the team.

### 📚 Initialize AI Documentation in Any Repository

**WARNING**: With the release of Claude 4 you probably don't need this script. Claude is smart enough to understand the project structure and conventions without it.

Use the `init-ai-docs.py` script to set up comprehensive AI documentation in any project:

```bash
# Initialize docs in current directory
init-ai-docs.py

# Initialize docs in specific project
init-ai-docs.py /path/to/project

# Preview what will be created
init-ai-docs.py --dry-run
```

This creates:
- Project-level CLAUDE.md and .cursor/rules/
- Component-level CLAUDE.md files
- Compatible with Cursor, Claude Code, and other AI tools

See [full documentation](docs/init-ai-docs.md) for detailed usage and options.

## 🛠️ Claude Code Commands

The following commands are available after installation:

### `init-project-ai-docs`

Initializes top-level AI documentation for the entire project with foundational structure and project-wide rules. Use this when setting up AI documentation for a new project to establish consistent coding standards and development workflows.

### `prime-context`

Reads and loads project context files (README.md, CLAUDE.md, docs) into Claude's working memory. Use this at the start of a Claude session to ensure Claude understands your project structure and conventions.

### `init-component-ai-docs`

Initializes AI documentation for a specific component/directory within a project with component-specific rules. Use this when adding AI documentation to individual components or modules within an existing project structure.

### `parallel-repository-tasks`

Executes the same action across multiple repositories in parallel for batch operations. Use this when you need to analyze patterns, implement changes, or audit multiple repositories simultaneously.

### `create-implementation-plan`

Creates a detailed implementation plan with scaffolding for features or system enhancements (deprecated - use v2). Use this when you need a structured approach to implementing complex features with clear milestones.

### `create-implementation-plan-v2`

Generates comprehensive implementation plans optimized for maximum parallelization during execution. Use this for planning complex features where you want Claude to identify and execute independent tasks concurrently.

### `create-implementation-plan-v3`

Enhanced implementation planning with improved analysis, dependency management, and execution tracking. Use this for the most sophisticated planning needs with automated progress monitoring.

### `review-implementation-plan`

Facilitates systematic review of implementation plans with step-by-step analysis and feedback collection. Use this to review and refine implementation plans before execution, ensuring all proposed changes align with project requirements. Usually run after `create-implementation-plan-v2` has generated the plan.

### `eip`

Analyzes Ethereum Improvement Proposals by fetching content and optionally deep-diving into implementations. Use this when you need to understand an EIP's specifications and see how various clients have implemented it.

### `create-feedback-loop`

Creates a temporary feedback loop script that iterates with Claude until a success condition is met. Use this when you need Claude to repeatedly attempt a task (like fixing tests or meeting performance targets) until it succeeds.

### `create-presentation`

Creates succinct and effective presentations in Marp format with automatic HTML generation. Use this when you need to generate professional presentations from complex topics with clear, space-efficient slides.

### `prepare-one-shot`

Enables one-shot implementation mode for automated end-to-end feature development with issue creation, parallel implementation, and PR creation. Use this when you want Claude to autonomously implement a complete feature from planning through CI monitoring without manual intervention.

## 🏗️ Component Details

### Commands
Individual Claude Code command templates that can be installed/uninstalled separately:
- Each command is a standalone `.md` file with specific instructions
- Install individual commands or all commands at once
- Commands are immediately available in Claude Code after installation

### Code Standards  
Language-specific coding standards that can be managed individually:
- **Go**: `go/CLAUDE.md` - Go formatting, naming conventions, error handling
- **Python**: `python/CLAUDE.md` - PEP compliance, type hints, documentation
- **Rust**: `rust/CLAUDE.md` - Memory safety, error handling, cargo conventions  
- **TailwindCSS**: `tailwindcss/CLAUDE.md` - Utility-first CSS patterns
- Install/uninstall standards per language
- Automatically referenced by Claude when editing files

### Hooks
Individual automation hooks for different languages and tools:
- **eslint**: JavaScript/TypeScript formatting with ESLint
- **gofmt**: Go code formatting after edits
- **golangci-lint**: Go linting and static analysis
- **typescript**: TypeScript type checking after edits
- Choose global (all projects) or local (current project) installation
- Install/uninstall hooks individually based on your needs

### Scripts
Utility scripts added to your system PATH:
- **init-ai-docs.py**: Initialize AI documentation in projects
- **install-hooks.py**: Legacy hooks installer (still functional)
- Scripts become globally accessible commands after installation

## 📋 Requirements

### System Requirements

- **Operating System**: macOS, Linux, or Windows (with WSL)
- **Python**: 3.8 or higher
- **Shell**: bash, zsh, or fish
- **Git**: For cloning and updating the repository

### Claude Code Requirements

- **Claude Code**: Latest version recommended
- **Claude Account**: Active subscription for AI features
- **Internet Connection**: Required for Claude API access

### Optional Dependencies

- **Go**: Required for `gofmt` and `golangci-lint` hook functionality
- **Node.js/npm**: Required for `eslint` and `typescript` hooks
- **Make**: Required for some project automation

## 🤝 Contributing

1. Create a branch for your changes
2. Add your commands, documentation, or scripts
3. Test your changes with the installer
4. Update documentation as needed
5. Create a pull request for review
6. After approval your changes will be merged to main
