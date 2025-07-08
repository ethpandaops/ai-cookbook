<div align="center">
  <img src="./images/wok.png" alt="ethPandaOps AI Cookbook" width="350">
  <h1>🐼 ethPandaOps AI Cookbook 🍳</h1>
   <h4><i>Get the wok out</i></h4>
</div>
<hr style="height: 1px; background-color: #e1e4e8; border: none;">

This repo is a shared, centralized location for the team to put common workflows and tools that we've found useful in our AI use. While the team is the main contributors/users, external contributions are certainly welcome.

The majority of this repo focuses around [Claude Code](https://claude.ai/code) integrations. You can pick and choose which tools and features you want, but we have an ever-evolving recommended set [here](./recommended-tools.yaml) which can be automatically installed with `ai-cookbook recommended --yes`.

### ✨ Available Tools

- [Claude Code - Commands](./claude-code/commands) - reusable slash commands that we use every day.
- [Claude Code - Code Standards](./claude-code/code-standards) - supports multiple languages with minimal token overhead.
- [Claude Code - Hooks](./claude-code/hooks) - before/after hooks that put Claude Code on rails. e.g. `gofmt` after Claude touches a `.go` file.
- [Scripts](./scripts) - scripts that we find useful, like programatically creating `CLAUDE.md` recursively in a project

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

6. To uninstall all installed components:
   ```bash
   ai-cookbook uninstall
   ```


# Tools
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
