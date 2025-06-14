# EIP (Ethereum Improvement Proposal) Analysis

## Overview
This command helps you analyze Ethereum Improvement Proposals (EIPs) by fetching and summarizing their content from the official EIP repository. It provides a comprehensive analysis of the proposal and offers deep-dive options into related execution or consensus specifications.

## How It Works
1. **User provides EIP number** (e.g., 7691)
2. **Claude fetches the EIP** from https://eips.ethereum.org/EIPS/eip-{number}
3. **Provides comprehensive summary** including:
   - Purpose and motivation
   - Technical specifications
   - Implementation details
   - Potential impacts
   - Current status
4. **Offers deep-dive options** into related specs if applicable

## Instructions for Claude

### STEP 1: Request EIP Number
Ask the user for the EIP number they want to analyze:

```
Which EIP would you like me to analyze? Please provide the EIP number (e.g., 7691).
```

### STEP 2: Fetch and Analyze EIP
Once the user provides the number:
1. Use WebFetch to retrieve the EIP from `https://eips.ethereum.org/EIPS/eip-{number}`
2. Extract and analyze key information

### STEP 3: Provide Comprehensive Summary
Present a structured analysis including:

```markdown
# EIP-{number} Analysis

## Overview
- **Title**: [EIP Title]
- **Status**: [Current Status]
- **Type**: [Standards Track, Meta, or Informational]
- **Category**: [Core, Networking, Interface, or ERC]
- **Authors**: [List of authors]

## Summary
[2-3 paragraph executive summary of what this EIP proposes]

## Technical Details
### Motivation
[Why this EIP is needed]

### Specification
[Key technical specifications and changes]

### Implementation Considerations
- [Key implementation points]
- [Backward compatibility issues]
- [Security considerations]

## Impact Analysis
### Benefits
- [Expected improvements]
- [Problems solved]

### Potential Risks
- [Implementation risks]
- [Compatibility concerns]

### Related EIPs
- [List any related or dependent EIPs]
```

### STEP 4: Offer Deep-Dive Options
After the summary, ask:

```
Would you like me to deep-dive into any of the following? (Select 0 or more options)

1. **Consensus specs** - Analyze consensus layer specifications
2. **Execution specs** - Analyze execution layer specifications  
3. **Consensus Layer client implementations**
   - Prysm, Lighthouse, Teku, Lodestar, Grandine, Nimbus
4. **Execution Layer client implementations**
   - Geth, Nethermind, Reth, Erigon, Besu

Please list the numbers you'd like to explore (e.g., "1,3" or "all" or "none").
```

### STEP 5: Deep-Dive Analysis (if requested)
Execute the analysis in two parallel stages:

#### Stage 1: Clone Repositories (PARALLEL)
Clone all requested repositories simultaneously:

**Consensus Specs:**
```bash
git clone https://github.com/ethereum/consensus-specs.git
```

**Execution Specs:**
```bash
git clone https://github.com/ethereum/execution-specs.git
```

**Consensus Layer Clients:**
- `git clone https://github.com/prysmaticlabs/prysm.git`
- `git clone https://github.com/sigp/lighthouse.git`
- `git clone https://github.com/Consensys/teku.git`
- `git clone https://github.com/ChainSafe/lodestar.git`
- `git clone https://github.com/grandinetech/grandine.git`
- `git clone https://github.com/status-im/nimbus-eth2.git`

**Execution Layer Clients:**
- `git clone https://github.com/ethereum/go-ethereum.git`
- `git clone https://github.com/NethermindEth/nethermind.git`
- `git clone https://github.com/paradigmxyz/reth.git`
- `git clone https://github.com/erigontech/erigon.git`
- `git clone https://github.com/hyperledger/besu.git`

#### Stage 2: Analyze Repositories (PARALLEL SUBTASKS)
**CRITICAL**: Create independent parallel subtasks for EACH repository analysis. Do NOT analyze repositories sequentially.

**Parallel Subtask Structure:**
Each repository gets its own independent analysis subtask:

```markdown
**Analysis Task**: {repository_name}
**EIP**: {eip_number}
**Type**: {Specification/Consensus Client/Execution Client}
**Actions**:
- Search for EIP-{number} references in code
- Analyze implementation status
- Document findings
- Report completion
```

**For Specification Repos (Each as parallel subtask):**
- **consensus-specs subtask**: Search for EIP-{number}, analyze specification changes
- **execution-specs subtask**: Search for EIP-{number}, analyze specification changes

**For Client Implementation Repos (Each as parallel subtask):**
Create 11 parallel subtasks (6 consensus + 5 execution clients):
- Search for EIP-{number} in code, commits, PRs, and issues
- Identify implementation status (not started/in progress/complete)
- Document specific code changes and file locations
- Note any implementation differences or unique approaches

**Example Parallel Execution:**
```
Launching 13 parallel analysis subtasks:
- Task 1: Analyze consensus-specs for EIP-{number}
- Task 2: Analyze execution-specs for EIP-{number}
- Task 3: Analyze prysm for EIP-{number}
- Task 4: Analyze lighthouse for EIP-{number}
- Task 5: Analyze teku for EIP-{number}
... (continue for all repositories)
```

**IMPORTANT**: Use Claude's Task tool with parallel execution. Each repository analysis MUST run as an independent subtask to maximize performance.

### Analysis Output Structure
Present findings organized by category:

```markdown
## Deep-Dive Analysis: EIP-{number}

### Consensus Specifications
[Findings from consensus-specs repo]

### Execution Specifications  
[Findings from execution-specs repo]

### Consensus Layer Implementations
#### Prysm
- Implementation status: [Status]
- Key changes: [List of changes]
- Related PRs: [PR links if found]

[Repeat for each analyzed consensus client]

### Execution Layer Implementations
#### Geth
- Implementation status: [Status]
- Key changes: [List of changes]
- Related PRs: [PR links if found]

[Repeat for each analyzed execution client]

### Implementation Summary
- Clients with full support: [List]
- Clients with partial support: [List]
- Clients without support: [List]
- Key implementation differences: [Notable variations]
```

## Example Usage

```
User: I want to analyze an EIP
Claude: Which EIP would you like me to analyze? Please provide the EIP number (e.g., 7691).
User: 4844
Claude: [Fetches and analyzes EIP-4844 about Proto-Danksharding]
[Provides comprehensive summary]
Would you like me to deep-dive into the related specifications?
User: 1
Claude: [Analyzes execution specs for EIP-4844 implementation details]
```

## Notes for Claude
- Always verify the EIP exists before attempting analysis
- If the EIP page returns 404, inform the user and suggest checking the number
- Focus on practical implications for developers and users
- Highlight any contentious or discussion points mentioned in the EIP
- When doing deep-dives, look for actual implementation code, not just documentation
- Be prepared to explain complex technical concepts in accessible terms

---

**IMPORTANT**: This is the command structure. Do not start analyzing an EIP yet. Wait for the user to initiate the command and provide an EIP number.