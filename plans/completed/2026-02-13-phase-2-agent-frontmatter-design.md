# Phase 2 Design: Agent Frontmatter Updates

**Status**: Ready to Implement
**Locked Decisions**:
- ✓ Option A: Enable agents to self-load context (autonomous, token-efficient)
- ✓ Explicit configuration (no pattern matching, no guessing)
- ✓ Each agent declares features it owns in frontmatter

---

## Overview

Transform agents from context-agnostic to context-aware. Each agent will declare in its frontmatter which features it specializes in, and the system will automatically load only the relevant docs, constraints, and state.

### Purpose
Reduce token waste, improve context clarity, enable agent autonomy without guesswork.

### Scope
- Update 8 agent frontmatter files with explicit feature mappings
- Create 12 lightweight PRDs (200-400 words each)
- No changes to agent code or behavior
- Agents remain autonomous but focused

### Success Criteria
- [x] Each agent has explicit feature mapping in frontmatter
- [x] All 13 features have PRDs (1 exists, need 12 more)
- [x] Frontmatter is consistent across all agents
- [x] System knows exactly what each agent can load

---

## Data Model

### Agent Frontmatter Structure

```yaml
---
name: pdf-agent
description: PDF extraction, generation, and template handling
specialization:
  primary_features: [pdf]
  supporting_features: []
  shared_rules: [architecture, data-validation-rules, pdf/pdf-generation]
  state_files: [feature-pdf.json, PROJECT-STATE.json]
  prd: prds/pdf-extraction-v2-prd-2.0.md
---
```

### Frontmatter Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Agent identifier |
| description | string | Yes | What agent does |
| specialization.primary_features | array | Yes | Features agent owns (1-2 typically) |
| specialization.supporting_features | array | No | Features agent touches but doesn't own (0+) |
| specialization.shared_rules | array | Yes | Shared architecture + feature-specific rules |
| specialization.state_files | array | Yes | State files to load (always include PROJECT-STATE.json) |
| specialization.prd | string | No | Path to PRD if exists |

---

## Phase 2A: Explore Agent Capabilities

**Goal**: Map each agent to features based on its actual specialization.

### Step 1: Read Each Agent Definition

For each of the 8 agents, read `.claude/agents/{name}.md` and document:
- What problem does this agent solve?
- Which features does it naturally touch?
- What tools/skills does it use?
- Any constraints or specializations?

**Agents to analyze**:
1. planning-agent
2. frontend-flutter-specialist-agent
3. backend-data-layer-agent
4. backend-supabase-agent
5. auth-agent
6. pdf-agent
7. code-review-agent
8. qa-testing-agent

### Step 2: Create Feature-to-Agent Mapping

Document which agent(s) can own each feature:

**Example**:
```
Feature: PDF
  Primary: pdf-agent
  Supporting: backend-data-layer-agent (models), backend-supabase-agent (sync)

Feature: Sync
  Primary: backend-supabase-agent
  Supporting: backend-data-layer-agent (repos)

...
```

**Note**: Some agents will own multiple features (e.g., backend-supabase-agent → sync, auth, others). Some features may not have a clear owner (document as "generic").

### Output
Create file: `.claude/state/AGENT-FEATURE-MAPPING.json`

---

## Phase 2B: Update Agent Frontmatter

**Goal**: Add context-loading declarations to each agent.

### For Each Agent:

1. Read current agent definition
2. Determine primary + supporting features (from Phase 2A mapping)
3. List shared rules (always include `architecture.md` + feature-specific rules)
4. List state files (always include `PROJECT-STATE.json` + feature state files)
5. Add frontmatter block at top of agent file

### Example: pdf-agent

```yaml
---
name: pdf-agent
description: PDF extraction, table detection, OCR, template generation
specialization:
  primary_features: [pdf]
  supporting_features: []
  shared_rules:
    - architecture.md
    - data-validation-rules.md
    - pdf/pdf-generation.md
    - pdf/pdf-v2-constraints.md
  state_files:
    - feature-pdf.json
    - PROJECT-STATE.json
  prd: prds/pdf-extraction-v2-prd-2.0.md
---
```

### Effort
~30 minutes per agent × 8 = 4 hours total

---

## Phase 2C: Create 12 Lightweight PRDs

**Goal**: Quick-reference product requirements for non-critical features.

### Features Needing PRDs
PDF has one, need 12 more:
- auth, contractors, dashboard, entries, locations, photos, projects, quantities, settings, sync, toolbox, weather

### PRD Template (200-400 words)

```markdown
# {Feature} PRD

## Purpose
[1-2 sentences: What problem does this solve?]

## Core Capabilities
- [Capability 1]
- [Capability 2]
- [Capability 3]

## Data Model
- Primary entity: [Name] (SQLite table)
- Key fields: [field1, field2, field3]
- Sync: [Cloud First / Sync to Cloud / Local Only]

## User Flow
[1-2 sentences describing how users interact with this feature]

## Offline Behavior
[Read/write capabilities offline, sync strategy]

## Dependencies
- Features: [dependencies]
- Packages: [external packages]

## Owner Agent
[Agent responsible]
```

### Effort
~30 minutes per PRD × 12 = 6 hours total

---

## Implementation Phases (PR-sized chunks)

### Phase 2.1: Exploration + Mapping
- **Time**: 2 hours
- **Output**: AGENT-FEATURE-MAPPING.json
- **Deliverable**: Clear understanding of agent capabilities

### Phase 2.2: Update Frontmatter (Agents 1-4)
- **Time**: 2 hours
- **Agents**: planning-agent, frontend-flutter-specialist-agent, backend-data-layer-agent, backend-supabase-agent
- **Deliverable**: 4 agent files with frontmatter

### Phase 2.3: Update Frontmatter (Agents 5-8)
- **Time**: 2 hours
- **Agents**: auth-agent, pdf-agent, code-review-agent, qa-testing-agent
- **Deliverable**: 4 agent files with frontmatter

### Phase 2.4: Create PRDs (Part 1)
- **Time**: 3 hours
- **PRDs**: auth, contractors, dashboard, entries, locations, photos
- **Deliverable**: 6 new PRDs in .claude/prds/

### Phase 2.5: Create PRDs (Part 2)
- **Time**: 3 hours
- **PRDs**: projects, quantities, settings, sync, toolbox, weather
- **Deliverable**: 6 new PRDs in .claude/prds/

**Total Phase 2 Effort**: ~12 hours across 5 phases

---

## Edge Cases

### What if an agent doesn't fit cleanly into one feature?
→ List primary_features (1-2) and supporting_features (0+)

### What if a feature has no natural owner?
→ Document as "generic" or "cross-cutting" in AGENT-FEATURE-MAPPING.json

### What if frontmatter conflicts with agent's actual use?
→ Phase 3 (Workflow Integration) will validate; adjust mapping if needed

---

## Validation Before Proceeding

**Does this approach match your expectations?** Any changes before we move to implementation?

