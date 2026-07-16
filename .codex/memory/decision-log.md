# Decision log

## D-001 — preserve the native LibreOffice stack

- Date: 2026-07-16
- State: accepted direction
- Decision: implement product UI in the languages and resource formats of the
  affected LibreOffice modules, primarily C++, VCL/UNO, and XML UI resources.
- Reason: the project objective is a native whole-suite rewrite, not a separate
  web application. The HTML/CSS site is documentation only.

## D-002 — shared primitives before application variants

- Date: 2026-07-16
- State: accepted direction
- Decision: establish semantic tokens and VCL components before migrating
  Writer, Calc, Impress/Draw, Base, Math, and remaining surfaces.
- Reason: suite consistency and accessibility cannot be maintained through
  duplicated application-local styling.

## D-003 — evidence slots remain empty until verified

- Date: 2026-07-16
- State: active policy
- Decision: the public gallery shows labeled empty slots and a count of zero
  until real build captures exist and pass the evidence contract.
- Reason: mock or generated images would overstate implementation progress.

## D-004 — use off-screen desktop automation for UI proof

- Date: 2026-07-16
- State: harness preflight verified; LibreOffice execution pending
- Decision: use `lowlevel-computer-use-mcp` to launch and interact with real GUI
  processes on Windows off-screen desktops or Linux Xvfb displays.
- Reason: repeatable captures should not take over the operator's desktop, and
  window identity plus run metadata must remain attributable.
- Observation: commit `806d9ba85e4afbc2af58d7499496babfa7c68891`
  successfully completed a Notepad-only create/enumerate/capture/cleanup
  preflight. That observation validates harness mechanics only and is excluded
  from LibreOffice Material evidence.

## D-005 — publish a dependency-free static project site

- Date: 2026-07-16
- State: implemented locally; deployment unverified
- Decision: serve `site/index.html` and `site/styles.css` directly through a
  GitHub Pages Actions workflow.
- Reason: a static artifact keeps deployment auditable, accessible, responsive,
  and independent of package registries or externally hotlinked assets.

## D-006 — retain explicit import provenance

- Date: 2026-07-16
- State: active policy
- Decision: distinguish the fork's new root import commit from the upstream
  commit even though their tree objects match.
- Reason: tree equivalence does not preserve or recreate upstream ancestry.
