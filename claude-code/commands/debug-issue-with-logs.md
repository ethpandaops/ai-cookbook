# Debug Issue with Logs

## Overview
Ultrathink. This command enables systematic debugging of issues by analyzing provided logs OR issue descriptions, investigating the codebase, and developing root cause theories. **CRITICAL: This command is for INVESTIGATION ONLY. Claude must NOT attempt to fix the issue, only identify potential root causes.**

## How It Works
1. **User provides input** either as:
   - Logs containing error messages, stack traces, or unusual behavior
   - Description of the issue they're experiencing
2. **Claude analyzes input** to identify symptoms and potential problem areas
3. **Investigates codebase** using various debugging tools and techniques
4. **Collects facts** through API calls, docker commands, and code analysis
5. **Develops theories** presenting 3 potential root causes based on evidence
6. **Documents findings** with reproducible commands for verification

## Instructions for Claude

### STEP 1: Request Input
When invoked, first determine what information the user has:

```
I can help debug your issue. Please choose how you'd like to proceed:

1. **I have logs** - Paste error messages, stack traces, or system logs
2. **I'll describe the issue** - Explain what's happening without logs

What information do you have available?
```

### STEP 2A: Log Analysis Path (ULTRATHINK REQUIRED)
If logs are provided:

1. **Parse and identify key indicators:**
   - Error messages and stack traces
   - Timestamps and sequence of events
   - Affected components or services
   - Resource constraints or limits
   - Network or connectivity issues
   - Permission or access problems

2. **Extract critical information:**
   - Error codes and types
   - File paths and line numbers
   - Function/method names
   - Variable states
   - Environment details

3. **Identify patterns:**
   - Recurring errors
   - Timing correlations
   - Cascading failures
   - Resource exhaustion patterns

### STEP 2B: Description Analysis Path (ULTRATHINK REQUIRED)
If only a description is provided:

1. **Gather detailed information through targeted questions:**
   ```
   To help me investigate, please answer these questions:
   
   • What exactly is happening? (e.g., app crashes, slow performance, incorrect output)
   • When did this start occurring? (specific time, after a deployment, etc.)
   • How frequently does it occur? (always, intermittently, under specific conditions)
   • What were you doing when it happened? (specific user actions, API calls, etc.)
   • Has anything changed recently? (code, configuration, infrastructure)
   • What environment is affected? (development, staging, production)
   • Are there any error messages visible to users?
   ```

2. **Based on description, identify investigation areas:**
   - Component or service likely affected
   - Type of issue (performance, functionality, connectivity)
   - Potential failure points
   - Critical code paths to examine

3. **Proactively gather logs and system state:**
   ```bash
   # Try to retrieve relevant logs based on description
   docker logs <likely_container> --tail 500 --since 1h
   journalctl -u <likely_service> --since "1 hour ago"
   tail -n 1000 /var/log/<application>/*.log
   
   # Check system state
   docker ps -a
   systemctl status <services>
   netstat -tulpn | grep <port>
   ```

### STEP 3: Systematic Investigation
Based on the analysis (logs or description), conduct parallel investigations:

#### Phase 1: Code Investigation (PARALLEL TASKS)
Execute these investigations simultaneously:

```markdown
**Task 1: Examine error location**
- Navigate to specific files/lines mentioned in logs
- Analyze the failing code section
- Check recent commits affecting this area
- Review function dependencies

**Task 2: Search for similar issues**
- Grep for error messages across codebase
- Search for related error handling
- Look for TODO/FIXME comments nearby
- Check for known issues in documentation

**Task 3: Configuration analysis**
- Review configuration files
- Check environment variables
- Verify service dependencies
- Examine deployment settings

**Task 4: Resource and state investigation**
- Check for resource limits (memory, CPU, disk)
- Verify database connections
- Examine network configurations
- Review file permissions
```

#### Phase 2: Dynamic Analysis
Gather runtime information using appropriate tools:

**For containerized applications:**
```bash
# Check container status and resources
docker ps -a
docker stats
docker logs <container_id> --tail 100

# Inspect container configuration
docker inspect <container_id>

# Execute debugging commands inside container
docker exec <container_id> ps aux
docker exec <container_id> df -h
docker exec <container_id> netstat -tulpn
docker exec <container_id> env
```

**For system-level debugging:**
```bash
# Process investigation
ps aux | grep <process_name>
lsof -p <pid>
strace -p <pid> -f

# System resources
top -b -n 1
free -m
df -h
iostat -x 1 5

# Network debugging
netstat -tulpn
ss -tulpn
curl -v <endpoint>
nslookup <domain>
```

**For application-specific debugging:**
```bash
# Database connections
mysql -e "SHOW PROCESSLIST"
psql -c "SELECT * FROM pg_stat_activity"
redis-cli INFO

# API testing
curl -X GET/POST <api_endpoint> -H "Content-Type: application/json" -d '{}'
wget --debug <url>

# Log analysis
tail -f /var/log/<application>.log
journalctl -u <service> -n 100
grep -r "ERROR\|FATAL\|CRITICAL" /var/log/
```

### STEP 4: Evidence Collection
Document all findings systematically:

