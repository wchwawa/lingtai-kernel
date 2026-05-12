# Knowledge v2: file-backed paper objects

**Status:** draft v1 (design only)
**Date:** 2026-05-12
**Builds on:** PR #95 (`docs-library-contract`) which makes `knowledge` the canonical private durable-memory capability and removes the old `library` / `codex` aliases.

## Problem

PR #95 cleans up the naming and contract around private durable memory:

- `knowledge` is the only private durable-memory capability/tool name.
- `skills` is the portable procedure catalog.
- The current prompt catalog is a progressive-disclosure index: `id + title + summary` are prompt-visible; full `content` and `supplementary` are loaded on demand.

That is a useful conservative guardrail, but it is not yet a new knowledge architecture. The current implementation remains a single JSON file:

```text
<agent>/knowledge/knowledge.json
```

with entry fields roughly shaped as:

```text
title + summary + content + supplementary
```

This works for small curated facts, but it has several limits:

1. **The storage unit is not a document.** A knowledge entry is one object inside a JSON array, not an independently inspectable, editable, versionable artifact.
2. **Progressive disclosure is too coarse.** The ladder is only catalog -> content -> supplementary. There is no separate abstract, claims list, reference list, or evidence expansion layer.
3. **Revision history is weak.** JSON rewrites do not naturally express per-entry revision, consolidation, supersession, or audit history.
4. **References are unstructured.** Entries can mention files, skills, PRs, emails, URLs, and logs, but there is no first-class reference model.
5. **Agent and human affordances diverge.** Humans understand paper-like structure immediately; agents benefit from fielded metadata and predictable disclosure levels. The current shape serves neither as well as it could.

## Goals

1. Define a **knowledge v2 target model** without changing runtime behavior in this design PR.
2. Treat each knowledge entry as an **agent-native paper object**: a durable document with metadata, abstract, plain-language summary, claims, main text, references, and supplementary material.
3. Move the long-term direction from one JSON array to **file-per-entry Markdown with YAML frontmatter**.
4. Use **git as substrate** for audit, revision, recovery, and migration history, while keeping the agent-facing tool API simple.
5. Make progressive disclosure explicit and multi-level: prompt catalog -> abstract/metadata -> main text -> selected references/evidence -> supplementary/attachments.
6. Preserve the `knowledge` / `skills` boundary: knowledge may reference public skills; skills must not depend on private knowledge.
7. Split implementation into small PRs so the conservative rename can land independently.

## Non-goals

- Implementing the file backend in this PR.
- Migrating existing `knowledge/knowledge.json` stores in this PR.
- Changing the `knowledge(...)` tool schema in this PR.
- Making knowledge shared across agents. Knowledge remains private, agent-owned memory.
- Turning agents into git operators. Git is an implementation substrate, not the primary interface.
- Secure erasure. Ordinary delete/archive in a git-backed store does not erase history; true purge would be a separate human-confirmed design.

## Design summary

Target architecture:

```text
knowledge/
  manifest.yaml
  .git/                         # local repo when file backend is active
  .gitignore
  .knowledge.lock               # ignored lock file

  entries/
    <id>.md                     # active knowledge entries

  archive/
    consolidated/
      <id>.md                   # no longer prompt-visible
    deleted/
      <id>.md                   # ordinary delete means archive, not purge

  attachments/
    <id>/
      raw-log.json
      diagram.png

  .cache/
    index.json                  # generated, ignored, never source of truth
```

Each active entry is a Markdown file with YAML frontmatter. The frontmatter is the prompt-catalog and routing layer; the Markdown body is the deep content layer.

The agent still calls a simple tool surface. The implementation maps those actions to files and commits:

```text
submit       -> create entries/<id>.md and commit
view         -> parse selected entries and disclose requested depth
consolidate  -> create new entry; move old entries to archive/consolidated; commit
delete       -> move entries to archive/deleted; commit
revise       -> future: edit one entry preserving id; commit
search       -> future: snippet search across hidden content without full disclosure
```

## Why paper-like, but agent-native

Human academic papers are not perfect for agents, but several decades of publishing practice solved a real progressive-disclosure problem:

| Paper affordance | Agent-native interpretation |
|---|---|
| Title | Fast routing handle. Should be short and stable enough for prompt catalog. |
| Abstract | Agent-facing compressed statement of the entry's main claim and scope. |
| Plain-language summary | Cross-agent / low-cost-model / human-friendly explanation. Useful when the reader is not the original author. |
| Main text | Full explanation, decision, reasoning, background, and caveats. |
| Claims | Structured assertions that can be scanned, linked, or reviewed independently. |
| References | Typed pointers to evidence: skills, files, PRs, issues, emails, URLs, commits, reports. |
| Supplementary material | Raw logs, long transcripts, big diffs, datasets, and appendices. Explicit opt-in only. |

