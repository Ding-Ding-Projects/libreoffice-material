# Release-channel integrity

LibreOffice Material publishes two independent kinds of GitHub Release:

- a prebuilt Windows x64 MSI from `.github/workflows/windows-installer.yml`;
- a zip containing the touchless source installer from
  `.github/workflows/source-installer.yml`.

Their tags are immutable and disjoint, but GitHub's `Latest` release pointer is
shared mutable state. The stable updater and public MSI download URL require
that pointer to resolve to a release containing exactly one
`LibreOfficeMaterial-Windows-x64.msi`. A source-installer release must therefore
never become Latest.

> **Incident and repair record (2026-07-26):** before these guards landed, a
> source-installer release became Latest. The public
> `releases/latest/download/LibreOfficeMaterial-Windows-x64.msi` route then
> returned 404 because that release contains no MSI. The one-time repair has now
> restored `windows-msi-123-1-952090ce26` at `952090ce2` as Latest with exactly
> four assets. The canonical unauthenticated MSI, XML, and checksum Latest URLs
> returned HTTP 200 with lengths 197,111,808, 960, and 103 bytes respectively.
> The three legacy unguarded MSI runs were cancelled before this follow-up push;
> the same Latest identity, asset shape, and public route lengths were verified
> again after cancellation.

## Behavior

### Source-installer channel

The source workflow reads the repository's Latest release without cache before
creating anything, then creates a normal, non-draft release with
`--latest=false` and repeats the same check afterwards. Both checks fail unless:

- Latest is not the source tag just published; and
- Latest contains exactly the canonical Windows MSI asset name.

Before release creation, a fail-closed matching-ref lookup proves the exact
source tag is absent; API failure is not treated as absence. The workflow still
publishes its own immutable source tag even though it cannot claim Latest. Its
tag creation no longer causes the exhaustive Windows UI contract to run a
second time: that workflow accepts branch pushes, pull requests, and manual
dispatches, but excludes release-tag pushes.

### Stable MSI channel

Publisher-capable main-branch MSI runs use one repository-wide concurrency group
with `cancel-in-progress: false`. A non-main manual diagnostic run gets a
run-unique group, so it cannot occupy or replace the stable queue even though its
publish step is skipped. GitHub may discard superseded *pending* main MSI jobs in
favor of the newest pending job, but it does not cancel the running publisher;
every commit still receives the fast source-installer release.

After its MSI and metadata pass the draft-release checks, the workflow reads the
current Latest release. If Latest contains the canonical MSI and names an exact
40-hex commit, the workflow compares that commit with the commit it built. It
promotes the new release to Latest only when the new commit is `ahead` of or
`identical` to the current stable commit. An older manual run, a late queued
build, an unparseable target, or an ancestry lookup failure produces a normal
historical release with `--latest=false`; it does not roll Latest backward.

When promotion is allowed, the workflow still verifies the exact release
target, title, four asset names, sizes, and digests, then downloads all four
public Latest assets with cache busting and compares their bytes. When
promotion is withheld, it verifies the preserved release identity when the
pre-publish read succeeded and requires the exact stable four-asset shape.

### CI fleet closure

`bin/check-build-free-gate-coverage.py` inventories every eligible build-free
checker and mutation suite and fails when one is not invoked by its required CI
workflow. Its own mutation suite protects that coverage rule. The release-
channel checker and mutation suite fail closed on removal of the source
`--latest=false` policy, the post-publish stable-MSI assertion, the branch-only
Windows UI trigger, or the stable MSI serialization/monotonic-promotion rules.

## Configuration

