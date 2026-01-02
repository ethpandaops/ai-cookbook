# Network Analysis Command

Analyze Ethereum network nodes using the `ethereum-client-analyzer` subagent.

**Rules**: Do not hallucinate. Do not provide mitigation ideas. Present data in tables.

## Usage

```
analyze-network <devnet> <scope> <target> [period] [mode]
```

## Parameters

| Parameter | Description | Default | Examples |
|-----------|-------------|---------|----------|
| `devnet` | Target network | - | fusaka-devnet-3, holesky, sepolia |
| `scope` | Analysis scope | - | instance, cl, el, all |
| `target` | Target based on scope | - | See below |
| `period` | Time range | 30m | 15m, 30m, 1h |
| `mode` | Analysis depth | full | quick, full |

**Target by scope**:
- `instance`: specific instance ID (e.g., lighthouse-besu-1)
- `cl`: consensus client (grandine, lighthouse, lodestar, nimbus, prysm, teku)
- `el`: execution client (geth, nethermind, besu, erigon, reth, nimbusel)
- `all`: use "nodes"

**Period limits**: Default 30m, max recommended 1h. For longer periods, subagents use 30m pagination windows automatically.

**Modes**:
| Mode | Use Case | Speed | Detail |
|------|----------|-------|--------|
| `quick` | "Is there a problem?" | Fast | Error counts only |
| `full` | "Give me details" | Slower | Complete analysis |

## Execution Strategy

### Phase 1: Pre-Discovery (REQUIRED before spawning subagents)

Before launching any subagents, discover which clients actually exist on the devnet to avoid wasting tokens on empty queries.

**For `scope=all`**: Run these Loki queries first:
```
# Discover CL clients present
action: label_values
label: ethereum_cl
query: {testnet="{devnet}"}
start: now-30m
end: now

# Discover EL clients present
action: label_values
label: ethereum_el
query: {testnet="{devnet}"}
start: now-30m
end: now

# Discover all instances (to pass to subagents)
action: label_values
label: instance
query: {testnet="{devnet}"}
start: now-30m
end: now
```

**For `scope=cl`**: Verify the target CL client exists and get instances:
```
action: label_values
label: instance
query: {testnet="{devnet}", ethereum_cl="{target}"}
start: now-30m
end: now
```

**For `scope=el`**: Verify the target EL client exists and get instances:
```
action: label_values
label: instance
query: {testnet="{devnet}", ethereum_el="{target}"}
start: now-30m
end: now
```

**For `scope=instance`**: Auto-detect client type:
```
# Query one log line to extract labels
action: query
query: {testnet="{devnet}", instance="{target}"}
start: now-5m
end: now
limit: 1
compact: true
```

From the result, extract `ethereum_cl` or `ethereum_el` label to determine:
- If `ethereum_cl` present → `layer=cl`, `client={ethereum_cl value}`
- If `ethereum_el` present → `layer=el`, `client={ethereum_el value}`

**Decision logic**:
- If no clients/instances found → Report "No {target} found on {devnet}" and stop
- If clients found → Proceed to Phase 2 with discovered data

### Phase 2: Launch Subagents

Only spawn subagents for clients confirmed to exist in Phase 1.

**Pass discovered instances to subagents** to skip their Phase 1 discovery.

**For `scope=all`**:
1. Group discovered instances by client type
2. Launch CL subagents in parallel (only for discovered CL clients)
3. Launch EL subagents in parallel (only for discovered EL clients)

**For `scope=cl` or `scope=el`**: Single subagent for the specified client.

**For `scope=instance`**: Single subagent with auto-detected client info.

### Subagent Prompt Format

Use this exact format when invoking `ethereum-client-analyzer`:

