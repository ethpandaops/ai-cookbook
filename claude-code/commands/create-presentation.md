# Create Presentation

## Overview

This command creates succinct and effective presentation files in Marp format. It analyzes prompts, breaks them down into parallel subtasks where possible, and generates human-consumable presentations that offer precise and intelligent views of complex topics. The command automatically builds the presentation and offers to open it for viewing.

## Important Notes

- Presentations MUST be created in Marp (Markdown Presentation Ecosystem) format
- Content MUST be human-consumable with clear, concise messaging
- Complex prompts MUST be broken down into parallel subtasks to avoid context dilution
- Generated presentations automatically build to HTML using Marp CLI
- User receives a y/n prompt to open the generated presentation

## Command Structure

### STEP 1: Prompt Analysis and Breakdown

Upon receiving the user's prompt:

1. **Zoom out and analyze** the complete problem space
2. **Identify key themes** and presentation sections
3. **Break down into parallel subtasks** where possible to minimize context pollution
4. **Determine presentation flow** and logical structure

### STEP 2: Marp Presentation Creation

**MUST follow these directives:**

#### Presentation Format Requirements

- **MUST** use Marp YAML frontmatter with space-efficient theme and configuration
- **MUST** structure content with clear slide hierarchy
- **MUST** use concise, impactful messaging (max 5 bullets per slide)
- **MUST** include title slide with clear topic statement
- **MUST** provide logical flow with section dividers
- **MUST** ensure content fits within slide boundaries
- **MUST NOT** include excessive text or cramped slides
- **MUST NOT** use more than 2 levels of bullet nesting
- **MUST NOT** exceed 40 characters per bullet point when possible

#### Content Guidelines

- **MUST** present information in digestible chunks
- **MUST** use clear, professional language
- **MUST** highlight key insights and takeaways
- **MUST** include actionable items where relevant
- **MUST** provide visual hierarchy with headers and emphasis
- **MUST** optimize for readability and space efficiency
- **MUST NOT** overwhelm slides with information
- **MUST NOT** include implementation details unless specifically requested

#### Marp Template Structure

```markdown
---
marp: true
theme: gaia
class: lead
paginate: true
backgroundColor: #1a1a2e
color: #eee
style: |
  .lead h1 { font-size: 2.5rem; }
  .lead h2 { font-size: 1.8rem; }
  section { font-size: 1.4rem; padding: 70px; }
  ul { line-height: 1.6; }
  li { margin-bottom: 0.8rem; }
---

# [Title]
## [Subtitle]

**[Context]**

---

## Agenda

- **[Section 1]**
- **[Section 2]** 
- **[Section 3]**
- **[Takeaways]**

---

# [Section Title]

---

## [Slide Title]

- **Key Point**: Concise statement
- **Detail**: Supporting context
- **Action**: What's needed

---

# Key Insights

- **Primary**: Main conclusion
- **Next**: Action required
- **Success**: How to measure

---

# Questions?

**Thank you**
```

### STEP 3: Parallel Task Execution
When breaking down complex topics:

#### Task Identification

- **Identify independent research areas** that can be processed in parallel
- **Separate content creation tasks** by topic/section
- **Parallelize data gathering** and analysis where possible
- **Avoid sequential dependencies** unless absolutely necessary

#### Parallel Execution Strategy

```markdown
**Parallel Task Group A**: Content Research (Execute simultaneously)
- Task A.1: Research [Topic 1] - gather key insights and data
- Task A.2: Research [Topic 2] - analyze current state and challenges  
- Task A.3: Research [Topic 3] - identify solutions and recommendations

**Parallel Task Group B**: Content Synthesis (Execute after Group A)
- Task B.1: Synthesize findings into presentation outline
- Task B.2: Create slide content with key messaging
- Task B.3: Format for Marp and ensure visual clarity
```

### STEP 4: Build and Preview Process

After creating the presentation file:

1. **Build the presentation** using Marp CLI:

   ```bash
   npx @marp-team/marp-cli@latest [filename].md
   ```

2. **Offer to open** the generated HTML file:

   ```text
   Presentation built successfully! 
   Would you like to open the presentation now? (y/n)
   ```

3. **If user responds 'y'**: Execute `open [filename].html` to launch in browser
4. **If user responds 'n'**: Provide file location and completion message

## Content Strategy

### Slide Design Principles

- **One key message per slide** - avoid information overload
- **Use visual hierarchy** - headers, bullets, emphasis
- **5±2 rule** - maximum 5 bullets or concepts per slide for space efficiency
- **Clear transitions** - logical flow between sections
- **Strong opening and closing** - memorable start and actionable end
- **Character limits** - keep bullet points under 40 characters when possible

### Message Crafting

- **Lead with insights** - what's the key takeaway?
- **Support with evidence** - data, examples, context
- **End with action** - what should the audience do?
- **Use active voice** - direct, engaging language
- **Eliminate jargon** - accessible to intended audience
- **Optimize for space** - concise, impactful wording

## Example Usage Scenarios

### Complex Analysis Request

```text
User: "Analyze the current state of Ethereum's consensus mechanism and present recommendations for optimization"

Claude's Approach:
1. Break into parallel research tasks:
   - Current mechanism analysis
   - Performance bottleneck identification  
   - Optimization strategy research
2. Synthesize findings into presentation
3. Build and offer to open
```

### Multi-Topic Presentation

```text
User: "Create a presentation covering our Q4 roadmap, technical debt priorities, and resource allocation"

Claude's Approach:
1. Parallel task execution:
   - Q4 roadmap analysis and timeline
   - Technical debt assessment and prioritization
   - Resource allocation modeling and recommendations
2. Integrate into cohesive presentation narrative
3. Build and preview
```

## Quality Assurance

### Pre-Build Checklist

- [ ] Marp frontmatter properly configured with space-efficient theme
- [ ] Logical slide progression and flow
- [ ] Clear, concise messaging throughout (max 5 bullets per slide)
- [ ] Proper visual hierarchy and formatting
- [ ] Actionable takeaways included
- [ ] No information overload on individual slides
- [ ] Content fits within slide boundaries

### Post-Build Verification

- [ ] HTML file generated successfully
- [ ] All slides render properly in browser
- [ ] Navigation works correctly
- [ ] Content is readable and professional
- [ ] Text fits properly on all slides
- [ ] File ready for sharing or presentation

## Error Handling

- **Marp CLI failures**: Provide troubleshooting steps and alternative build methods
- **Content formatting issues**: Auto-correct common Marp syntax problems
- **File access problems**: Suggest alternative file locations or permissions fixes
- **Browser opening failures**: Provide manual file path and alternative opening methods

---

**CRITICAL DIRECTIVES FOR CLAUDE**:

- **MUST** analyze prompts holistically before starting presentation creation
- **MUST** use parallel subtasks for complex topics to prevent context dilution
- **MUST** follow Marp format requirements exactly with space-efficient theme
- **MUST** create human-consumable, actionable content that fits on slides
- **MUST** build presentation with Marp CLI after creation
- **MUST** offer y/n prompt to open the generated file
- **MUST NOT** create overly technical presentations unless specifically requested
- **MUST NOT** skip the parallel task breakdown for complex prompts
- **MUST NOT** proceed without building and offering to open the presentation
- **MUST NOT** exceed content limits that cause text overflow on slides