# Pre-push gla11y accessibility FATAL gate

`bin/check-ui-a11y-fatals.py` (commit `3da2eae51`) reproduces the build's exact
`gla11y` invocation locally so `.ui` accessibility FATALs are caught in seconds
**before push** — instead of aborting the ~3h Windows MSI build at its a11y
stage ("Link critical Windows desktop library"), roughly three hours in.

It was born from this session's actual MSI failures: wave-introduced one-sided
`label-for` / mnemonic-to-`GtkBox` / duplicate-mnemonic FATALs (fixed in
`b3e63d6af`) that no local checker caught, because nothing local ran `gla11y`
the way the build does.

## Behavior

The script reproduces the recipe from `solenv/gbuild/UIConfig.mk` verbatim,
per UIConfig module:

```
<interp> bin/gla11y \
    -P <SRCDIR>/ \
    -f solenv/sanitizers/ui/<module>.false    (only if it exists) \
    -s solenv/sanitizers/ui/<module>.suppr    (only if it exists) \
    --widgets-suffixignored +ValueSet,HBox,VBox,ToolBox,Preview,PreviewWin,PreviewWindow,PrevWindow \
    --widgets-button +svtlo-ManagedMenuButton \
    --fatal-all \
    --not-fatal-type duplicate-mnemonic \
    --not-fatal-type labelled-by-and-mnemonic \
    --not-fatal-type orphan-label \
    <uifiles...>
```

Key fidelity points:

- The **`-P <SRCDIR>/` prefix** and repo-relative `.ui` paths are essential:
  that is how gla11y makes printed file names match the repo-relative entries
  in the suppression files. With absolute paths (and no matching prefix strip)
  the suppressions silently fail to match and dozens of phantom FATALs appear.
- Each module's `.false` / `.suppr` sanitizer files are passed only when they
  exist.
- The module -> `.ui`-files mapping is parsed from the authoritative
  `*/UIConfig_*.mk` `gb_UIConfig_add_uifiles` entries, **not** by globbing
  directories, so `--list` reflects the full registration set.

## Configuration

| Flag | Effect |
| --- | --- |
| `--list` | List the discovered UIConfig modules and exit. |
| `--module NAME` | Restrict the run to one or more named modules (repeatable). |

## Failure modes

Fails **closed**: gla11y prints e.g. "3 new errors" / "1 new fatal"; the script
captures the leading count and reports a module as `FAIL` when N > 0. Any
module with new errors or fatals makes the whole gate exit non-zero.

Exit codes: `0` all modules clean; `1` at least one module reported new
gla11y errors/fatals; `2` usage / internal error.

## Verification

- **Portable interpreter.** The gla11y subprocess is launched with
  `sys.executable`, so it runs under whatever Python invoked the checker rather
  than assuming a fixed interpreter name.
- Verified to report **0 FATALs on a clean tree** and to **fail closed on an
  injected `.ui` defect**.
- This is a build-free reproduction of the CI gate, not the CI gate itself; the
  authoritative run is still the MSI build's own gla11y stage. The value is
  catching the same failure class in seconds pre-push.

## Security considerations

None. The gate reads `.ui` and sanitizer files and runs the in-tree `gla11y`
script; it makes no network access and changes no product behavior.
