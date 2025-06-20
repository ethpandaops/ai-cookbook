# Review Implementation Plan

## Overview
This command facilitates a systematic review of an existing implementation plan. It analyzes the plan file and guides through each proposed change one by one, allowing for feedback before any updates are made.

## Purpose
- Analyze an existing implementation plan created by `create-implementation-plan-v2`
- Review each proposed change individually
- Collect feedback on each change
- Only update the plan when explicitly instructed

## Usage
```bash
# Simply invoke the command
"review-implementation-plan"
# Claude will prompt you for the plan file location
```

## Process

### STEP 1: Setup and Plan Selection
- Prompt the user to provide the implementation plan file path
- Wait for user to specify the plan location
- Validate that the file exists and is readable
- Do NOT proceed to analysis until a valid plan file is provided
- Example prompt: "Please provide the path to the implementation plan you'd like to review (e.g., @ai_plans/notification-system.md)"

### STEP 2: Load and Analyze Plan
- Read the specified plan file
- Parse the structure to identify all proposed changes
- Create an internal index of all tasks and modifications

### STEP 3: Codebase Analysis
- Analyze the current codebase relevant to the plan
- Identify existing implementations that would be affected
- Map out dependencies and potential conflicts
- Note any discrepancies between plan assumptions and actual code

### STEP 4: Step-by-Step Review
For each proposed change in the plan:

1. **Present the Change**
   - Show the specific task or modification
   - Display relevant context from the plan
   - Show current state of affected files/components

2. **Analyze Impact**
   - Explain what this change would affect
   - Identify potential risks or dependencies
   - Suggest any concerns or improvements

3. **Wait for Feedback**
   - Pause for user input on this specific change
   - Options: approve, modify, skip, or request more details
   - Do NOT proceed to next change until feedback received

4. **Document Feedback**
   - Record user's decision and comments
   - Keep track of approved/rejected/modified items
   - Maintain review state throughout session

### STEP 5: Summary and Next Steps
After reviewing all changes:
- Provide summary of review decisions
- List approved changes
- List items needing modification
- Only update the plan when explicitly asked: "update the plan with the feedback"

## Example Interaction

```
User: "review-implementation-plan"

Claude: I'll help you review an implementation plan. Please provide the path to the implementation plan you'd like to review (e.g., @ai_plans/notification-system.md)

User: "@ai_plans/auth-system.md"

Claude: Thank you. I'll analyze the implementation plan at @ai_plans/auth-system.md and review it with you step by step.

[Reads plan and analyzes codebase]

I've analyzed the plan which contains 8 proposed changes across 3 parallel execution groups. Let me walk through each one:

**Change 1/8: Database Schema Setup (Group A.1)**
- Task: Create new auth tables for session management
- Files affected: `migrations/`, `src/db/schema.ts`
- Current state: No auth-specific tables exist

My analysis: This is a foundational change that other tasks depend on. The schema looks appropriate but consider adding an index on the session token for performance.

How would you like to proceed with this change? (approve/modify/skip/details)

User: "approve, but add the index suggestion"

Claude: Noted. I'll include the index recommendation when we update the plan.

**Change 2/8: API Endpoint Scaffolding (Group A.2)**
[Continues with next change...]
```

## Key Behaviors

1. **Never Auto-Proceed**: Always wait for explicit feedback on each change
2. **Provide Context**: Show both the planned change and current state
3. **Analytical Approach**: Offer insights about risks, dependencies, and improvements
4. **No Premature Updates**: Only modify the plan when explicitly instructed
5. **Maintain State**: Track all feedback throughout the review session

## Important Notes

- This command is for REVIEW ONLY - no implementation during review
- The plan file remains unchanged until user explicitly requests updates
- Each change is reviewed individually with full context
- User maintains complete control over the review pace
- All feedback is collected before any plan modifications

## Integration with create-implementation-plan-v2

This command is designed to work seamlessly after running `create-implementation-plan-v2`:
1. Generate plan with `create-implementation-plan-v2`
2. Review plan with `review-implementation-plan`
3. Update plan based on feedback (only when requested)
4. Proceed with implementation using the refined plan

---

**REMINDER FOR CLAUDE**: 
- Read the entire plan before starting the review
- Analyze actual codebase to provide informed feedback
- Never skip ahead - review one change at a time
- Wait for explicit user feedback before proceeding
- Do not modify the plan unless explicitly asked