The agent-native version differs from a static paper:

- It is **living**: entries can be revised and superseded.
- It is **private by default**: references may point to local files and internal mail IDs; those must not leak into shared skills.
- It is **tool-addressable**: the agent can ask for metadata, claims, references, main text, or supplementary material by depth.
- It is **history-aware**: git tracks how an entry changed and why.

## Entry schema

Example target file:

```markdown
---
schema_version: 1
id: b01c7008
title: Knowledge entries should be file-backed paper objects
abstract: >-
  Private durable knowledge should be stored as one Markdown file per entry with
  YAML frontmatter, allowing prompt-visible metadata, staged disclosure, and
  per-entry revision history through git.
plain_language_summary: >-
  Instead of hiding every memory in one JSON file, each important thing an agent
  learns should become a small paper-like document. The prompt sees only the
  short description; deeper sections are loaded only when needed.
claims:
  - id: c1
    text: File-per-entry storage makes individual knowledge entries inspectable and versionable.
  - id: c2
    text: Prompt catalogs should include only routing metadata, not full prose or raw evidence.
  - id: c3
    text: Git should provide history underneath the tool API, not become the agent-facing interface.
tags:
  - knowledge
  - progressive-disclosure
  - storage
status: active
created_at: "2026-05-12T08:00:00Z"
updated_at: "2026-05-12T08:00:00Z"
consolidated_from: []
superseded_by: null
references:
  - type: skill
    label: skills-manual
    path: .library/intrinsic/capabilities/skills/SKILL.md
    visibility: public
  - type: pr
    label: PR #95
    url: https://github.com/Lingtai-AI/lingtai-kernel/pull/95
    visibility: public
  - type: file
    label: current implementation
    path: src/lingtai/core/knowledge/__init__.py
    visibility: repo
attachments: []
---

## Main Text

The full explanation lives here. This is more detailed than the abstract and can
include tradeoffs, failure modes, design history, and concrete examples.

## Evidence

Evidence expands references into selected quotations, commit hashes, test
results, or short excerpts. It should stay curated rather than becoming a raw log
dump.

## Supplementary Material

Long raw material lives here only when it is still worth keeping near the entry.
Very large or binary material should be placed under `attachments/<id>/` and
referenced from frontmatter.
```

### Required frontmatter

- `schema_version`
- `id`
- `title`
- `abstract`
- `plain_language_summary`
- `status`
- `created_at`
- `updated_at`

### Recommended frontmatter

- `claims`
- `tags`
- `references`
- `consolidated_from`
- `superseded_by`
- `attachments`

### Body sections

- `## Main Text` is the default deep explanation.
- `## Evidence` is curated backing material and citation expansion.
- `## Supplementary Material` is the deepest normal layer and should never be prompt-visible by default.

Tool-written files should render stable headings. A parser may tolerate manually edited files with missing headings, but should warn and avoid silently discarding content.

## Progressive disclosure ladder

Knowledge v2 should expose entries in layers.

### Level 0: prompt catalog

Always-on prompt section. Derived only from frontmatter, never from body.

Suggested default line shape:

```text
- [b01c7008] Knowledge entries should be file-backed paper objects — abstract: Private durable knowledge should be stored as one Markdown file per entry...
```

Possible fields:

- `id`
- `title`
- short `abstract` or `plain_language_summary`
- maybe `tags` if budget allows

Must not include:

- full main text
- evidence body
- supplementary material
- attachment contents

### Level 1: metadata / abstract view

A lightweight `view` mode returns:

- frontmatter
- abstract
- plain-language summary
- claims
- typed reference list

This lets an agent decide whether the entry matters before paying for the main text.

### Level 2: main-text view

Returns `## Main Text` for selected entries. This is the natural replacement for today's `content`.

### Level 3: evidence / reference expansion

Returns curated `## Evidence` plus typed reference metadata. Future versions may support selecting specific references by label/id so the agent can expand one citation without loading every backing note.

### Level 4: supplementary / attachments

Returns `## Supplementary Material` and/or attachment metadata only with explicit opt-in. Large attachments should require separate file reads; the knowledge tool should avoid dumping large binary/raw material into the model context.

## Agent-facing API direction

The initial implementation can preserve the existing four actions and add fields gradually.

### `submit`

Near-term compatibility:

- Accept current `title`, `summary`, `content`, `supplementary`.
- Map `summary` to `abstract` if no explicit `abstract` is provided.
- Map `content` to `## Main Text`.
- Map `supplementary` to `## Supplementary Material`.

Future additive fields:

- `abstract`
- `plain_language_summary`
- `claims`
- `tags`
- `references`
- `attachments`

### `view`

Near-term compatibility:

- Default can continue returning a `content` field for existing callers.
- Internally, `content` is `## Main Text`.
- `include_supplementary=true` continues to disclose supplementary material.

Future additive option:

```text
depth = metadata | main | evidence | supplementary | all
```

Suggested compatibility rule:

- `include_supplementary=true` is equivalent to `depth=supplementary` or `depth=all` depending on exact response shape.
- Omitted depth behaves like today's `view`: main text without supplementary.

### `consolidate`

Current behavior removes old entries from the active list. File-backed behavior should preserve lineage:

1. Create a new active entry with `consolidated_from: [old_ids...]`.
2. Move old entries to `archive/consolidated/`.
3. Set old entries' `status: consolidated` and `superseded_by: <new_id>`.
4. Commit all moves and edits together.

The prompt catalog includes only active entries by default.

### `delete`

Ordinary delete should mean archive, not secure erasure:

1. Move active entry to `archive/deleted/`.
2. Set `status: deleted`.
3. Remove it from prompt catalog.
4. Commit.

True erasure would require a separate explicit `purge` design, because git history retains content.

### Future `revise`

File-backed entries make revision natural:

- Preserve `id` and `created_at`.
- Update selected fields/body sections.
- Set `updated_at`.
- Commit the diff.

This may be more important than search, because long-lived pads and other entries can safely reference stable IDs while content evolves.

### Future `search`

Search should preserve progressive disclosure:

- Search title, abstract, claims, main text, and optionally evidence/supplementary.
- Return snippets and matched fields, not full content.
- Require `view` for deliberate expansion.

## Git semantics

Use one git repository per agent knowledge store. Do not use branch-per-entry as the storage primitive.

### Why one repo + file history

- Per-entry history is available through path history:

  ```bash
  git -C knowledge log --follow -- entries/<id>.md
  git -C knowledge diff <old>..<new> -- entries/<id>.md
  ```

- Consolidation can be one commit touching several files.
- Archive moves are visible through `git mv` and `--follow`.
- The catalog is simply the set of active files on the main branch.

### Why not branch/worktree per entry

A branch is whole-repo state, not a document record. Branch-per-entry creates avoidable problems:

- Catalog discovery becomes a cross-ref query.
- Search and view require many refs or checkouts.
- Consolidation becomes branch choreography rather than a document operation.
- Stale branches become memory-discovery failures.
- Worktree cleanup becomes operational debt.

Branches and worktrees remain useful for migrations, repairs, experiments, and future shared-knowledge proposal flows, but not as the ordinary entry storage unit.

## Transaction model

Mutation flow for the file backend:

1. Acquire `knowledge/.knowledge.lock`.
2. Ensure repo exists (`git init`, `manifest.yaml`, `.gitignore`).
3. Re-read entries from disk inside the lock.
4. Validate no unexpected dirty tree, or fail with a clear repair instruction.
5. Validate operation inputs and resulting entry schema.
6. Write files via temp file + atomic replace; use `git mv` / filesystem rename for archive moves.
7. Rebuild the prompt catalog from active frontmatter.
8. Stage exact touched paths.
9. Commit with local agent identity in environment variables, not global git config.
10. On success, update prompt and return.
11. On failure, attempt rollback; if rollback fails, mark the knowledge store dirty/broken and block future mutations until repair.

First implementation should block mutation on a dirty tree. Later versions can add explicit `repair` / `adopt_external_edits` flows.

## Cache policy

`knowledge/.cache/index.json` is optional and generated.

Rules:

- Source of truth is `entries/*.md` plus archive files and git history.
- Missing cache -> rebuild.
- Corrupt cache -> ignore and rebuild.
- Stale cache -> rebuild.
- Cache corruption must not hide entries.

For 50-100 entries, scanning frontmatter directly is likely cheap enough; cache can wait until profiling shows need.

## Corruption and failure behavior

| Failure mode | Behavior |
|---|---|
| One active entry has invalid frontmatter | Prompt warning listing path/id if known; block mutating actions until repair. |
| One body section is malformed | Warn; allow viewing raw body if safe; block mutation until repair if parse ambiguity risks data loss. |
| `.git/` is broken but files are readable | Read and prompt from files with warning; block mutations until repair/reinit. |
| `git` executable missing | Read-only file parsing may work; mutations fail clearly; JSON backend remains fallback while supported. |
| Dirty tree before mutation | Block with repair/adopt instructions. |
| Duplicate IDs | Hard error; do not silently rename. |
| Filename/frontmatter ID mismatch | Hard error or explicit repair path; do not silently choose one. |
| Large supplementary section | Never prompt-visible; warn on size; recommend attachment. |
| Binary material | Store under `attachments/<id>/`, never inline into prompt. |
| Ordinary delete | Archive only; not secure erasure. |
| True purge request | Separate human-confirmed history rewrite design. |

