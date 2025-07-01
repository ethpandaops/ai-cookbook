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

2. Run the setup script to install Claude Code commands & scripts:
   ```bash
   ./setup.sh
   ```
   This will:
   - Copy all commands from `./claude-code/commands/*` to `~/.claude/commands/ethpandaops/`
   - Add the `scripts/` directory to your PATH

3. (Optional) Install team coding standards for automatic code style enforcement:
   ```bash
   ./install-code-standards.sh
   ```
   Claude will automatically apply ethPandaOps coding standards when working with supported languages.

4. (Optional) Install Claude Code hooks:
   ```bash
   install-hooks.py
   ```
   Hooks are behind-the-scenes scripts that run before/after Claude Code operations. We have hooks like `gofmt` which automatically formats Go files after Claude Code touches them.

5. To update everything, simply run:
   ```bash
   git pull
   ```

## 📁 Structure

```
├── claude-code/
│   ├── commands/              # Claude Code commands for the team
│   ├── code-standards/        # Team coding standards for Claude
│   └── hooks/                 # Claude Code hooks
├── docs/                      # Team documentation
├── scripts/                   # Shared scripts
├── setup.sh                   # Installation script for commands
├── install-code-standards.sh  # Installation script for coding standards
└── README.md                  # This file
```

## 🎮 Usage

After running `setup.sh`, the commands will be available in Claude Code. You can use them by referencing the command name in your Claude Code sessions.

### 📋 EthPandaOps Coding Standards

Install team coding standards that Claude will automatically apply:

```bash
./install-code-standards.sh
```

This adds instructions to `~/.claude/CLAUDE.md` telling Claude to load the latest coding standards from the local ai-cookbook repository when working with supported languages.

**Commands:**

- `./install-code-standards.sh` - Install/update standards (default)
- `./install-code-standards.sh --status` - Check current status
- `./install-code-standards.sh --uninstall` - Remove standards

### 🪝 Claude Code Hooks

Use the `install-hooks.py` script to manage hooks that automatically run after Claude Code operations:

```bash
# Interactive mode (default when no arguments)
install-hooks.py
```

**Available Hooks:**

- `gofmt` - Automatically formats Go files after editing
- Additional hooks available in `claude-code/hooks/`

Hooks are configured in `~/.claude/settings.json` (global) or `.claude/settings.json` (local).

See [full documentation](docs/install-hooks.md) for detailed usage and options.

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

The following commands are available after running `setup.sh`:

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

### `review-implementation-plan`

Facilitates systematic review of implementation plans with step-by-step analysis and feedback collection. Use this to review and refine implementation plans before execution, ensuring all proposed changes align with project requirements. Usally run after `create-implementation-plan-v2` has generated the plan.

### `eip`

Analyzes Ethereum Improvement Proposals by fetching content and optionally deep-diving into implementations. Use this when you need to understand an EIP's specifications and see how various clients have implemented it.

### `create-feedback-loop`

Creates a temporary feedback loop script that iterates with Claude until a success condition is met. Use this when you need Claude to repeatedly attempt a task (like fixing tests or meeting performance targets) until it succeeds.

### `create-presentation`

Creates succinct and effective presentations in Marp format with automatic HTML generation. Use this when you need to generate professional presentations from complex topics with clear, space-efficient slides.

### `prepare-one-shot`

Enables one-shot implementation mode for automated end-to-end feature development with issue creation, parallel implementation, and PR creation. Use this when you want Claude to autonomously implement a complete feature from planning through CI monitoring without manual intervention.

### Adding New Commands

To add new commands:

1. Create or modify files in the `claude-code/commands/` directory
2. Commit and push your changes
3. Team members can update by running `git pull`

## 🤝 Contributing

1. Create a branch for your changes
2. Add your commands, documentation, or scripts
3. Create a pull request for review
4. After approval, merge to main

## 🆘 Support

For questions or issues, please create an issue in this repository or reach out to the ethPandaOps team.
