# Clean Windows install, upgrade and uninstall plan

This is the release-gate record for a disposable Windows 10/11 x64 machine.
It is a plan and evidence template; it has not been executed on the daily
computer.

## Inputs

- Installer: `dist-release/installer-0.1.10/虹夏桌宠-Setup-0.1.10.exe`
- Expected installer SHA-256:
  `063805df2fa9716b6d6313916d4f8ebae05267f8e0b7420a2f9822bce4f1b8f9`
- Intended install root: `%LOCALAPPDATA%\NijikaDesktopPet\app`
- Intended user data root: `%USERPROFILE%\.nijika-desktop-pet`
- Test account: a disposable local Windows account with no existing Codex,
  DSH, Work, Claude, Agent profiles or Nijika data.

## Before installation

1. Create a VM checkpoint or Windows Sandbox instance and record the Windows
   version, architecture and WebView2 availability.
2. Verify the installer hash and record the empty state of the install root,
   user data root, desktop shortcuts, startup folder and uninstall registry.
3. Keep the network available only for the installer prerequisites and record
   every downloaded dependency; do not sign in to personal accounts.

## Fresh install acceptance

1. Run the installer as the disposable user and choose the default install
   root, desktop shortcut and optional startup entry.
2. Verify the desktop pet starts without a console window and the settings
   center opens.
3. Confirm the installed tree contains `dist\虹夏MCP-v2\虹夏MCP-v2.exe`
   and its sibling `_internal\` directory.
4. Confirm the MCP is local stdio, no public listening port is opened, and
   repeated MCP starts do not create new `%TEMP%\_MEI*` directories.
5. Use the settings center test reminder, then verify one local message and
   one click reply. Do not claim external Agent integration until a new task
   in that client observes the call.
6. Record process names, shortcut targets, startup target, installed files,
   package version and the SHA-256 values of the three programs.

## Upgrade acceptance

1. Before upgrading, create a harmless sentinel notification, one imported
   test skin, one Agent profile and one settings value in the disposable user
   data root.
2. Install the candidate over the existing installation.
3. Verify the new program version and onedir MCP path are active after
   restarting the pet and reconnecting the client.
4. Verify the sentinel notification, skin, Agent profile and settings remain.
5. Verify the exact legacy onefile MCP path is removed only when the installer
   upgrade rule targets it; unrelated files and client configuration remain.

## Uninstall acceptance

1. Close the pet and test client, then uninstall from Windows Apps.
2. Verify the installed application directory, desktop shortcut, startup
   entry and uninstall registration are removed according to the installer
   contract.
3. Verify `%USERPROFILE%\.nijika-desktop-pet` remains intact with the
   sentinel data and no unrelated user files are touched.
4. Verify no Nijika process or MCP process remains and no new `_MEI*`
   residue is created.
5. Restore the VM checkpoint and retain the logs, hashes and screenshots as
   `diagnostics/clean-windows-install-<date>/` outside Git.

## Release decision

Mark the gate `PASS` only when fresh install, upgrade, uninstall, data
preservation and residue checks all have observed evidence. A skipped VM or a
test interrupted before its result is `UNVERIFIED`; keep the installer as a
prerelease and do not claim the full Windows lifecycle passed.
