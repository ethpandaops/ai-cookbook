# Network Analysis Command

## Command Specification

The `analyze-network` command provides comprehensive analysis of Ethereum network nodes across different testnets and analysis scopes.

### Usage

```
analyze-network <devnet> <scope> <target> [time_period]
```

### Parameters

- **devnet**: The target testnet/devnet name (e.g., `fusaka-devnet-3`, `holesky`, `sepolia`)
- **scope**: Analysis scope, one of:
  - `instance` - Analyze a specific node instance
  - `cl` - Analyze all instances of a consensus client type
  - `el` - Analyze all instances of an execution client type
  - `all` - Analyze all nodes on the network
- **target**: The specific target based on scope:
  - For `instance`: specific instance identifier
  - For `cl`: consensus client name (grandine, lighthouse, lodestar, nimbus, prysm, teku)
  - For `el`: execution client name (geth, nethermind, besu, erigon, reth, nimbusel)
  - For `all`: use `nodes` as the target
- **time_period**: Time range for analysis (optional, default: 1h)
  - Examples: `30m`, `1h`, `2h`, `4h`, `6h`, `12h`, `1d`

## Analysis Scope Examples

### 1. Single Instance Analysis
```bash
analyze-network fusaka-devnet-3 instance lighthouse-001 1h
```
Analyzes logs for a specific lighthouse instance `lighthouse-001` on fusaka-devnet-3 for the last hour.

### 2. Consensus Client Type Analysis  
```bash
analyze-network holesky cl teku 4h
```
Analyzes logs for all Teku consensus client instances on Holesky testnet for the last 4 hours.

### 3. Execution Client Type Analysis
```bash
analyze-network sepolia el geth 30m
```
Analyzes logs for all Geth execution client instances on Sepolia testnet for the last 30 minutes.

### 4. Full Network Analysis
```bash
analyze-network fusaka-devnet-3 all nodes 2h
```
Analyzes logs for all nodes (both CL and EL) on fusaka-devnet-3 network for the last 2 hours. This launches 12 parallel ethereum-client-analyzer agents (one per client type) and aggregates the results.

## Implementation Details

The command uses the `ethereum-client-analyzer` agent to perform the analysis with the ethpandaops-production-data MCP server. The agent constructs appropriate Loki queries based on the specified scope and parameters.

### Execution Strategy

**Single Target Analysis:**
- For `instance`, `cl`, or `el` scopes with a specific target, a single `ethereum-client-analyzer` agent is launched

**Multiple Target Analysis:**
- For `all` scope, multiple `ethereum-client-analyzer` agents are launched in parallel:
  - One agent per CL client type (grandine, lighthouse, lodestar, nimbus, prysm, teku)
  - One agent per EL client type (geth, nethermind, besu, erigon, reth, nimbusel)
  - Results are aggregated and presented in a unified report

### Parallel Execution

When analyzing multiple targets, the command uses Claude Code's Task tool to launch concurrent sub-agents:

```bash
# For analyze-network fusaka-devnet-3 all nodes 1h
# Launches 12 parallel agents (6 CL + 6 EL types):

Task ethereum-client-analyzer "Analyze lighthouse on fusaka-devnet-3" &
Task ethereum-client-analyzer "Analyze teku on fusaka-devnet-3" &
Task ethereum-client-analyzer "Analyze geth on fusaka-devnet-3" &
Task ethereum-client-analyzer "Analyze nethermind on fusaka-devnet-3" &
# ... (continue for all client types)

# Wait for all analyses to complete, then aggregate results
```

### Query Construction

Based on the scope, different Loki query patterns are used:

- **Instance scope**: `{testnet="<devnet>", instance="<target>"}`
- **CL scope**: `{testnet="<devnet>", ethereum_cl="<target>"}`
- **EL scope**: `{testnet="<devnet>", ethereum_el="<target>"}`
- **All scope**: Parallel queries for each client type on `{testnet="<devnet>"}`

### Result Aggregation

For parallel multi-client analysis, results are aggregated as follows:

1. **Executive Summary**: Combined health status (worst case scenario)
2. **Node Instances**: Merged tables from all sub-analyses
3. **Critical Issues**: Consolidated and deduplicated issues across all clients
4. **Network Connectivity**: Combined connectivity metrics
5. **Recommendations**: Prioritized actions across all analyzed components

## Output Format

All analyses follow the same structured format with data presented in tables for easy parsing:

### Executive Summary
- Overall health status: HEALTHY/WARNING/CRITICAL
- Current slot and sync status
- Key issues summary (if any)

