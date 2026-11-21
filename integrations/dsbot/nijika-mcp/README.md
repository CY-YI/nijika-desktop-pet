# DS Bot local integration

The `nijika-mcp` package registers the installed `虹夏MCP-v2.exe` as a stdio
MCP server for DS Bot. `nijika-dsbot-dialog` supplies the end-of-turn and
decision rules. `global-instructions.txt` contains the marked block to merge
into the DS Bot home `AGENTS.md`.

The checked-in `cordis.patch.yml` is a template. Run the installer from the
repository root so the recipient's actual MCP path and DS Bot home are written
to a stable local copy of the bundle:

```powershell
powershell -ExecutionPolicy Bypass -File .\integrations\dsbot\install.ps1
```

The current Windows installation uses:

- DS Bot home: `%USERPROFILE%\.ds-bot`
- profile: `%USERPROFILE%\.ds-bot\profiles\ds-bot`
- skill: `%USERPROFILE%\.ds-bot\skills\nijika-dsbot-dialog`
- global instructions: `%USERPROFILE%\.ds-bot\AGENTS.md`
- stable bundle: `%USERPROFILE%\.ds-bot\integrations\nijika-dsbot-mcp`

The installer backs up the profile files, resolves the full onedir MCP path,
rewrites `__NIJIKA_MCP_EXE__` only in the installed copy, refreshes the
profile's `@cy/nijika-dsbot-mcp` link, and updates the skill and marked global
instructions block. Do not add the same MCP registration again in
`cordis.patch.yml`. Restart DS Bot after changing the bundle or global
instructions, then start a new task and verify the bubble plus its
`Agent · DS Bot` source label.
