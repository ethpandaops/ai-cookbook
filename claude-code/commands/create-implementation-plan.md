# Create Implementation Plan

## Overview
This command helps you create a detailed, well-structured implementation plan for a feature, script, or system enhancement. It provides a standardized template with proper scaffolding to ensure comprehensive planning with clear sections, measurable outcomes, and actionable steps.

## Important Notes
- The plan should be detailed enough to serve as a complete reference for implementation
- Include specific code examples where relevant
- Structure should follow a logical progression from overview to specific implementation details
- Each section should be clearly labeled with appropriate heading levels for hierarchy
- Technical requirements and constraints should be explicitly stated
- Prioritize modularity, maintainability, and clear component boundaries

## Tasks

### TASK 1: Current State Assessment
Analyze and document the current state of the system or component being modified:

```markdown
## Current State Assessment

- Describe existing implementation (if any)
- Identify limitations, issues, or gaps in current approach
- Document relevant dependencies and integrations
- Note any technical debt or constraints
- Summarize what's working well and should be preserved
```

### TASK 2: Define Plan Purpose and Scope
Start by defining the core purpose of the implementation and establishing clear boundaries:

```markdown
# [Feature/System Name] Implementation Plan

## Overview
> A concise introduction that explains the purpose, context, and importance of the implementation. This should be an executive summary of the plan.

- What problem is being solved
- How it fits into the broader system/project

If you 
```


### TASK 3: Define Clear Goals
Establish specific, measurable goals for the implementation:

```markdown
## Goals

1. Primary goal: [One sentence describing main objective]
2. [Additional specific goals as bullet points]
   - [Measurable outcome]
   - [Performance target]
   - [User-facing improvement]
3. [Non-functional requirements]
   - [Scalability considerations]
   - [Security requirements]
   - [Maintainability targets]
```

### TASK 4: Design Approach and Architecture
Document the high-level design approach, architecture, and key components:

```markdown
## [System/Feature] Design Approach

### Architecture Overview
[Describe the architectural approach using clear, concise paragraphs]
- Component relationships and boundaries
- Data flow descriptions
- Key design patterns being utilized

### Component Breakdown
1. **[Component Name]**
   - Purpose: [One sentence describing component function]
   - Responsibilities: [Bullet points of specific responsibilities]
   - Interfaces: [How it interacts with other components]

2. **[Component Name]**
   - Purpose: [One sentence describing component function]
   - Responsibilities: [Bullet points of specific responsibilities]
   - Interfaces: [How it interacts with other components]
```

### TASK 5: Detailed Implementation Plan
Provide a detailed, step-by-step implementation plan organized by tasks. These tasks should be specific, actionable, and contain all relevent context to complete the task.

```markdown
## Implementation Approach

### 1. [n] [Implementation Area]

#### Specific Changes
- [Detailed description of changes needed]
- [Files affected]
- [New components/functions to create]

#### Sample Implementation
```[language]
// Code example demonstrating key implementation details
function exampleImplementation() {
  // Show critical algorithm, pattern or approach
}
```

### TASK 6: Define Testing Strategy
Outline the testing approach for validating the implementation:

```markdown
## Testing Strategy

### Unit Testing
- [Key components to test]
- [Critical test cases]
- [Mock requirements]

### Integration Testing
- [Integration test scenarios]
- [System boundaries to verify]

### Validation Criteria
- [Specific criteria that define success]
- [Performance benchmarks]
- [Edge cases to validate]
```

### TASK 7: Implementation Dependencies
Create a logical sequence for implementation with dependencies:

```markdown
## Implementation Dependencies

1. **Phase 1: [First Milestone]**
   - [Task 1]
   - [Task 2]
   - Dependencies: [List any external dependencies]

2. **Phase 2: [Second Milestone]**
   - [Task 1]
   - [Task 2]
   - Dependencies: [List any dependencies on Phase 1]
```

### TASK 8: Risks and Considerations
Identify potential risks and mitigation strategies:

```markdown
## Risks and Considerations

### Implementation Risks
- [Risk 1]: [Mitigation strategy]
- [Risk 2]: [Mitigation strategy]

### Performance Considerations
- [Performance concern]: [Addressing approach]

### Security Considerations
- [Security concern]: [Addressing approach]
```

### TASK 9: Expected Outcomes and Success Metrics
Define how success will be measured:

```markdown
## Expected Outcomes

- [Concrete, measurable outcome 1]
- [Concrete, measurable outcome 2]

### Success Metrics
- [Metric 1]: [Target value]
- [Metric 2]: [Target value]
```

## Example Structure
Use this structure as a template for your plan:

```markdown
# Feature X Implementation Plan

## Overview
> A concise introduction explaining what's being built and why.

## Current State Assessment
[Description of current implementation...]

## Goals
1. Primary goal: [Main objective]
2. [Additional goals...]

## Design Approach
[Architecture and design details...]

## Implementation Approach
### 1. [Component/Area 1]
[Detailed implementation steps...]

#### Code Examples
```javascript
// Sample code
```

### 2. [Component/Area 2]
[Detailed implementation steps...]

## Testing Strategy
[Testing approach and validation criteria...]

## Implementation Timeline
[Phased implementation plan...]

## Risks and Considerations
[Potential issues and mitigation strategies...]

## Expected Outcomes
[Success criteria and metrics...]
```

## Best Practices for Implementation Plans

1. **Be Specific**: Include concrete details instead of vague descriptions
2. **Show Code**: Use code examples to illustrate key concepts
3. **Define Boundaries**: Clearly state what is and isn't in scope
4. **Consider Dependencies**: Identify external dependencies and integration points
5. **Address Risks**: Acknowledge potential issues and include mitigation strategies
6. **Prioritize**: Identify must-have vs. nice-to-have elements
7. **Set Success Criteria**: Define measurable outcomes to evaluate success
8. **Progressive Disclosure**: Organize from high-level to detailed implementation
9. **Modular Design**: Ensure components have clear responsibilities and boundaries
10. **Maintainability**: Consider future maintenance and extensibility 