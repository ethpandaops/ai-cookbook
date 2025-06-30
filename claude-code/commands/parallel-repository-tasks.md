# Parallel Repository Tasks

## Overview
This command prompts for a list of repositories and an action to perform, then executes the specified action against each repository in parallel subtasks. It's designed for batch operations across multiple repositories where the same action needs to be applied consistently.

## Important Notes
- Each repository task runs as an independent parallel subtask
- All repositories must be accessible from the current environment
- Actions should be self-contained and not depend on other repositories' results
- Use absolute paths or ensure proper working directory context for each task
- Claude MUST use parallel task execution when running multiple repository operations

## Security Restriction - CRITICAL
**Claude Code has a security restriction that prevents changing directories outside the original working directory.** This means:
- ❌ DO NOT use `cd` commands to navigate into repositories
- ✅ DO use absolute paths to access files: `$original_cwd/repo_name/file.txt`
- ✅ DO use git's `-C` flag for git commands: `git -C repo_name status`
- ✅ DO use tool flags that accept paths: `find repo_name -name "*.go"`

This restriction ensures that parallel subtasks maintain proper security boundaries while still being able to analyze repository contents.

## Tasks

### TASK 1: Prompt for Repository List
Prompt the user to provide a list of repositories to process:

```
Please provide the list of repositories to process. You can specify them as:
- Repository URLs (https://github.com/org/repo)
- Local paths (/path/to/local/repo)
- Repository names (org/repo for GitHub)

For remote repositories, you can optionally specify a branch:
- Repository with branch: org/repo@branch-name
- Repository URL with branch: https://github.com/org/repo@branch-name

Examples (Consensus Layer repositories):
- https://github.com/prysmaticlabs/prysm
- https://github.com/sigp/lighthouse
- https://github.com/Consensys/teku
- https://github.com/ChainSafe/lodestar
- https://github.com/grandinetech/grandine
- https://github.com/status-im/nimbus-eth2

Examples (Execution Layer repositories):
- https://github.com/ethereum/go-ethereum
- https://github.com/NethermindEth/nethermind
- https://github.com/paradigmxyz/reth
- https://github.com/erigontech/erigon
- https://github.com/hyperledger/besu

Enter repositories (one per line, empty line to finish):
```

Store the repository list for processing.

### TASK 2: Prompt for Action
Prompt the user to specify the action to perform on each repository:

```
Please specify the action to perform on each repository.

Examples:
- "analyze how the http client is implemented and output analysis to README-analysis.md"
- "implement rate limiting with exponential backoff"
- "audit for security vulnerabilities and create vulnerability-report.md"
- "update all dependencies to latest versions and test compatibility"
- "generate API documentation from code comments"

Action to perform:
```

Store the action description for execution.

### TASK 3: Validate Inputs
Validate the provided inputs:
- Ensure at least one repository is specified
- Verify repository format (for URLs/names) and accessibility (for local paths)
- Confirm the action description is clear and actionable
- Ask for clarification if needed

### TASK 4: Download/Clone Repositories (Parallel)
Create parallel subtasks to ensure all repositories are available locally:

**IMPORTANT**: All operations should maintain the original working directory context. Store the original CWD at the start and ensure all file paths are relative to it.

#### Parallel Repository Download Logic
For each repository in the list, create an independent parallel subtask:

#### Repository Download Subtask Structure
Each repository gets its own download subtask with:

1. **Store Original Working Directory**:
   - Capture the current working directory: `original_cwd=$(pwd)`
   - All file outputs should be relative to this directory
   - **IMPORTANT**: Do NOT use `cd` to change directories - use absolute paths instead

