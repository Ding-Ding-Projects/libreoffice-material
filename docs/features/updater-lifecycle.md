# Material updater lifecycle notifications

## Behavior

The Windows updater now routes eligible actionable and exceptional lifecycle
status through the shared bottom-right Material notification stack instead of
opening its dedicated legacy bubble.
The existing update icon remains visible and remains the action/details entry
point; the shared notification provides the non-blocking state summary and the
notification centre retains its history.

The controller sends a stable state separately from translated title/body text.
Eleven states cover checking, checking failure, no update, available/manual
download, automatic start, downloading, paused, download failure, downloaded,
and extension updates. Error cards persist, paused state is a warning, completed
download is a success, and the other lifecycle summaries are informational.
Worker-thread events are posted to the VCL main thread before reaching
`NotificationRouter`.

The state map is deliberately broader than the emission set. The existing
suppression policy keeps routine automatic checking and no-update results quiet,
hides the update icon when nothing is available, and emits only while the update
dialog is hidden or minimized. Repeated callbacks in the same state remain
suppressed.

Application-update cards name the exact update version. The in-dialog progress
bar remains the live percentage owner; paused and stalled cards include the
current percentage, and repeated progress callbacks in the same state do not
create toast spam. Check/download failures state the real automatic retry
behavior. Download-complete copy explains that Windows Installer—not
LibreOffice—reports installation completion or rollback.

This repository currently has no bundled, verifier-backed dim-sum catalog and
no release-code-name field in its update feed. The UI therefore uses the exact
version alone and does not invent a code name.

## Configuration

Online Update settings continue to control check cadence and automatic
download. Notification-centre preferences control whether and how the shared
cards are shown. The update icon remains available for opening details,
starting or pausing a download, resuming, and reviewing installation.

Install is intentionally different from status: after download verification,
the user must choose in a modal Yes/No decision that defaults to **No**. No
silent install path is added.

## Failure modes

- If no `SfxApplication` notification presenter exists, the router returns
  without blocking or opening a replacement modal; the update icon and update
  dialog remain the action/status fallback.
- If posting the main-thread event fails, its owned payload is destroyed and no
  stale callback is retained.
- Unsafe display text or an unapproved producer source is rejected by the
  notification store's existing privacy guards.
- Checking and download failures remain retryable according to their existing
  bounded backoff schedules; errors do not auto-dismiss.
- The app never reports an installer success or rollback result it cannot
  observe. Windows Installer owns that result.
- Source composition does not prove native compilation, notification pixels,
  focus behavior, localization, or a real update lifecycle.

## Security and accessibility

The notification change does not weaken updater trust. The selected GitHub
Release source, canonical MSI name/MIME/size/SHA-256, local bytes, and protected
non-overwriting staged copy are verified before launch. A retained handle
excludes writes/deletes across launch. Windows Installer remains interactive
and receives only `/i`, the staged MSI, `REBOOT=ReallySuppress`, and
`MSIRESTARTMANAGERCONTROL=DisableShutdown`.

Status notifications are non-modal, keyboard reachable, announced by the
shared notification surface, and reviewable in its centre. The only blocking
surface is the install decision the user must answer; it remains modal and
default-No. The no-browser error is now a persistent warning notification
rather than an acknowledgment-only modal box.

## Verification

`qa/windows-ui-contract/updater-lifecycle-composition.json` is enforced by
`bin/check-updater-lifecycle-composition.py` and twenty-two focused tests
(twenty-one mutations plus production). The contract pins all eleven state names,
severity mapping, main-thread handoff, legacy-bubble suppression, exact-version
ordering, progress/retry/rollback-owner copy, notification producer registration,
the `sfx` link, default-No consent, prelaunch verification, protected staging,
interactive command vector, and restart suppression.

The shared producer registry now covers nine producers across four modules and
passes forty tests. Immutable source commit
`cef0eefaca69dd0771b4b773ec157fcb291ded95` supplies this surface's final
source-ledger evidence; the generated ledger is 100.0% (1271/1271) with zero
pending rows. `runtime_verified` remains `false`; an exact-source Windows
build and a real check/download/pause/retry/consent/installer walkthrough are
still required.

## Suggested articles

- [Windows Installer lifecycle branding](msi-lifecycle-branding.md)
- [Release-channel integrity](../build/release-channel-integrity.md)
- [Feedback and notifications specification](../design/07-feedback.md)
- [Updater privacy](../../PRIVACY.md)
