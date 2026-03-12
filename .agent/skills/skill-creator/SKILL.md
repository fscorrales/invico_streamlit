---
name: "Skill Creator"
description: "Creates new Antigravity workspace skills. Analyzes user requests to generate the correct folder structure, descriptive SKILL.md files with proper YAML frontmatter, and any necessary auxiliary scripts or resources."
---

# Skill Creator Instructions

When the user requests the creation of a new skill, follow this procedure:

1.  **Analyze the Request**: Determine the clear goal and scope of the requested skill.
2.  **Define Location**: Use the directory `.agent/skills/<skill-name>/` in the workspace root.
3.  **Create the Frontmatter**: Draft the YAML frontmatter for the `SKILL.md` file containing:
    *   `name`: A clear, readable title for the skill.
    *   `description`: A highly detailed, **3rd-person description** of what the skill does (e.g., "Generates unit tests for Python files..."). This is crucial for the agent's semantic discovery of the skill.
4.  **Write the Instructions**: Following the frontmatter, write the detailed step-by-step Markdown instructions for the agent to follow when executing the skill.
    *   Use checklists, decision trees, or "If/Then" logic.
    *   Delegate complex algorithms or operations to executable scripts rather than explaining them in Markdown.
5.  **Create Files**: Use the `write_to_file` tool to generate the `SKILL.md` file.
6.  **Create Auxiliary Folders (If needed)**: Create `scripts/`, `examples/`, or `resources/` within the skill directory if the skill requires helper scripts, reference inputs/outputs, or static templates.

**Skill Verification Checklist**:
- [ ] Is the `description` in the YAML frontmatter written in the 3rd person?
- [ ] Is the skill focused on a single responsibility?
- [ ] Are any complex logic setups offloaded to the `scripts/` directory?