## Migration strategy

Migration from JSON to file backend should be explicit and safe.

1. Detect existing `knowledge/knowledge.json`.
2. Strict-parse JSON. Malformed JSON blocks migration and asks for repair.
3. Validate/backfill entries using the current compatibility rules.
4. Create `entries/<id>.md` for each entry.
5. Preserve `id` and `created_at` where possible.
6. Set `updated_at = created_at` unless a better timestamp exists.
7. Set `status: active` and `source: migrated_from_json` if source metadata is desired.
8. Initialize git and write manifest/gitignore.
9. Commit once: `knowledge: migrate json store to markdown entries`.
10. Preserve the original JSON as a backup.
11. Rebuild prompt catalog from Markdown.
12. Compare migrated count/IDs against JSON before declaring success.

Avoid long-term dual-write. During transition, support two backends behind configuration:

- `json`
- `files`
- `auto` (prefer files if manifest/entries exists, else JSON)

## Relationship to pad, skills, and shared knowledge

| Layer | Role in this design |
|---|---|
| Pad | Active working index. Points at knowledge IDs, files, PRs, and next steps. Does not inline full knowledge. |
| Knowledge | Private durable memory. Stores what one agent learned, decided, and experienced. May reference public skills. |
| Skills | Portable procedures. Must not reference private knowledge IDs, private agent paths, or private mail IDs. |
| Shared library / recipes | Public or network-shared methodology. Knowledge can be distilled into skills/recipes, but not automatically leaked. |

Directionality remains:

```text
private knowledge -> public skill reference is allowed
public skill -> private knowledge dependency is forbidden
```

## Privacy and portability

Knowledge references need visibility metadata because entries are private but may point to public or private things.

Suggested reference field:

```yaml
references:
  - type: file | skill | pr | issue | url | email | commit | report
    label: human-readable label
    path: optional local path
    url: optional URL
    id: optional private/local id
    visibility: public | repo | agent-private | human-private
```

Rules:

- Prompt catalog should not expose agent-private reference IDs by default.
- Shared skills must not include private references copied from knowledge.
- Export/publish flows need a scrub step if knowledge entries are ever shared.

## Implementation slices

### PR 1: design only

- Add this design doc.
- Optionally link to it from `src/lingtai/core/knowledge/CONTRACT.md` as future direction.
- No runtime behavior change.

### PR 2: internal model and parser/renderer

- Add `KnowledgeEntry` internal model.
- Add Markdown + YAML frontmatter parser/renderer.
- Add fixtures and tests.
- Keep JSON backend default.
- No migration.

### PR 3: read-only file backend

- Add backend abstraction.
- Allow reading prompt catalog and `view` from file entries behind opt-in config.
- JSON remains default.
- Tests for malformed frontmatter, duplicate IDs, and prompt catalog exclusion.

### PR 4: mutating file backend

- Implement submit/view/consolidate/delete for file backend.
- Add lock and git transaction wrapper.
- Add archive-on-delete and consolidate lineage.
- Keep opt-in.

### PR 5: migration

- Add explicit JSON -> files migration command/action.
- Preserve IDs and timestamps.
- Backup JSON.
- Test malformed JSON refusal and count/ID preservation.

### PR 6: v2 affordances

- Add `revise`.
- Add snippet `search`.
- Add staged `view(depth=...)` if not already introduced.
- Add reference expansion helpers.

### PR 7: default switch and UI support

- Teach TUI/portal knowledge browsers to read both backends.
- Make file backend default for new agents after soak.
- Keep JSON fallback for existing agents until migration is mature.

## Open questions

1. Should the prompt catalog use `abstract`, `plain_language_summary`, or both?
2. Should `claims` be required, or optional until agents learn to write them well?
3. Should references be free-form at first, or validated against a strict enum?
4. Should `view(depth=metadata)` become the default for v2, or should compatibility keep returning main text by default?
5. How should very large supplementary material be summarized before the agent decides to open it?
6. What is the repair UX for manually edited broken entries?
7. Should `revise` land before file-backend mutation, or immediately after?
8. How much of git history should be exposed through the tool API, if any?

## Recommendation

Keep PR #95 focused on the canonical rename and conservative guardrails. Then pursue knowledge v2 as a separate sequence starting with this design.

The target is:

```text
knowledge = private, agent-owned, paper-like memory objects;
            one Markdown file per entry;
            YAML frontmatter for routing metadata;
            Markdown body for main text/evidence/supplementary;
            git for history underneath;
            staged disclosure by default;
            explicit references;
            no dependency from shared skills back into private knowledge.
```

This gives agents a durable memory system that is both human-legible and agent-native: shallow enough to route in prompt, deep enough to recall on demand, structured enough to cite, and versioned enough to trust.