```markdown
## Debugging Facts Collected

### 1. Initial Analysis Findings
- **Primary Issue**: [Exact error message or described problem]
- **Frequency**: [How often it occurs]
- **First Occurrence**: [When it started]
- **Preceding Events**: [What happened before the issue]

### 2. Code Investigation Results
- **Affected Files**: [List of files involved]
- **Problematic Functions**: [Specific functions/methods]
- **Recent Changes**: [Commits that might be related]
- **Code Patterns**: [Any anti-patterns or issues found]

### 3. System State
- **Resource Usage**: [CPU, Memory, Disk metrics]
- **Service Status**: [Running services and their states]
- **Network Status**: [Connectivity issues]
- **Dependencies**: [External service availability]

### 4. Commands Executed for Verification
```[List all commands run with their outputs]```
```

### STEP 5: Root Cause Theory Development
Based on collected evidence, present THREE distinct theories:

```markdown
## Root Cause Analysis

### Theory 1: [Most Likely Cause]
**Confidence Level**: High/Medium/Low

**Evidence Supporting This Theory:**
- [Specific log entries pointing to this issue]
- [Code analysis findings]
- [System state observations]

**Why This Is The Root Cause:**
[Detailed explanation of the failure mechanism]

**How To Verify:**
```bash
# Commands to confirm this theory
[Specific commands that would prove/disprove this theory]
```

### Theory 2: [Alternative Cause]
**Confidence Level**: High/Medium/Low

**Evidence Supporting This Theory:**
- [Different interpretation of the same evidence]
- [Additional findings]
- [Historical patterns]

**Why This Could Be The Root Cause:**
[Explanation of this failure scenario]

**How To Verify:**
```bash
# Commands to confirm this theory
[Verification commands]
```

### Theory 3: [Less Likely But Possible Cause]
**Confidence Level**: High/Medium/Low

**Evidence Supporting This Theory:**
- [Edge case scenarios]
- [Indirect evidence]
- [Environmental factors]

**Why This Might Be The Root Cause:**
[Explanation of this possibility]

**How To Verify:**
```bash
# Commands to confirm this theory
[Verification commands]
```

## Recommended Next Steps
1. Verify the most likely theory using provided commands
2. Gather additional logs if needed: [Specify what logs would help]
3. Check these specific areas: [List areas needing investigation]
4. Consider these monitoring additions: [Suggest future debugging aids]
```

### STEP 6: Senior Developer Mindset
When debugging, channel the mindset of a senior developer:

1. **Question Assumptions**: Don't trust error messages at face value
2. **Look for Side Effects**: The actual problem might be upstream
3. **Consider Timing**: Race conditions, timeouts, and synchronization issues
4. **Check the Basics**: Permissions, disk space, network connectivity
5. **Review Recent Changes**: What changed recently in code or environment?
6. **Think About Scale**: Issues that only appear under load
7. **Examine Edge Cases**: Null values, empty sets, boundary conditions
8. **Verify Dependencies**: External services, libraries, APIs

## Example Usage

### Example 1: With Logs
```
User: Debug this issue
Claude: I can help debug your issue. Please choose how you'd like to proceed:
1. I have logs - Paste error messages, stack traces, or system logs
2. I'll describe the issue - Explain what's happening without logs

User: 1 [Pastes error logs showing database connection timeout]
Claude: [Ultrathinks and analyzes the logs]
[Investigates code, checks configuration, runs docker/system commands]
[Presents collected facts and three theories about connection pool exhaustion, network issues, or database overload]
```

### Example 2: With Description Only
```
User: Debug this issue
Claude: I can help debug your issue. Please choose how you'd like to proceed:
1. I have logs - Paste error messages, stack traces, or system logs
2. I'll describe the issue - Explain what's happening without logs

User: 2
Claude: To help me investigate, please answer these questions:
[Asks targeted questions]
User: The application becomes unresponsive every day around 2 PM. Users see timeout errors. Started happening after last week's deployment.
Claude: [Ultrathinks about the pattern]
[Proactively gathers logs from the timeframe]
[Investigates deployment changes, cron jobs, traffic patterns]
[Presents three theories about scheduled jobs, traffic spikes, or memory leaks]
```

## Notes for Claude

### DO:
- Use ultrathink for deep analysis
- Run multiple investigations in parallel
- Provide exact commands for fact verification
- Consider multiple interpretations of evidence
- Think like a senior developer with years of debugging experience
- Document everything for reproducibility
- Look beyond the obvious symptoms

### DON'T:
- Attempt to fix the issue
- Make changes to code or configuration
- Assume the first theory is correct
- Skip verification steps
- Ignore environmental factors
- Trust error messages blindly
- Focus only on the immediate error location

### Debugging Principles:
- **Correlation != Causation**: Just because two things happen together doesn't mean one causes the other
- **Occam's Razor**: The simplest explanation is often correct, but verify it
- **Five Whys**: Keep asking "why" to get to the root cause
- **Reproduce First**: If possible, reproduce the issue before theorizing
- **Isolate Variables**: Change one thing at a time when testing theories
- **Document Everything**: Future you (or others) will thank you

---

**IMPORTANT**: This is a debugging investigation command. Focus on understanding and identifying root causes. Do NOT implement fixes or modifications. Wait for the user to provide either logs or an issue description before beginning the analysis.