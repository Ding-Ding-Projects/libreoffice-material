# Upstream provenance

LibreOffice Material is an independent experimental fork of the LibreOffice
core source maintained by The Document Foundation and its contributor
community. It is not an official The Document Foundation distribution.

## Imported baseline

| Field | Value |
| --- | --- |
| Upstream repository | `https://github.com/LibreOffice/core.git` |
| Upstream commit | `63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21` |
| Upstream subject | `CppunitTest_sw_core_text: disable test on Windows` |
| Fork import commit | `44d393283e776c7e099763496c57b02ae509cd15` |
| Import form | new root commit containing the exact upstream tree |
| Verified tree object | `68ccb73abac4f7da67f894f11b0802627e90b474` |

The root import preserves every file in that upstream tree but does not embed
upstream commit ancestry in the fork's `main` branch. The `upstream` remote is
therefore essential for provenance and future synchronization.

## Reproduce the tree check

With both commits available locally:

```console
git rev-parse 44d393283e776c7e099763496c57b02ae509cd15^{tree}
git rev-parse 63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21^{tree}
git diff --stat 63584e7f9f0cdc74b0e004bcbf88e5c3b42dba21 44d393283e776c7e099763496c57b02ae509cd15
```

At import verification, both `rev-parse` commands returned
`68ccb73abac4f7da67f894f11b0802627e90b474`, and the diff was empty.

If the upstream commit is missing, fetch it without rewriting local work:

```console
git remote add upstream https://github.com/LibreOffice/core.git
git fetch upstream master
```

If `upstream` already exists, confirm its URL before fetching.

## Synchronization policy

- never describe a fork commit as an upstream commit merely because its tree is
  equal;
- record the exact upstream commit used for every future import or merge;
- retain original author, license, and notice information;
- document conflicts that alter upstream behavior;
- rerun build and headless evidence gates after each synchronization.

## Licensing and names

The source tree includes the authoritative license texts in `COPYING`,
`COPYING.LGPL`, and `COPYING.MPL`, plus source-header guidance in
`TEMPLATE.SOURCECODE.HEADER`. Those files and per-file headers govern the code;
this summary does not replace them.

LibreOffice and The Document Foundation names and marks belong to their
respective owners. Fork documentation should always identify upstream and avoid
implying endorsement.
