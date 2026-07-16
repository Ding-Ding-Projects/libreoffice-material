# Verified screenshot index

**Current verified screenshot count: 0.**

No application screenshot has been committed for LibreOffice Material yet.
This page reserves reviewable evidence categories without linking to missing
files or showing mock imagery. A gallery card that says “awaiting capture” is a
status indicator, not a screenshot.

A 2026-07-16 off-screen Notepad capture was used only to preflight the local
low-level desktop driver. It was temporary, was not committed, and cannot enter
this registry because it does not show LibreOffice. The verified LibreOffice
Material screenshot count therefore remains zero.

## Evidence slots

| Slot | Surface | Minimum checkpoint | Current state | Verified file |
| --- | --- | --- | --- | --- |
| E-START-001 | Start center and shared shell | stable launch, light and dark | Awaiting genuine capture | — |
| E-WRITER-001 | Writer | document open, formatting and sidebar visible | Awaiting genuine capture | — |
| E-CALC-001 | Calc | populated sheet, formula bar and sheet tabs visible | Awaiting genuine capture | — |
| E-IMPRESS-001 | Impress | editing canvas, slide pane and properties visible | Awaiting genuine capture | — |
| E-DIALOG-001 | Shared dialog | keyboard focus, validation, and long labels | Awaiting genuine capture | — |
| E-A11Y-001 | Accessibility modes | high contrast, 200% scale, visible focus | Awaiting genuine capture | — |

## Adding a verified image

1. Complete a run using [`HEADLESS_UI_EVIDENCE.md`](HEADLESS_UI_EVIDENCE.md).
2. Confirm the image, manifest, hashes, scenario result, and sensitive-data
   review all pass.
3. Commit the real image inside its evidence run directory.
4. Replace the dash in **Verified file** with a relative link to that existing
   file and add its run identifier.
5. Update the public site, roadmap, and repository memory in the same change.

Never pre-populate the index with a future path: a link appearing here is a
claim that the referenced artifact exists and has passed review.
