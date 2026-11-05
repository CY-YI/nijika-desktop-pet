# Third-party notices

The MIT license in `LICENSE` applies to original source code in this
repository only. Dependencies and imported resources keep their own licenses.

## Direct dependencies

| Package | Version used for the verified build | License | Source |
| --- | --- | --- | --- |
| Pillow | 12.2.0 | MIT-CMU | [Pillow](https://github.com/python-pillow/Pillow) |
| PyInstaller | 6.20.0 | GPL-2.0-or-later with the PyInstaller exception | [PyInstaller](https://github.com/pyinstaller/pyinstaller) |
| MCP Python SDK | 2.3.0 | MIT | [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk) |
| pywebview | 6.2.1 | BSD-3-Clause | [pywebview](https://github.com/r0x0r/pywebview) |

The complete pinned dependency set is in `requirements-lock.txt`. The frozen
MCP runtime retains package metadata and license files under its `_internal`
directory. When redistributing a rebuilt binary, keep those files or provide
equivalent license texts in the distribution documentation.

## Installer translation

`installer/ChineseSimplified.isl` is the Simplified Chinese translation from
the Inno Setup translation repository. Its original maintainer attribution and
source link are retained in that file. Do not remove those notices when
modifying the installer language file.

## Character, icon and support materials

The files under `assets/`, `art/`, `web-demo/` and the default character
references in the UI are project materials with a separate rights status.
The repository does not grant a blanket license to reuse the Nijika-derived
character or icon artwork. `distribution/support.png` is an author-provided
public payment image; it is included by explicit author choice, but this does
not grant reuse rights for the image or its payment identifier.

Before publishing a source snapshot with these files, obtain redistribution
permission, replace them with original or permissively licensed artwork, or
publish the code with those materials removed and document how users provide
their own assets.
