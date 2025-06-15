# Create Implementation Plan

## Overview
This command generates a comprehensive implementation plan that serves as both a user-facing roadmap and Claude's technical reference. The plan consists of two key parts:

1. **User-Facing Executive Summary**: A detailed, fleshed-out overview that explains the what, why, and how of the implementation in clear business and technical terms. This section should be thorough enough that stakeholders can understand the full scope and impact of the work.

2. **Claude's Implementation Reference**: Structured tasks with technical specifics, code examples, and actionable checklists that Claude will use during actual implementation. These tasks are more granular and technical in nature.

### Key Principles
- **MAXIMIZE PARALLELIZATION**: Claude has the ability to execute multiple tasks concurrently. This is CRITICAL for performance. Structure plans to identify and execute independent tasks in parallel whenever possible.
- **Research Through Subtasks**: When creating the plan, Claude should use subtasks to conduct research and gather any missing information from the user. This ensures the plan is complete and accurate before finalization.
- **Checklist Format**: All implementation tasks MUST be in checklist format for progress tracking
- **Minimize Sequential Dependencies**: Analyze task dependencies carefully and structure the plan to reduce unnecessary sequential task flow. Only enforce sequential ordering when absolutely required.
- **Actionable Steps**: Each task must contain enough context and detail to be independently executable
- **Location**: Plans are created in `./ai_plans/$PLAN_NAME.md`

## Plan Structure

### 1. Executive Summary (User-Focused)
Create a comprehensive overview that stakeholders can read to understand the full scope:

```markdown
# [Feature/System Name] Implementation Plan

## Executive Summary
> A detailed 3-5 paragraph overview that covers:
> - Business context and problem statement
> - Proposed solution and its benefits
> - High-level technical approach
> - Expected impact and outcomes
> - Timeline and resource considerations

## Goals & Objectives
### Primary Goals
- [Main business objective with measurable success criteria]
- [Key technical achievement with specific metrics]

### Secondary Objectives
- [Additional benefits and improvements]
- [Long-term maintainability goals]

## Solution Overview
### Approach
[2-3 paragraphs explaining the solution architecture, key design decisions, and rationale]

### Key Components
1. **[Component Name]**: [Business purpose and technical role]
2. **[Component Name]**: [Business purpose and technical role]

### Expected Outcomes
- [Specific, measurable business outcomes]
- [Technical improvements and metrics]
- [User experience enhancements]
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
**Use subtasks to gather all necessary information:**
- Analyze existing codebase structure
- Identify current limitations or pain points
- Research similar implementations or patterns
- **Ask the user for any unclear requirements or preferences**

### STEP 2: Dependency Analysis (CRITICAL)
**Analyze task dependencies to maximize parallelization:**
- Identify which tasks can run completely independently
- Group tasks that share no dependencies for parallel execution
- Map out the minimal sequential dependencies
- Structure the plan to reduce total execution time by running independent tasks concurrently

### STEP 3: Draft Executive Summary
Write a comprehensive overview that addresses:
- Problem statement and business case
- Solution architecture and approach
- Expected benefits and outcomes
- Risk assessment and mitigation strategies

### STEP 4: Define Implementation Tasks with Parallel Groups
Create detailed, actionable tasks organized by parallel execution groups:
- **Group independent tasks** that can run simultaneously
- **Explicitly mark parallel opportunities** in each task
- **Minimize sequential chains** - only enforce ordering when absolutely necessary
- Include code examples for complex implementations
- Each task should be self-contained with clear inputs/outputs

### STEP 5: Validate & Optimize for Parallelization
Before finalizing:
- Review the plan to identify any additional parallelization opportunities
- Ensure task groupings maximize concurrent execution
- Verify that dependencies are truly necessary (not just convenient)
- Consider breaking large sequential tasks into smaller parallel subtasks

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

1. **PARALLELIZE AGGRESSIVELY**: This is the #1 priority. Always look for opportunities to run tasks concurrently. Question every sequential dependency.
2. **Research First**: Always use subtasks to gather complete information before writing the plan
3. **Ask Questions**: Don't assume - ask the user for clarification on requirements
4. **Be Specific**: Include concrete details, file paths, and code examples
5. **Consider Scale**: Address performance, security, and maintainability upfront
6. **Optimize Execution Time**: Structure the plan to minimize total runtime by maximizing parallel execution
7. **Clear Dependencies**: Only enforce sequential ordering when absolutely necessary - challenge every dependency

### Parallelization Examples
- **Good**: "Tasks A.1, A.2, and A.3 can all run in parallel as they touch different parts of the codebase"
- **Better**: "Execute all 5 foundation tasks simultaneously, reducing setup time from 50 minutes sequential to 10 minutes parallel"
- **Best**: "Group A (5 tasks) runs fully parallel, Group B (3 tasks) starts after A completes but B tasks run parallel with each other"

Remember: The executive summary is for humans to read and understand the full picture. The implementation tasks are for Claude to execute with MAXIMUM PARALLELIZATION. Both should be detailed but serve different audiences.

---

**IMPORTANT FOR CLAUDE**: This document provides the structure and guidelines for creating implementation plans. DO NOT start creating a plan yet. This is just context loading. The user will provide specific instructions about what implementation plan to create in their next message. Wait for those instructions before beginning work.

**CRITICAL REMINDER**: THIS IS THE STRUCTURE OF A PLAN. DO NOT START IMPLEMENTATION YET. DO NOT MODIFY ANY FILES. AWAIT INSTRUCTIONS FROM THE USER. Your only task is to CREATE THE PLAN DOCUMENT in `./ai_plans/$PLAN_NAME.md` - nothing more.