# Debug Issue with Logs

Systematic debugging command for root cause investigation. **Investigation only - do NOT fix issues.**

## Workflow

1. User provides logs OR describes issue
2. Determine investigation approach (see Tool Selection below)
3. Analyze symptoms and identify investigation areas
4. Investigate codebase and gather runtime data
5. Present 3 root cause theories with verification commands

## Tool Selection

Choose the right approach based on the issue type:

| Issue Type | Recommended Approach | When to Use |
|------------|---------------------|-------------|
| Ethereum client (CL/EL) | `ethereum-client-analyzer` agent | Client sync issues, errors, peer connectivity |
| ethPandaOps devnet/testnet | Direct MCP tools | Custom queries, metrics correlation, non-client logs |
| Local application | Standard debugging | Codebase issues, local logs |

### For Ethereum Client Issues

Use the `ethereum-client-analyzer` agent via Task tool:

```
Task tool with subagent_type: ethereum-client-analyzer
prompt: "Analyze {client} on {devnet}, layer={cl|el}, period=30m, mode={quick|full}"
```

**Parameters:**
- `devnet`: fusaka-devnet-3, holesky, sepolia, etc.
- `client`: lighthouse, teku, prysm, geth, nethermind, etc.
- `layer`: cl (consensus) or el (execution)
- `mode`: quick (fast health check) or full (detailed analysis)

The agent handles phased querying automatically to minimize token usage.

### For Custom ethPandaOps Queries

Use MCP tools directly when you need:
- Custom LogQL/PromQL queries
- Cross-service correlation
- Metrics + logs together
- ClickHouse (Xatu) blockchain data

**Available MCP Tools:**

| Tool | Purpose | Example Use |
|------|---------|-------------|
| `loki_tool` | Container logs | `{testnet="fusaka-devnet-3"} \|~ "error"` |
| `prometheus_tool` | Devnet metrics | `ethereum_slots_head{network="fusaka-devnet-3"}` |
| `clickhouse_tool` | Xatu blockchain data | Beacon block analysis, attestation queries |

**Key Labels for Filtering:**
- Devnets: `testnet`, `network`, `ethereum_cl`, `ethereum_el`, `instance`
- Platform: `ingress_user`, `container`, `pod`, `namespace`

**Always use these Loki settings:**
```
compact: true
limit: 50
max_line_length: 300
```

## Step 1: Get Input

Ask user:
- **Option 1**: Paste logs (errors, stack traces, system logs)
- **Option 2**: Describe the issue (what, when, how often, what changed)
- **Option 3**: Specify devnet/client for Ethereum-specific investigation

## Step 2: Analyze Input

**From logs**, extract:
- Error messages, codes, stack traces
- Timestamps and event sequence
- Affected components, file paths, line numbers
- Resource/network/permission indicators

**From description**, identify:
- Likely affected components
- Issue type (performance, functionality, connectivity)
- Critical code paths to examine

## Step 3: Parallel Investigation

Run these investigation phases concurrently:

| Phase | Focus | Key Actions |
|-------|-------|-------------|
| Code | Error location | Check files/lines in logs, recent commits, dependencies |
| Config | Settings | Environment vars, config files, service dependencies |
| Runtime | System state | Container/process status, resources, network |
| Logs | Patterns | Grep for errors, check related services |

**Local investigation commands** (use as needed):
- `docker ps -a`, `docker logs <container> --tail 100`
- `docker inspect <container>`, `docker stats`
- `ps aux`, `top -b -n 1`, `free -m`, `df -h`
- `netstat -tulpn`, `curl -v <endpoint>`

### Ethereum/Devnet Investigation (MCP Tools)

For ethPandaOps infrastructure issues, query remotely:

**1. Check health first:**
```
mcp__ethpandaops-production-data__health_check()
```

**2. Discover available labels:**
```
loki_tool(action="labels", start="now-1h")
loki_tool(action="label_values", label="testnet", start="now-1h")
```

**3. Error aggregation (understand volume before fetching):**
```
loki_tool(
  action="query",
  query='count_over_time({testnet="fusaka-devnet-3"} |~ "(?i)error" [30m])',
  start="now-30m",
  compact=true
)
```

**4. Targeted log fetch:**
```
loki_tool(
  action="query",
  query='{testnet="fusaka-devnet-3", ethereum_cl="lighthouse"} |~ "(?i)(error|warn)"',
  start="now-30m",
  limit=50,
  compact=true,
  max_line_length=300
)
```

**5. Metrics correlation:**
```
prometheus_tool(
  query='ethereum_slots_head{network="fusaka-devnet-3"}',
  mode="range",
  start="now-1h",
  step="30s"
)
```

**6. Xatu blockchain data (ClickHouse):**
```
clickhouse_tool(
  sql='SELECT slot, proposer_index FROM beacon_api_eth_v2_beacon_block WHERE network = \'fusaka-devnet-3\' ORDER BY slot DESC LIMIT 10',
  from="now-1h"
)
```

**Common LogQL Filters:**
| Filter | Purpose |
|--------|---------|
| `\|~ "(?i)error"` | Case-insensitive error match |
| `\|!~ "health.?check"` | Exclude health checks |
| `\|= "slot"` | Exact string match |

## Step 4: Document Findings

Collect facts in structured format:

```
## Findings
- Primary Issue: [exact error/symptom]
- Affected Files: [list]
- System State: [resources, services, network]
- Recent Changes: [relevant commits/deployments]
```

## Step 5: Present 3 Theories

For each theory, provide:

```
### Theory N: [Name]
**Confidence**: High/Medium/Low

**Evidence**:
- [specific log entries]
- [code analysis findings]
- [system observations]

**Mechanism**: [how this causes the issue]

**Verify**:
[specific commands to prove/disprove]
```

## Debugging Principles

- Question assumptions - error messages can mislead
- Look upstream - actual problem may not be at error location
- Check basics - permissions, disk, network, dependencies
- Consider timing - race conditions, timeouts
- Review recent changes - code and environment
- Reproduce before theorizing when possible

## Rules

**DO**:
- Use parallel investigation
- Provide exact verification commands
- Consider multiple interpretations
- Document everything
- Use `ethereum-client-analyzer` agent for Ethereum client issues (saves tokens, structured output)
- Always use `compact=true` and `limit=50` for Loki queries
- Check error counts (aggregation) before fetching full logs

**DON'T**:
- Fix issues or modify code/config
- Assume first theory is correct
- Skip verification or trust errors blindly
- Use `limit > 100` for Loki queries (token overflow)
- Query more than 1h without pagination (split into 30m windows)
- Forget to filter by devnet/testnet label

## Datasource Reference

| UID | Type | Description |
|-----|------|-------------|
| P8E80F9AEF21F6940 | Loki | Container logs - filter by `testnet`, `ethereum_cl`, `ethereum_el` |
| P3893C6D10EAD8176 | Prometheus | Devnet metrics - use `network` label |
| P4169E866C3094E38 | VictoriaMetrics | Platform metrics - use `ingress_user`, `container`, `pod` |
| PDE22E36FB877C574 | ClickHouse | Xatu blockchain data - always filter by partition key |