```
devnet={devnet} client={client} layer={cl|el} period={period} mode={mode} [instances={inst1,inst2}] [instance={instance}]
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `devnet` | Yes | Target testnet name |
| `client` | Yes | Client name (lowercase) |
| `layer` | Yes | "cl" or "el" |
| `period` | Yes | Time range (e.g., "30m") |
| `mode` | Yes | "quick" or "full" |
| `instances` | No | Comma-separated instance list (skips subagent Phase 1) |
| `instance` | No | Single instance ID (for instance scope) |

### Parallel Execution Example (scope=all, mode=full)

**Step 1**: Pre-discovery queries return:
- CL clients: `[lighthouse, teku, nimbus]`
- EL clients: `[geth, nethermind]`
- Instances: `[lighthouse-geth-1, lighthouse-geth-2, teku-nethermind-1, nimbus-geth-1, ...]`

**Step 2**: Group instances by client:
- lighthouse: `lighthouse-geth-1,lighthouse-geth-2`
- teku: `teku-nethermind-1`
- nimbus: `nimbus-geth-1`
- geth: `lighthouse-geth-1,lighthouse-geth-2,nimbus-geth-1`
- nethermind: `teku-nethermind-1`

**Step 3**: Launch subagents with pre-discovered instances:
```
# CL subagents (parallel)
Task ethereum-client-analyzer "devnet=fusaka-devnet-3 client=lighthouse layer=cl period=30m mode=full instances=lighthouse-geth-1,lighthouse-geth-2"
Task ethereum-client-analyzer "devnet=fusaka-devnet-3 client=teku layer=cl period=30m mode=full instances=teku-nethermind-1"
Task ethereum-client-analyzer "devnet=fusaka-devnet-3 client=nimbus layer=cl period=30m mode=full instances=nimbus-geth-1"

# EL subagents (parallel)
Task ethereum-client-analyzer "devnet=fusaka-devnet-3 client=geth layer=el period=30m mode=full instances=lighthouse-geth-1,lighthouse-geth-2,nimbus-geth-1"
Task ethereum-client-analyzer "devnet=fusaka-devnet-3 client=nethermind layer=el period=30m mode=full instances=teku-nethermind-1"
```

Wait for all to complete, then aggregate results.

### Instance Scope Example (auto-detection)

**Step 1**: Query returns log with labels:
```
{testnet="fusaka-devnet-3", instance="lighthouse-geth-1", ethereum_cl="lighthouse", ethereum_el="geth"}
```

**Step 2**: Extract client info → `layer=cl, client=lighthouse`

**Step 3**: Launch subagent:
```
Task ethereum-client-analyzer "devnet=fusaka-devnet-3 client=lighthouse layer=cl period=30m mode=full instance=lighthouse-geth-1"
```

## Timeouts and Retries

| Scope | Timeout per Subagent | Max Retries |
|-------|---------------------|-------------|
| instance | 60s | 2 |
| cl/el | 90s | 2 |
| all | 120s per subagent | 1 |

**Timeout handling**:
- If subagent exceeds timeout → Mark as TIMEOUT in results, continue with others
- Include timeout info in final report

**Retry logic**:
- Retry on: network errors, Loki query failures
- Do not retry on: no data found, parsing errors
- Between retries: wait 5 seconds

## Result Aggregation

Combine subagent outputs into a unified report:

1. **Executive Summary**: Worst-case health status across all analyses
2. **Instance Inventory**: Merged tables from all subagents (preserve all rows)
3. **Issues**: Deduplicated issues across all clients, sorted by severity
4. **Connectivity**: Combined metrics for all instances

**Aggregation rules**:
- Health status: CRITICAL > WARNING > TIMEOUT > HEALTHY (use worst case)
- Preserve all instance rows from all subagents
- Deduplicate identical issues (same message, same instance)
- Group issues by client type for readability

Do not summarize or omit individual instance data.

## Output Format

### Executive Summary
```
| Metric | Value |
|--------|-------|
| Overall Status | CRITICAL / WARNING / HEALTHY |
| Mode | quick / full |
| Devnet | {devnet} |
| Period | {period} |
| CL Clients Analyzed | {list} |
| EL Clients Analyzed | {list} |
| Total Instances | {count} |
| Issues Found | {count} |
| Subagent Failures | {count or "None"} |
```

### Instance Status (all instances from all subagents)
```
| Instance | CL Client | EL Client | Slot/Block | Peers | Sync | Health |
|----------|-----------|-----------|------------|-------|------|--------|
```

### Issues Summary (deduplicated)
```
| Client | Issue | Count | Severity |
|--------|-------|-------|----------|
```

## Debugging Use Cases

Use this command to debug common issues on devnets:

### Quick Health Check
**Question**: "Is the network healthy?"
```bash
analyze-network fusaka-devnet-3 all nodes 30m quick
```
Returns error counts per client in seconds. If all zeros → network is healthy.

### Investigate Specific Client Issues
**Question**: "Lighthouse nodes are having problems"
```bash
analyze-network fusaka-devnet-3 cl lighthouse 30m full
```
Returns detailed error logs, sync status, and peer counts for all Lighthouse instances.

### Debug a Specific Node
**Question**: "Node lighthouse-geth-1 is not syncing"
```bash
analyze-network fusaka-devnet-3 instance lighthouse-geth-1 1h full
```
Deep dive into one instance with full error details and sync progress.

### Compare Client Performance
**Question**: "Which clients are struggling?"
```bash
analyze-network fusaka-devnet-3 all nodes 30m quick
```
Quick mode shows error counts per client - compare to identify problematic clients.

### Check After Deployment
**Question**: "Did the new release break anything?"
```bash
# Quick check first
analyze-network fusaka-devnet-3 all nodes 15m quick

