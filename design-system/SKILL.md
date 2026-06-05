---
name: gss-monitoring-design
description: Use this skill to generate well-branded interfaces and assets for the GSS Innovations Sports Monitoring platform, either for production (Tailwind 3 + Django) or throwaway prototypes/mocks. Contains design tokens, colors, typography, semantic status system, and ready-to-use component classes.
user-invocable: true
---

Read `README.md` within this skill first, then explore the other files.

Key files:
- `tokens.css` — source of truth for all design tokens (CSS variables).
- `tailwind.config.js` — all tokens mapped to a Tailwind 3 theme.
- `gss-components.css` — `.gss-*` component classes (`@layer components`).
- `styleguide.html` — living visual reference.
- `DJANGO.md` — step-by-step integration for Tailwind 3 + Django.

The brand is **minimalismo estruturado**: warm-neutral surfaces, IBM Plex Sans + Mono
typography (numbers always mono + tabular), and saturated color used ONLY for semantic
clinical status (wellness / hydration / recovery / alert) computed by the wellnessEngine.
Never use the semantic colors decoratively. Interface copy is in Brazilian Portuguese;
status enums stay in uppercase English to match the backend contract.

If creating visual artifacts (mocks, prototypes), copy assets out and produce static HTML
that links `tokens.css`. If working on production Django code, follow `DJANGO.md` to wire
the tokens into Tailwind and use the `.gss-*` classes in templates.

If invoked without guidance, ask what to build, ask a few questions, and act as an expert
designer for this brand — outputting HTML artifacts or production code depending on need.
