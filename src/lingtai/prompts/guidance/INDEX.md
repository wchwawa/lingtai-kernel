---
kind: meta-guidance-index
audience: developers, coding-agents
schema_version: 1
guidance_version: 0.7.0
priority: high
render_mode: latest_tool_result_only
summary: >
  Index for the resident `meta_guidance` runtime-guidance catalog. Carries the
  top-level guidance payload fields (schema_version, guidance_version, priority,
  render_mode) that used to live at the root of guidance.json. Each sibling
  `<id>.md` is one ordered guidance section; the kernel assembles them (plus the
  generated `_meta` readme and the active adapter's static rules) into the final
  `meta_guidance` system-prompt section.
why: >
  guidance.json became a skill-style Markdown catalog so every guidance rule is
  a self-explaining frontmatter+Markdown file, like the prompt sections and
  skills. This frontmatter is developer-facing metadata; it never renders into
  the LLM prompt. The derived `system/guidance.json` is still emitted for TUI/Portal consumers.
---