2. **Determine Repository Type**:
   - **URL format** (https://github.com/org/repo): Extract repo name from URL
   - **URL with branch** (https://github.com/org/repo@branch): Extract repo name and branch
   - **GitHub format** (org/repo): Convert to full GitHub URL
   - **GitHub with branch** (org/repo@branch): Convert to full GitHub URL and extract branch
   - **Local path** (/path/to/repo): Verify path exists and is accessible

3. **Generate Local Directory Name**:
   - For URLs/GitHub repos: Use the repository name (e.g., "go-ethereum" from "ethereum/go-ethereum")
   - For local paths: Use the repository as-is (already local)
   - Create full path: `repo_path="$original_cwd/$repo_name"`

4. **Check if Directory Exists**:
   - If directory already exists in current working directory, skip cloning
   - Print message: "Repository {repo_name} already exists locally, skipping download"

5. **Clone Repository** (if not exists):
   - Use shallow clone for performance: `git clone --depth 1 {repo_url} {local_directory_name}`
   - If a branch was specified, use: `git clone --depth 1 --branch {branch_name} {repo_url} {local_directory_name}`
   - For actions requiring full history, use git commands with `-C` flag: `git -C {local_directory_name} fetch --unshallow`
   - Handle clone failures and branch checkout failures gracefully with clear error messages
   - Verify successful clone and branch checkout using: `git -C {local_directory_name} branch --show-current`

#### Parallel Execution Guidelines for Downloads
- Use Claude's parallel task execution capabilities for repository downloads
- Each download subtask should be completely independent
- Provide clear task descriptions that include:
  - Repository identifier and type
  - Expected local directory name
  - Clone/verification requirements
  - Error handling approach

#### Example Parallel Download Subtask Creation
```markdown
**Repository Download Task**: {repository_identifier}
**Type**: {URL/GitHub format/Local path}
**Local Directory**: {expected_directory_name}
**Requirements**: 
- Check if directory exists before cloning
- Clone repository if needed
- Verify successful download
- Handle errors gracefully
- Report completion status
```

#### Example Download Process (Per Subtask)
```bash
# Store original working directory
original_cwd=$(pwd)

# For repository "ethereum/go-ethereum" (in parallel subtask)
if [ ! -d "go-ethereum" ]; then
    git clone --depth 1 https://github.com/ethereum/go-ethereum.git go-ethereum
    echo "✓ Cloned go-ethereum (shallow)"
else
    echo "→ go-ethereum already exists, skipping download"
fi

# For repository "ethereum/go-ethereum@develop" (with branch)
if [ ! -d "go-ethereum" ]; then
    git clone --depth 1 --branch develop https://github.com/ethereum/go-ethereum.git go-ethereum
    echo "✓ Cloned go-ethereum and checked out develop branch (shallow)"
else
    echo "→ go-ethereum already exists, skipping download"
    # Verify current branch if needed (using -C flag to avoid cd)
    git -C go-ethereum branch --show-current
fi

# If full history is needed for the action, unshallow after clone:
# git -C go-ethereum fetch --unshallow
```

#### Error Handling for Downloads
- Network connectivity issues
- Invalid repository URLs or names
- Permission/authentication problems
- Disk space limitations
- Repository not found (404 errors)

### TASK 5: Execute Parallel Repository Action Tasks
After all repositories are downloaded, create and execute parallel subtasks for the specified action:

#### Subtask Structure
Each repository gets its own independent subtask with:
1. **Working Directory Context**: 
   - Store the original working directory: `original_cwd=$(pwd)`
   - All output files should be written to the ORIGINAL working directory, not the repository subdirectory
   - **CRITICAL**: Avoid using `cd` commands - use absolute paths or tool-specific flags instead
2. **Repository Access**: Use absolute paths to access repository files
   - Use: `$original_cwd/{repo_name}/path/to/file` for file access
   - Use: `git -C {repo_name}` for git commands
   - Use: `find {repo_name} -name pattern` for searching
3. **Context Analysis**: Understand the repository structure and relevant files using absolute paths
4. **Action Execution**: Perform the specified action using absolute paths to repository files
5. **Output Generation**: 
   - Create any requested output files or reports
   - **IMPORTANT**: Write markdown files to the ORIGINAL working directory
   - Example: Write to `$original_cwd/architecture-overview.md`
6. **Cleanup**: Handle any temporary files or state

#### Parallel Execution Guidelines
- Use Claude's parallel task execution capabilities
- Each subtask should be completely independent
- Provide clear task descriptions that include:
  - Repository identifier
  - Full action description
  - Expected output format
  - Any specific requirements

#### Example Subtask Creation
```markdown
**Repository**: {repository_name}
**Action**: {full_action_description}
**Working Directory**: Store original CWD and ensure all outputs go there
**Requirements**: 
- Store original working directory: original_cwd=$(pwd)
- DO NOT use cd commands - use absolute paths instead:
  - Access files: $original_cwd/{repository_name}/path/to/file
  - Git commands: git -C {repository_name} [command]
  - Find/grep: find {repository_name} -name "pattern"
- Work within repository context using absolute paths
- Generate output files in ORIGINAL working directory:
  - Use: $original_cwd/{output_filename}
- Handle errors gracefully
- Provide summary of work completed
```

#### Example Action Execution (Per Subtask)
```bash
# Store original working directory
original_cwd=$(pwd)

# Set repository path
repo_name="go-ethereum"
repo_path="$original_cwd/$repo_name"

# Perform analysis using absolute paths (NO cd commands)
# List files in repository
find "$repo_path" -name "*.go" -type f | head -20

# Run git commands using -C flag
git -C "$repo_path" log --oneline -n 5

# Read files using absolute paths
cat "$repo_path/README.md"

# Write output to ORIGINAL working directory
cat > "$original_cwd/go-ethereum-architecture.md" << 'EOF'
# Go-Ethereum Architecture Overview
...
EOF
```

### TASK 6: Consolidate Results
After all parallel subtasks complete:
1. Collect results from each repository task
2. Provide a summary of completed work
3. Report any failures or issues encountered
4. Generate a consolidated report if applicable

### TASK 7: Report Completion
Provide a final summary including:
- Total repositories processed
- Successful completions
- Any failures with error details
- Location of generated files/reports
- Next steps or recommendations

## Error Handling
- Handle repository access failures gracefully
- Continue processing other repositories if one fails
- Provide clear error messages with suggested fixes
- Offer to retry failed repositories

## Example Usage Flow

1. **User Input**:
   ```
   Repositories:
   - https://github.com/ethereum/go-ethereum
   - /local/path/to/beacon-chain
   - ethpandaops/xatu@develop
   
   Action: analyze consensus client architecture and create architecture-overview.md
   ```

2. **Repository Download**:
   ```
   → go-ethereum already exists, skipping download
   ✓ Cloned beacon-chain
   ✓ Cloned xatu and checked out develop branch
   ```

3. **Parallel Execution**:
   - Task 1: Process go-ethereum repository (output to ./go-ethereum-architecture.md)
   - Task 2: Process beacon-chain repository (output to ./beacon-chain-architecture.md)
   - Task 3: Process xatu repository (output to ./xatu-architecture.md)

4. **Results**:
   ```
   Completed parallel repository analysis:
   ✓ go-ethereum: ./go-ethereum-architecture.md created
   ✓ beacon-chain: ./beacon-chain-architecture.md created  
   ✓ xatu: ./xatu-architecture.md created
   
   All 3 repositories processed successfully.
   All markdown files created in current working directory.
   ```

## Best Practices
- Keep actions focused and well-defined
- Use consistent output formats across repositories
- Provide clear progress updates during execution
- Handle edge cases (empty repositories, access issues, etc.)
- Ensure parallel tasks don't interfere with each other
- Use appropriate timeouts for long-running operations