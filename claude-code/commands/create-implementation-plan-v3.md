# Create Implementation Plan Command

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

---

## PLAN OUTPUT TEMPLATE

**This is the EXACT structure that must appear in every generated plan file:**

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
```

### Data Flow
[ASCII diagram showing data movement - omit if not relevant]
```
Input → Process → Output
```

### Expected Outcomes
- [Specific, technical outcomes that are not "vibes" or "feelings". E.g. "The user can now login to the app"]

## Implementation Tasks

### CRITICAL IMPLEMENTATION RULES
1. **NO PLACEHOLDER CODE**: Every implementation must be production-ready. NEVER write "TODO", "in a real implementation", or similar placeholders unless explicitly requested by the user.
2. **CROSS-DIRECTORY TASKS**: Group related changes across directories into single tasks to ensure consistency. Never create isolated changes that require follow-up work in sibling directories.
3. **COMPLETE IMPLEMENTATIONS**: Each task must fully implement its feature including all consumers, type updates, and integration points.
4. **DETAILED SPECIFICATIONS**: Each task must include EXACTLY what to implement, including specific functions, types, and integration points to avoid "breaking change" confusion.
5. **CONTEXT AWARENESS**: Each task is part of a larger system - specify how it connects to other parts.
6. **MAKE BREAKING CHANGES**: Unless explicitly requested by the user, you MUST make breaking changes.

### Visual Dependency Tree
[Shows folder structure, files, and what each task accomplishes]

```
src/
├── app.tsx (Task #12: Wire all routes, providers, and layouts into main app)
├── router.tsx (Task #11: Setup routing with all feature routes)
│
├── routes/
│   ├── userRoutes.ts (Task #8: Define all user-related routes)
│   └── productRoutes.ts (Task #9: Define all product-related routes)
│
├── api/
│   ├── users/
│   │   └── controller.ts (Task #7: HTTP handlers for user CRUD operations)
│   └── products/
│       └── controller.ts (Task #7: HTTP handlers for product operations)
│
├── services/
│   ├── userService.ts (Task #5: Business logic for user operations)
│   └── productService.ts (Task #5: Business logic for product operations)
│
├── models/
│   ├── User.ts (Task #3: Database model with CRUD methods)
│   └── Product.ts (Task #3: Database model with CRUD methods)
│
├── validation/
│   ├── userValidation.ts (Task #4: Input validation schemas)
│   └── productValidation.ts (Task #4: Input validation schemas)
│
├── types/
│   ├── user.ts (Task #1: User, UserRole, UserProfile interfaces)
│   ├── product.ts (Task #1: Product, Category interfaces)
│   └── auth.ts (Task #0: AuthToken, Session interfaces)
│
├── utils/
│   ├── database.ts (Task #2: Connection pool and query helpers)
│   ├── validation.ts (Task #0: Reusable validators like email, phone)
│   └── crypto.ts (Task #0: Password hashing, token generation)
│
├── components/
│   ├── Layout.tsx (Task #10: Main app layout wrapper)
│   └── Navigation.tsx (Task #6: Nav bar with auth-aware menu)
│
├── contexts/
│   └── AuthContext.tsx (Task #6: Auth state and methods)
│
└── constants/
    └── navigation.ts (Task #0: Route paths and nav items)
```

### Execution Plan

#### Group A: Foundation (Execute all in parallel)
- [ ] **Task #0**: Create validation utilities
  - Folder: `src/utils/`
  - File: `validation.ts`
  - Implements: validateEmail(), validatePhone(), validatePassword(), isValidUUID()
  - Exports: All validation functions for use by other modules
  - Context: These are pure functions used by validation schemas throughout the app

- [ ] **Task #0**: Create crypto utilities
  - Folder: `src/utils/`
  - File: `crypto.ts`
  - Implements: hashPassword(), verifyPassword(), generateToken(), generateSalt()
  - Exports: All crypto functions for auth system
  - Context: Used by auth service for user authentication

- [ ] **Task #0**: Create navigation constants
  - Folder: `src/constants/`
  - File: `navigation.ts`
  - Implements: ROUTES object with all paths, NAV_ITEMS array for menu
  - Exports: ROUTES, NAV_ITEMS
  - Context: Central source of truth for all navigation in the app

- [ ] **Task #0**: Create auth type definitions
  - Folder: `src/types/`
  - File: `auth.ts`
  - Implements: AuthToken, Session, LoginCredentials, AuthState interfaces
  - Exports: All auth-related TypeScript types
  - Context: Type safety for authentication system

#### Group B: Core Types (Execute all in parallel after Group A)
- [ ] **Task #1**: Create user type definitions
  - Folder: `src/types/`
  - File: `user.ts`
  - Implements: 
    ```typescript
    interface User {
      id: string;
      email: string;
      passwordHash: string;
      role: UserRole;
      profile: UserProfile;
      createdAt: Date;
      updatedAt: Date;
    }
    interface UserProfile {
      firstName: string;
      lastName: string;
      avatar?: string;
    }
    enum UserRole {
      ADMIN = 'admin',
      USER = 'user'
    }
    ```
  - Exports: User, UserProfile, UserRole, CreateUserDTO, UpdateUserDTO
  - Context: Core user types used by models, services, and API layers

- [ ] **Task #2**: Create database utilities
  - Folder: `src/utils/`
  - File: `database.ts`
  - Implements: Database connection pool, query(), transaction(), migrate()
  - Exports: db instance, query helpers, transaction wrapper
  - Context: All database operations go through this module

[Continue with detailed specifications for each task...]

---

## Implementation Workflow

This plan file serves as the authoritative checklist for implementation. When implementing:

### Required Process
1. **Load Plan**: Read this entire plan file before starting
2. **Sync Tasks**: Create TodoWrite tasks matching the checkboxes below
3. **Execute & Update**: For each task:
   - Mark TodoWrite as `in_progress` when starting
   - Update checkbox `[ ]` to `[x]` when completing
   - Mark TodoWrite as `completed` when done
4. **Maintain Sync**: Keep this file and TodoWrite synchronized throughout

### Critical Rules
- This plan file is the source of truth for progress
- Update checkboxes in real-time as work progresses
- Never lose synchronization between plan file and TodoWrite
- Mark tasks complete only when fully implemented (no placeholders)
- Tasks should be run in parallel, unless there are dependencies, using subtasks, to avoid context bloat.

### Progress Tracking
The checkboxes above represent the authoritative status of each task. Keep them updated as you work.
```

**END OF TEMPLATE**

---

## Creating the Plan - Detailed Instructions for Claude

### STEP 1: Research & Discovery
**Use subtasks to gather necessary information:**
- Analyze existing codebase structure
- Identify current limitations
- Research similar implementations
- All Subtasks MUST be told to 'ultrathink' in their prompt.
- **Ask the user for any unclear requirements**

### STEP 2: Build Task Dependency Tree (CRITICAL)
**Create two linked structures: a visual tree and an execution plan:**

#### Tree Building Process
1. **Map all files** that need to be created/modified
2. **Trace dependencies** - what imports what?
3. **Assign task numbers** - lower numbers = fewer dependencies
4. **Group by execution order** - tasks with same dependencies go in same group

#### Visual Tree Format
- Show file structure with task references
- Each node shows: `filename (Task #X)`
- Task numbers increase with dependency depth
- Multiple tasks can have the same number if at same level

#### Execution Plan Format
- Group tasks that can run in parallel
- Each task shows:
  - Task number
  - File to create/modify
  - Dependencies (other task numbers)
  - Brief description

#### Dynamic Sizing
- Tree can be any size needed
- Task numbers are generated based on actual dependencies
- Groups are created based on parallelization opportunities
- No limit on number of tasks or groups

### STEP 3: Draft Executive Summary
Write a concise overview that addresses:
- Problem statement
- Solution architecture and approach
- Expected outcomes
- Data flow (when relevant)

### STEP 4: Define Detailed Implementation Tasks
**CRITICAL: Be extremely specific about what each task must implement:**

#### Task Detail Requirements
For EVERY task, you MUST specify:
1. **Folder and file paths**
2. **Complete list of imports** (with exact paths)
3. **Every function/class/type to implement** (with full signatures)
4. **All exports** the module will provide
5. **How it integrates** with other parts of the system
6. **Example usage** if the API isn't obvious

#### Why This Level of Detail?
- **Prevents "breaking changes" confusion**: When Claude implements a task, it knows EXACTLY what's expected, otherwise subtasks are unaware of the full context of the task, and won't want to make breaking changes, effectively making the plan file useless.
- **Enables true parallelism**: Tasks are self-contained with clear boundaries
- **Avoids implementation guesswork**: No ambiguity about "complete" implementation

#### Example of PROPER Task Specification
```markdown
Task #3: Create User Model
- Folder: src/models/
- File: User.ts
- Imports:
  - import { User, CreateUserDTO } from '../types/user'
  - import { db } from '../utils/database'
  - import { generateUUID } from '../utils/crypto'
- Implements:
  - class UserModel with methods:
    - static async create(data: CreateUserDTO): Promise<User>
    - static async findById(id: string): Promise<User | null>
    - static async findByEmail(email: string): Promise<User | null>
    - static async update(id: string, data: Partial<User>): Promise<User>
    - static async delete(id: string): Promise<boolean>
    - static async list(limit: number, offset: number): Promise<User[]>
- SQL queries:
  - CREATE: INSERT INTO users (id, email, password_hash, ...) VALUES (?, ?, ?, ...)
  - SELECT: With proper column mapping
- Exports: UserModel class
- Integration: Used by userService for all database operations
- Note: This is the ONLY place that touches the users table directly
```

#### Task Grouping Rules
- **Group by dependency level**, not by feature
- **Same group = can run in parallel**
- **Cross-directory changes** stay in one task if they're tightly coupled
- **Be explicit** about what each task produces for other tasks to consume

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

0. **Use Subtasks**: Use subtasks to not overload Claude's context window. Each task in the plan should be a standalone subtask.
1. **PARALLELIZE AGGRESSIVELY**: Always look for opportunities to run tasks concurrently. Question every sequential dependency.
2. **Research First**: Use subtasks to gather complete information before writing the plan
3. **Ask Questions**: Ask the user for clarification on requirements
4. **Be Specific**: Include concrete details, file paths, and code examples
5. **Consider Scale**: Address performance, security, and maintainability
6. **Maximize Parallel Execution**: Structure the plan to maximize concurrent execution
7. **Clear Dependencies**: Only enforce sequential ordering when absolutely necessary
8. **Complete Implementations**: Every task must result in fully working code with all integrations

### Parallelization Examples
- **Good**: "Tasks A.1, A.2, and A.3 can all run in parallel as they touch different parts of the codebase"
- **Better**: "Execute all 5 foundation tasks simultaneously"
- **Best**: "Group A (5 tasks) runs fully parallel, Group B (3 tasks) starts after A completes but B tasks run parallel with each other"

## FORBIDDEN PATTERNS

**NEVER include these in implementation plans:**
1. `// TODO: implement this later`
2. `// In a real implementation, we would...`
3. `// This is a placeholder for...`
4. `// Would need to update consumers in other directories`
5. Any form of stub, mock, or incomplete implementation (unless explicitly for testing)

**NEVER structure tasks like this:**
- ❌ "Create types in types/ directory"
- ❌ "Later, update components to use new types"
- ❌ "In a follow-up task, integrate with API"

**ALWAYS structure tasks like this:**
- ✅ "Implement feature X including types, API integration, and all component updates"
- ✅ "Create authentication system with middleware, types, API routes, and frontend integration"

## Using the Plan During Implementation (Documentation)

The "Implementation Workflow" section gets embedded in every plan file. This section provides additional context for understanding the workflow:

### Key Benefits

- **Clean Context Support**: Implementation instructions are embedded in plan files, allowing Claude to work effectively even with a clean context
- **Progress Persistence**: Plan file checkboxes serve as persistent progress tracking across sessions
- **Single Source of Truth**: Reduces confusion by making the plan file the authoritative progress database

### Typical User Workflow

```markdown
User: "Create implementation plan for feature X"
→ Claude creates ./ai_plans/feature-x.md with embedded workflow instructions

User: (later, possibly clean context) "Implement the plan in ./ai_plans/feature-x.md"  
→ Claude reads plan file, sees workflow instructions, implements accordingly
```

## CRITICAL REMINDERS FOR CLAUDE

- This command is for PLANNING ONLY - never implement during plan creation
- Research first, then plan
- Focus on what changes and why specific changes are needed
- Include ASCII diagrams only when they clarify architecture or data flow
- Keep all explanations concise and actionable
- Maximize parallelization opportunities
- **GROUP CROSS-DIRECTORY CHANGES**: Never create tasks that leave incomplete implementations requiring follow-up work in sibling directories
- **NO PLACEHOLDERS OR TODOS**: Every task must describe complete, production-ready implementations
- **FORBIDDEN PHRASES**: Never use "TODO", "in a real implementation", "would need to update", or similar deferrals
- **INCLUDE IMPLEMENTATION INSTRUCTIONS**: Every plan file MUST include the "Implementation Workflow" section so Claude knows how to use the plan in a clean context
- **USE EXACT TEMPLATE**: The plan output must follow the template structure exactly as shown above

Remember: The executive summary is for humans to understand what is changing. The implementation tasks are for Claude to execute with MAXIMUM PARALLELIZATION. Both should be concise and focused.

**IMPORTANT**: This document provides guidelines for creating implementation plans. DO NOT start creating a plan yet. Wait for the user's specific instructions about what implementation plan to create.