# If issues found, get details
analyze-network fusaka-devnet-3 cl teku 30m full
```

### Investigate Sync Issues
**Question**: "Some nodes are falling behind"
```bash
# Check all CL clients for sync status
analyze-network fusaka-devnet-3 all nodes 30m full
```
Look at the "Sync State" column - nodes with "Syncing" or low slot numbers are behind.

### Check Peer Connectivity
**Question**: "Nodes can't find peers"
```bash
analyze-network fusaka-devnet-3 cl lighthouse 30m full
```
Check the Connectivity table for low peer counts or connection errors.

### Debug EL Issues
**Question**: "Execution layer is having problems"
```bash
analyze-network fusaka-devnet-3 el geth 30m full
```
Analyzes Geth instances for block import issues, sync problems, or errors.

### Monitor During Fork
**Question**: "How are nodes handling the fork?"
```bash
# Quick check across all clients
analyze-network fusaka-devnet-3 all nodes 15m quick

# If issues, check specific clients
analyze-network fusaka-devnet-3 cl prysm 30m full
analyze-network fusaka-devnet-3 cl nimbus 30m full
```

## Command Examples Summary

```bash
# Quick health checks
analyze-network fusaka-devnet-3 all nodes 30m quick      # Fast network health
analyze-network holesky cl lighthouse 15m quick          # Quick Lighthouse check

# Full analysis
analyze-network fusaka-devnet-3 all nodes 30m full       # Complete network analysis
analyze-network holesky cl teku 30m full                 # Detailed Teku analysis
analyze-network sepolia el geth 30m full                 # Detailed Geth analysis

# Instance debugging
analyze-network fusaka-devnet-3 instance lighthouse-geth-1 1h full   # Deep dive one node

# Abbreviated (defaults: period=30m, mode=full)
analyze-network fusaka-devnet-3 all nodes                # Full network analysis
analyze-network fusaka-devnet-3 cl nimbus                # Full Nimbus analysis
```

## Error Handling

- If pre-discovery finds no clients → Report clearly and stop (don't spawn empty subagents)
- If a subagent times out → Mark as TIMEOUT, continue with others, note in summary
- If a subagent fails → Mark as FAILED, continue with others, note failure reason
- If a subagent returns no data → Include in report as "No data" (don't omit)
- Report partial results with clear indication of gaps

### Error Report Format
```
## Subagent Issues

| Client | Status | Reason |
|--------|--------|--------|
| prysm | TIMEOUT | Exceeded 120s |
| lodestar | FAILED | Loki query error |
```
