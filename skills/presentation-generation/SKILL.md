---
name: presentation-generation
description: Build stakeholder decks from arbitrary context using markdown-first artifacts (slides.md, design.md), a Marp theme CSS aligned to the team’s slim reference deck, optional reference icons/images for polish, and Marp CLI to PDF/PPTX (final Office pass optional). Use when creating or refreshing presentations without paid chart add-ins.
---

# Presentation Generation Skill

## Purpose

Produce presentation-ready **markdown and design specs** first, then compile with **[Marp](https://marp.app/)** to **PDF** (primary review artifact) and **PPTX** (editable handoff). Use a **Marp theme `.css`** derived from the same **slim reference** `.pptx` your org curates so colors and type match brand. Reuse **icons and images** extracted once from reference decks for **aesthetically strong** slides without pasting heavy template files into every agent run. Optionally reuse **diagram shells** from **`diagram-library.pptx`** during an **offline** PowerPoint step—not required for Marp output.

## When to Use

- Any slide deck where the user supplies context (notes, bullets, briefs, research, threads, transcripts, demos, SDLC artifacts, or mixed sources).
- You want **stable, formatted** slides from markdown (**Marp**), with **optional** final alignment to corporate masters **offline** in PowerPoint.
- You want **review** on text and structure in **PDF** (or HTML) before any heavy layout polish.

## When Not to Use

- One-off slides with no need for traceability or reuse (draft directly in PowerPoint if faster).
- Decks that **require** a proprietary add-in as the authoring model (outside this skill’s constraints).

## Principle — Markdown First, PPT Last

1. **Source of truth:** `slides.md` (Marp) and `design.md`. Approve them before treating exports as final.
2. **PDF / Marp PPTX** are **compile artifacts** from Marp. If copy changes, edit **`slides.md`** (and `design.md` if visuals change), then re-export.
3. **Diagram geometry** for complex native charts may still live in **`diagram-library.pptx`**; merge or duplicate those slides **offline** after Marp export when needed.

## Inputs

### Default (always collect)

| Input | Notes |
|-------|--------|
| **Context** | Any materials the story is built from (notes, bullets, briefs, research, threads, transcripts, metrics, screenshots, **SDLC docs** such as initiative / product brief / epic / feature—only when relevant). |
| **Audience** | Who will see the deck; if missing, ask before locking tone and depth. |
| **Duration** | Slot length or slide budget; if missing, ask before locking structure. |
| **Goal** | One primary outcome: inform, decide, align, train, or pitch. |

### Optional and non-default (supply when applicable)

Record paths, versions, and URLs in **`design.md`** so Phase C does not depend on unstated assets.

| Input | When | Role in the workflow |
|-------|------|------------------------|
| **Slim `reference_template.pptx`** | Org ships a curated handoff deck | **Not** used as a Pandoc `--reference-doc=`. Use it to (1) read **`ppt/theme/theme1.xml`** for **Marp theme CSS** tokens, and (2) optionally **`ppt/media/`** as the **source** to copy icons/images into a small **`media/`** or **`assets/`** folder for Marp (see **Reference visuals** below). |
| **`template-profile.md`** | Brand distilled once | **Agent-facing** text: palette, fonts, rules, paths to **`marp_theme.css`**, **`media/`** catalog, `diagram-library.pptx`, `template_version`. Routine runs: read profile + theme + asset list—**not** full 30–40 slide sample packs. |
| **`marp_theme.css`** | Required for on-brand Marp | Path in `design.md`; pass **`marp --theme path/to/theme.css`**. Example: [`presentations/reference/handoff/marp-theme-hitachi-reference.css`](../../../presentations/reference/handoff/marp-theme-hitachi-reference.css). |
| **`media/` or `assets/`** (PNGs, SVGs) | You want icons / photos / logos on slides | **Curated** files extracted once from reference `.pptx` (see **Reference visuals**). Referenced from `slides.md` with relative paths; catalog in `design.md`. |
| **House `design.md`** | Brand already documented | **Input:** extend with deck-only fields (title, `marp_theme`, media catalog). |
| **Existing `slides.md`** | Refresh a deck | **Input:** edit Phases A–B; re-run Phase C. |
| **`diagram-library.pptx`** | Native diagram shells | **Offline:** after Marp PPTX or alongside PDF deliverable, copy shells into the deck if required. |
| **Structured data** (`.csv`, …) | Numeric slides | **Input** for bullets; cite in notes or `design.md`. |
| **Prior deck `.pptx`** | Migrate content | **Input** for structure only—lift copy into `slides.md`, then compile with Marp. |

### Enterprise template and agent context (important)

Official enterprise packages are often **large** `.pptx` files (sample slides, embedded icons). They are **human / one-time prep** sources for **theme XML** and **exported media**, not files agents re-read every run.

**Default for agents on routine runs**

1. **`template-profile.md`** — rules, paths, `template_version`.
2. **`marp_theme.css`** — colors and typography aligned to the slim reference theme.
3. **`media/`** (or `assets/`) — **small** set of vetted PNG/SVG from reference decks (see **Reference visuals**).
4. **`design.md`** — points at (1)–(3) plus compile commands.

**Do not** load the full enterprise sample `.pptx` for routine generation when (1)–(3) exist.

### Curating the handoff from the enterprise deck (human, one-time)

Goal: **`marp_theme.css`**, **`template-profile.md`**, optional **`media/`**, optional slim **`reference_template.pptx`** (for theme + zip media source only), optional **`diagram-library.pptx`**.

1. **Theme tokens:** `unzip -p handoff/reference-template-*-slim.pptx ppt/theme/theme1.xml` → build/update **`marp_theme.css`** (`/* @theme … */`, `@import "default";`, override `section`, `h1`–`h3`, lists, `footer`).
2. **Slim reference `.pptx` (optional but recommended):** one slide per layout master for **human** reference; keep **small**. It is the **authority** for theme XML and a **convenient** zip root for `ppt/media/`.
3. **Smoke-test Marp:** `marp --no-stdin slides.md --theme handoff/marp-theme-….css --pdf -o smoke.pdf` from a tiny test deck.
4. **`template-profile.md`:** paths, `template_version`, media catalog, diagram library pointer.
5. **`diagram-library.pptx`:** same masters as brand if you use offline shell duplication.
6. **Version** when IT ships a new template; bump `template_version` in `template-profile.md` and `design.md`.

### Reference visuals — icons and images from reference decks (aesthetics)

Marp renders **markdown + CSS**; **pictures** come from **image files** referenced in `slides.md`. To make decks **visually strong** while keeping agent context small:

1. **Extract once** from the official or slim reference `.pptx`: unzip and copy needed files from **`ppt/media/`** (e.g. `image1.png`, `image2.svg`) into a deck-local folder such as **`media/`** next to `slides.md`, or a shared **`presentations/reference/handoff/media/`** with stable names (`logo-corporate.png`, `icon-section.png`). Rename for purpose, not opaque `image3.png`.
2. **Catalog in `design.md`:** table `filename` | `use` (title accent, section divider, bullet row icon, logo) | max width / placement hint.
3. **Use in `slides.md`:** standard markdown `![](media/logo-corporate.png)` or Marp layouts such as split slides `![bg right:40%](media/hero.png)` and [Marp’s built-in directives](https://marpit.marp.app/image-syntax) (`<!-- _backgroundColor: … -->`, `<!-- _class: lead -->`) **sparingly**—one focal visual per slide unless design spec says otherwise.
4. **Match the theme:** tune **`marp_theme.css`** so images sit on backgrounds with enough contrast; reuse **accent hex** values from the same theme XML as bullets or heading rules.
5. **Licensing:** only use assets your organization **allows** to extract and redistribute in git; when in doubt, use officially published brand PNGs from the brand portal instead of ripping arbitrary marketing slides.

## Output Contracts

| Artifact | Required | Role |
|----------|----------|------|
| `slides.md` | Yes | **Marp** deck: YAML **front matter** (`marp: true`, `paginate`, `size: 16:9`, …) then slides separated by `---`; markdown + **relative** `![](media/...)` where visuals apply. |
| `design.md` | Yes | `compiler: marp`, **`marp_theme:`** path, **`media/`** catalog (if any), diagram library pointer if used offline, compile commands. |
| `marp_theme.css` | Yes (per org handoff) | Brand-aligned `@theme`; see handoff example path in **Curating** above. |
| `template-profile.md` | As needed | Agent-readable bundle metadata. |
| `media/` | As needed | Curated PNG/SVG from reference decks. |
| `diagram-library.pptx` | Team asset | Optional; offline merge. |

### `slides.md` (Marp only)

- **First lines** must be a Marp directive block:

```yaml
---
marp: true
paginate: true
size: 16:9
---
```

- **Slides:** use `---` on its own line **between** slides (only after the initial YAML block).
- **Images:** `![](relative/path.png)` or Marp background / split syntax per [Marpit image docs](https://marpit.marp.app/image-syntax); paths must resolve from the `slides.md` directory (or use `--input-dir` with Marp CLI).
- **Diagram library tag (optional, offline):** `<!-- diagram: pattern-id -->` for human/script merge after export—not interpreted by Marp.

### `design.md` (minimum sections)

1. **Meta:** Deck title, author, date, **`compiler: marp`** (fixed for this skill).
2. **Brand handoff:** Paths to **`template-profile.md`**, **`marp_theme.css`**, optional slim **`reference_template.pptx`** (source-only), **`template_version`**.
3. **Aspect ratio:** e.g. `16:9` (match Marp front matter).
4. **Palette / typography:** or “see `template-profile.md` / theme CSS”.
5. **Media catalog:** list each file under **`media/`** with intended use and sizing notes.
6. **Diagram library:** path + catalog if used **offline**; else “none”.
7. **Compile:** exact **`marp --no-stdin`** commands (see Phase C).

### `diagram-library.pptx`

- Optional **native** shells; merge **after** Marp export when you need shapes/charts not drawn in markdown.
- Same brand masters as reference when possible.

## Required Workflow

### Phase A — Markdown first (iterate here)

1. Ingest context; confirm audience, duration, goal.
2. Draft story arc; add **media** references where visuals improve clarity (per **Reference visuals**).
3. Write **`slides.md`** with Marp front matter and slide breaks.
4. Write **`design.md`**: `marp_theme`, media catalog, compile commands.
5. Tune **`marp_theme.css`** if new slide types or image layouts need CSS.

### Phase B — Review loop

1. Review **`slides.md`** (copy, density, images).
2. Review **`design.md`** (paths, catalog).
3. Prefer **`marp … --pdf`** output for stakeholder review before locking PPTX.

### Phase C — Export (Marp only)

1. Install **[Marp CLI](https://github.com/marp-team/marp-cli)** (OSS).

2. **Compile** (always pass **`--no-stdin`** in CI or headless environments):

   ```bash
   marp --no-stdin slides.md --theme path/to/marp-theme.css --pdf -o deck.pdf
   marp --no-stdin slides.md --theme path/to/marp-theme.css --pptx -o deck.pptx
   ```

3. **Optional offline:** open `deck.pptx` in PowerPoint to **apply** corporate template or paste **diagram-library** slides; keep narrative edits in **`slides.md`** and re-export.

## Compile stack (OSS only)

| Tool | License | Role |
|------|---------|------|
| Marp (Marpit) | OSS stack | **Primary:** `md` → `pdf` / `pptx` / `html` with `--theme`. |
| python-pptx | MIT | Optional automation (slide copy, tweaks) after export. |

**Excluded:** Paid chart add-ins; paid-only converters.

## Rules

- **No invented facts:** claims trace to supplied context or are labeled illustrative.
- **One primary idea per slide** where possible; **one focal image** per slide unless `design.md` specifies otherwise.
- **Marp only** for compile in this skill: **`compiler: marp`** in `design.md`; do not mix Pandoc slide conventions in the same `slides.md`.
- **Lightweight handoff:** use **`template-profile.md` + `marp_theme.css` + `media/`**—not full enterprise sample decks on every agent run.
- **Library / diagrams:** prefer **`diagram-library.pptx`** offline for complex native charts; use **markdown + images** for everything Marp can render well on its own.

## Verification

- [ ] `design.md` declares **`compiler: marp`**, **`marp_theme`** path, aspect ratio, and **media catalog** (or states no media).
- [ ] `slides.md` starts with Marp YAML and uses **`---`** only between slides after that block.
- [ ] All `![](…)` paths resolve; assets are listed in `design.md` and exist on disk.
- [ ] `marp --no-stdin … --pdf` succeeds; **`--pptx`** succeeds for handoff.
- [ ] Phase B complete before treating exports as final.
- [ ] No paid add-ins required.
