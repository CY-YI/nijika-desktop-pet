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

The author confirmed on 2026-11-05 that the role, icon and accompanying
screenshots in this repository were created by the author and may be publicly
distributed with the project. This confirmation applies to the project
materials listed above; it does not change the licenses of third-party
dependencies or referenced external works.

`distribution/support.png` is an author-provided public payment image. It is
included by explicit author choice, but the MIT code license does not grant
reuse rights for the image or its payment identifier.