### Node Instances Status
Instance overview table:
```
| Instance ID | Client Type | Layer | Status | Current Block/Slot | Peer Count | Sync State | Health |
|------------|-------------|-------|--------|---------------------|------------|------------|---------|
| lighthouse-001 | lighthouse | CL | Running | 12345678 | 87 | Synced | HEALTHY |
| geth-001 | geth | EL | Running | 18975432 | 45 | Synced | HEALTHY |
| teku-002 | teku | CL | Running | 12345677 | 92 | Syncing | WARNING |
```

Sync progress table (for syncing instances):
```
| Instance ID | Layer | Start Block/Slot | Current Block/Slot | Target Block/Slot | Rate/Min | Est. Completion |
|------------|-------|------------------|--------------------|--------------------|----------|----------------|
| teku-002 | CL | 12340000 | 12345677 | 12345800 | 245 slots | 00:30:15 |
| nethermind-003 | EL | 18970000 | 18975000 | 18975500 | 450 blocks | 00:01:07 |
```

### Critical Issues Identified
Issues summary table:
```
| Issue | Count | First Seen | Last Seen | Urgency | Impact |
|-------|-------|------------|-----------|---------|---------|
| Connection timeout | 12 | 14:32:15 | 15:45:22 | Medium | Performance |
| Fork choice error | 3 | 15:10:33 | 15:12:45 | High | Consensus |
| Memory warning | 45 | 14:00:00 | 15:50:00 | Low | Resource |
```


Network connectivity table:
```
| Instance | Layer | Connected Peers | Inbound | Outbound | Avg Latency (ms) | Status |
|----------|-------|-----------------|---------|----------|------------------|---------|
| lighthouse-001 | CL | 87 | 32 | 55 | 145 | Healthy |
| geth-001 | EL | 45 | 18 | 27 | 98 | Healthy |
| teku-002 | CL | 92 | 28 | 64 | 132 | Healthy |
```

### Recommendations
Priority-based action table:
```
| Priority | Action | Timeline | Expected Impact | Difficulty |
|----------|--------|----------|----------------|------------|
| Critical | Investigate fork choice errors | Immediate | High | Medium |
| High | Optimize peer connections | 1-2 hours | Medium | Low |
| Medium | Monitor memory usage trends | 24 hours | Low | Low |
```

## Integration Examples

### 1. Monitoring Dashboard
```bash
# Collect metrics for all CL types on multiple networks
analyze-network fusaka-devnet-3 cl lighthouse 1h
analyze-network holesky cl teku 1h
analyze-network sepolia cl prysm 1h
```

### 2. Incident Response
```bash
# Quick full network health check (parallel analysis of all client types)
analyze-network fusaka-devnet-3 all nodes 30m

# Deep dive into specific problematic client
analyze-network fusaka-devnet-3 cl grandine 4h

# Parallel analysis of all CL clients for comparison
analyze-network fusaka-devnet-3 all nodes 1h | grep "CL\|Consensus"
```

### 3. Performance Analysis
```bash
# Sequential individual client analysis
analyze-network holesky el geth 2h
analyze-network holesky el nethermind 2h  
analyze-network holesky el besu 2h

# Parallel analysis of all EL clients for comprehensive comparison
analyze-network holesky all nodes 2h | grep "EL\|Execution"
```

## Command Aliases

- `anet` - Short alias for `analyze-network`
- `check-network` - Alternative command name
- `net-health` - Health check focused alias

## Performance Characteristics

### Single Target Analysis
- **Execution Time**: 30-60 seconds depending on log volume
- **Resource Usage**: Single ethereum-client-analyzer agent
- **Memory**: ~100MB per analysis

### Multi-Target Analysis (All Nodes)
- **Execution Time**: 30-90 seconds (parallel execution)
- **Resource Usage**: Up to 12 concurrent ethereum-client-analyzer agents  
- **Memory**: ~1.2GB peak usage during parallel execution
- **Throughput**: 12x faster than sequential analysis

## Validation

The command validates:
- Devnet name exists and has available data
- Scope is one of the valid options
- Target is appropriate for the chosen scope
- Time period is in valid format
- For `all` scope, ensures sufficient system resources for parallel execution

Invalid parameters result in helpful error messages with examples of correct usage.

## Error Handling

### Parallel Execution Failures
- If individual sub-agents fail, continue with remaining analyses
- Report partial results with clear indication of failed components
- Provide fallback to sequential execution if resource constraints detected

### Network Issues  
- Retry failed Loki queries up to 3 times
- Graceful degradation when MCP server is unavailable
- Cache intermediate results to prevent data loss during long analyses