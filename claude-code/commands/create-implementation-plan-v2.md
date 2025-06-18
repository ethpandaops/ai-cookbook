# Create Implementation Plan

## Overview
Ultrathink. This command generates a comprehensive implementation plan that serves as both a user-facing roadmap and Claude's technical reference. **CRITICAL: This command is for PLANNING ONLY. Claude must NOT implement anything during plan creation.**

The plan consists of two key parts:

1. **User-Facing Executive Summary**: A detailed overview that explains what is changing and why specific changes are needed. Includes data flow diagrams when relevant.

2. **Claude's Implementation Reference**: Structured tasks with technical specifics and actionable checklists for future implementation.

### Key Principles
- **PLANNING ONLY**: Never implement during plan creation. Research and plan only.
- **MAXIMIZE PARALLELIZATION**: Structure plans to identify independent tasks for parallel execution.
- **Research Through Subtasks**: Use subtasks to gather missing information from the user.
- **Checklist Format**: All implementation tasks MUST be in checklist format.
- **Minimize Sequential Dependencies**: Only enforce sequential ordering when absolutely required.
- **Actionable Steps**: Each task must contain enough context for independent execution.
- **Location**: Plans are created in `./ai_plans/$PLAN_NAME.md`

## Plan Structure

### 1. Executive Summary (User-Focused)
Create a comprehensive overview that stakeholders can read to understand the full scope:

```markdown
# [Feature/System Name] Implementation Plan

## Executive Summary
> A concise overview that covers:
> - Problem statement
> - Proposed solution
> - Technical approach
> - Data flow (when relevant)
> - Expected outcomes

## Goals & Objectives
### Primary Goals
- [Main business objective with measurable success criteria]
- [Key technical achievement with specific metrics]

### Secondary Objectives
- [Additional benefits and improvements]
- [Long-term maintainability goals]

## Solution Overview
### Approach
[Concise explanation of solution architecture and key changes]

### Key Components
1. **[Component Name]**: [What changes and why]
2. **[Component Name]**: [What changes and why]

### Architecture Diagram
[ASCII diagram when system architecture changes - omit if not relevant]
```
[User] → [API] → [Database]
   ↓        ↓         ↓
[Cache] → [Queue] → [Service]
```

### Data Flow
[ASCII diagram showing data movement when relevant]
```
Input → Process → Output
  ↓       ↓        ↓
Validate → Transform → Store
```

### Expected Outcomes
- [Specific, measurable outcomes]
- [Technical improvements]
```

### 2. Technical Implementation (Claude-Focused)
Structured tasks for actual implementation work with **EXPLICIT PARALLELIZATION**:

```markdown
## Implementation Tasks

### Parallel Execution Groups

#### Group A: Independent Foundation Tasks (Execute ALL in parallel)
- [ ] **Task A.1**: [Database schema setup]
  - Files: [List of files to create/modify]
  - Dependencies: None (can run immediately)
  
- [ ] **Task A.2**: [API endpoint scaffolding]
  - Files: [List of files to create/modify]
  - Dependencies: None (can run immediately)
  
- [ ] **Task A.3**: [Frontend component structure]
  - Files: [List of files to create/modify]
  - Dependencies: None (can run immediately)

#### Group B: Core Implementation (Execute after Group A completes)
- [ ] **Task B.1**: [Business logic implementation]
  - Dependencies: A.1 (database must exist)
  - Can run parallel with: B.2, B.3
  
- [ ] **Task B.2**: [API integration]
  - Dependencies: A.2 (endpoints must exist)
  - Can run parallel with: B.1, B.3
  
- [ ] **Task B.3**: [UI components]
  - Dependencies: A.3 (component structure)
  - Can run parallel with: B.1, B.2

#### Group C: Integration & Testing (Sequential where needed)
[Testing tasks with clear dependency chains...]
```

## Creating the Plan

### STEP 1: Research & Discovery
**Use subtasks to gather necessary information:**
- Analyze existing codebase structure
- Identify current limitations
- Research similar implementations
- **Ask the user for any unclear requirements**

### STEP 2: Dependency Analysis (CRITICAL)
**Analyze task dependencies to maximize parallelization:**
- Identify which tasks can run completely independently
- Group tasks that share no dependencies for parallel execution
- Map out the minimal sequential dependencies
- Structure the plan to maximize concurrent execution

### STEP 3: Draft Executive Summary
Write a concise overview that addresses:
- Problem statement
- Solution architecture and approach
- Expected outcomes
- Data flow (when relevant)

### STEP 4: Define Implementation Tasks with Parallel Groups
Create detailed, actionable tasks organized by parallel execution groups:
- **Group independent tasks** that can run simultaneously
- **Explicitly mark parallel opportunities** in each task
- **Minimize sequential chains** - only enforce ordering when absolutely necessary
- Include code examples for complex implementations
- Each task should be self-contained with clear inputs/outputs

### STEP 5: Validate & Optimize for Parallelization
Before finalizing:
- Review for additional parallelization opportunities
- Ensure task groupings maximize concurrent execution
- Verify dependencies are truly necessary
- Break large sequential tasks into smaller parallel subtasks

## Example Usage

```bash
# User request
"Create an implementation plan for adding real-time notifications to our app"

# Claude's approach:
1. Uses subtasks to research:
   - Current notification infrastructure
   - User requirements (ask: "What types of notifications? Push, email, in-app?")
   - Performance requirements (ask: "Expected notification volume?")
   - Integration preferences (ask: "Preferred notification service?")

2. Creates comprehensive plan with:
   - Detailed executive summary explaining the notification system
   - Technical tasks for WebSocket setup, event handling, UI components
   - Testing strategy and rollout plan
```

## Best Practices

1. **PARALLELIZE AGGRESSIVELY**: Always look for opportunities to run tasks concurrently. Question every sequential dependency.
2. **Research First**: Use subtasks to gather complete information before writing the plan
3. **Ask Questions**: Ask the user for clarification on requirements
4. **Be Specific**: Include concrete details, file paths, and code examples
5. **Consider Scale**: Address performance, security, and maintainability
6. **Maximize Parallel Execution**: Structure the plan to maximize concurrent execution
7. **Clear Dependencies**: Only enforce sequential ordering when absolutely necessary

### Parallelization Examples
- **Good**: "Tasks A.1, A.2, and A.3 can all run in parallel as they touch different parts of the codebase"
- **Better**: "Execute all 5 foundation tasks simultaneously"
- **Best**: "Group A (5 tasks) runs fully parallel, Group B (3 tasks) starts after A completes but B tasks run parallel with each other"

Remember: The executive summary is for humans to understand what is changing. The implementation tasks are for Claude to execute with MAXIMUM PARALLELIZATION. Both should be concise and focused.

---

---

**CRITICAL REMINDER FOR CLAUDE**: 
- This command is for PLANNING ONLY - never implement during plan creation
- Research first, then plan
- Focus on what changes and why specific changes are needed
- Include ASCII diagrams only when they clarify architecture or data flow
- Keep all explanations concise and actionable
- Maximize parallelization opportunities

**IMPORTANT**: This document provides guidelines for creating implementation plans. DO NOT start creating a plan yet. Wait for the user's specific instructions about what implementation plan to create.