| Setting | Value | Purpose |
| --- | --- | --- |
| Stable workflow | `.github/workflows/windows-installer.yml` | Builds, validates, publishes, and may promote a Windows MSI |
| Source workflow | `.github/workflows/source-installer.yml` | Packages the build-from-source script without claiming Latest |
| Stable tag | `windows-msi-<run>-<attempt>-<sha10>` | Immutable MSI release identity |
| Source tag | `source-installer-<run>-<attempt>-<sha10>` | Immutable source-package release identity |
| Canonical MSI asset | `LibreOfficeMaterial-Windows-x64.msi` | Required discriminator for the stable Latest channel |
| Main MSI concurrency group | `windows-msi-stable-publisher` | Makes publisher-capable Latest promotion single-writer |
| Non-main manual group | `windows-msi-nonpublisher-<run-id>` | Keeps diagnostic builds out of the stable queue |
| Pending-run cancellation | `cancel-in-progress: false` | Never cancels the running publisher |

The updater and public download button consume the GitHub Latest route. Changing
the canonical MSI name or release policy therefore requires a coordinated
update to the workflow, updater metadata, contracts, and documentation.

## Failure modes

| Failure | Result |
| --- | --- |
| A source release attempts to become Latest | Source publication or the integrity gate fails closed |
| Latest is already invalid before a source publish | The source workflow fails before creating another release |
| Exact source-tag lookup fails or finds a collision | Publication stops; API failure is never accepted as tag absence |
| Latest lacks the canonical MSI after a source publish | The source job fails and reports channel corruption; operators restore a known verified MSI and recheck public routes |
| An older/manual MSI build finishes after a newer stable build | Its verified release remains public but non-Latest |
| Current Latest target is not an exact commit | The new MSI is published without promotion rather than guessing ancestry |
| GitHub Latest or compare API is unavailable | Promotion is withheld; the workflow does not roll the channel forward blindly |
| A build-free checker is omitted from CI | Fleet-closure validation fails |
| A release tag is pushed | The Windows UI contract does not duplicate its branch-push run |
| A release tag already exists | The publisher fails instead of overwriting immutable release state |

The pre-fix 404 is the important distinction: repository source can be fixed
while the remote mutable pointer remains wrong. The 2026-07-26 repair required
an explicit operational update and public-route checks; it was not inferred
from a green source checker.

## Security considerations

- Release jobs receive `contents: write`; validation jobs do not need broader
  repository or organization permissions.
- Exact targets, canonical asset names, positive sizes, and SHA-256 digests are
  checked before stable publication. Public bytes are re-downloaded after a
  successful Latest promotion.
- Serial promotion narrows the check-to-edit race around mutable Latest state;
  ancestry checks prevent an older or divergent build from silently becoming
  the updater target.
- API failures are fail-safe for Latest promotion. They may delay a stable
  update, but do not justify guessing at release ancestry.
- Workflows must not print GitHub tokens or other credentials. The configured
  token is used only through authenticated GitHub CLI operations.

## Verification status

- Commit `27a7c7d00` added source `--latest=false`, the post-publish stable-MSI
  assertion, branch-only Windows UI triggers, build-free fleet closure, and the
  release-channel integrity checker/mutation suite. Source run `30213637973`
  attempt 2 subsequently published `source-installer-20-2-27a7c7d000` while
  preserving MSI-123 as Latest. The later exact-tag matching-ref preflight is
  locally verified and awaits its first hosted run.
- Current source also serializes MSI publishers and makes Latest promotion
  ancestry-monotonic. No MSI workflow has yet completed under that revised
  publisher, so hosted behavior remains unverified.
- At least twenty source-installer releases had been published by 2026-07-26.
  That proves the packaging/publishing channel has run; it does **not** prove that
  `Install-LibreOfficeMaterial-FromSource.ps1` can provision a clean Windows
  host, compile LibreOffice, install shortcuts, and launch the result end to
  end.
- The pre-fix source release did become Latest and the stable MSI Latest URL did
  return 404. The one-time GitHub repair restored
  `windows-msi-123-1-952090ce26` at `952090ce2` with exactly four assets. The
  canonical unauthenticated MSI/XML/checksum routes returned HTTP 200 at the
  expected 197,111,808/960/103-byte lengths.
- Runs `30209383677`, `30210931048`, and `30213637979` were created before the
  new constant concurrency group. They were cancelled, and the
  Latest/tag/asset/route checks passed again afterwards. No MSI workflow has yet
  completed under the revised single-writer publisher.
