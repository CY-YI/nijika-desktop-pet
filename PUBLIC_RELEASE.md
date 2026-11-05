# Public release readiness

This document records the checks required before changing the repository to a
public open-source repository.

## Public snapshot

- Final audited development commit: `5c6cd6e2da7d9ed3d6b1f0f250cdba4ed440196a`
- Clean public branch: `public-snapshot-20261105`
- Public default branch: `main`, serving the same clean root commit
- Public history boundary: the public snapshot has no parent commit and does not
  inherit the development branch's author metadata or development paths
- Python tests: 196 passed, 1 optional PyYAML test skipped
- JavaScript tests: 20 passed
- Release/source package scan: no SQLite database, log, private key, token, or
  user Agent configuration found

## Required before public visibility

1. Keep `LICENSE` and `THIRD_PARTY_NOTICES.md` with the source.
2. Resolve the separate rights status of the character, icon, screenshots,
   and payment image. The author confirmed on 2026-11-05 that the character,
   icon and screenshots are author-created and may be publicly distributed;
   the payment image remains intentionally public but is not covered by the
   MIT code license.
3. Use the clean `public-snapshot-20261105` branch or a new public repository;
   remove personal author emails and old development paths from published Git
   history. A `.mailmap` does not remove those values from raw commits. The
   safe option is a new public repository or a new squashed history created
   from the audited snapshot. Do not force-rewrite the existing shared history
   without reviewing the remote branches and tags first.
4. Make the audited snapshot the default branch, or merge it into `main` and
   verify the default branch contents before changing repository visibility.
5. Rebuild and re-scan the final public package after any asset or history
   change. Keep the installer marked as prerelease until clean Windows
   install/upgrade/uninstall testing is complete.

## Completed publication boundary

The clean `public-snapshot-20261105` branch and `main` were replaced with a
new root commit created from the final audited tree. The root commit uses the
GitHub noreply identity and does not include the development branch history.

Other remote development branches and historical tags can still expose their
own old commits while they remain published. Replacing `main` does not erase
GitHub caches, forks, clones, old branch refs or tags. Deleting or replacing
those refs requires a separate destructive history cleanup decision.

The clean Windows test sequence is recorded in
`CLEAN_WINDOWS_INSTALL_PLAN.md`; it is a release gate and has not been run on
this computer.

## Intentionally public data

The developer selected `distribution/support.json` and
`distribution/support.png` for inclusion in release packages. The image is a
public payment identifier and may be copied once the repository is public.
Remove it before publication if that exposure is no longer desired.

## Local audit

The latest read-only evidence is kept outside Git at
`diagnostics/public-open-source-audit-20261105/report.json`.
