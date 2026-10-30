# Windows installer

`nijika.iss` builds the per-user Windows Setup EXE. Use
`tools/build_installer.ps1`; do not compile against the whole workspace.
The script first creates an allowlisted staging tree.

`ChineseSimplified.isl` is the unmodified Simplified Chinese language file
from the official Inno Setup source repository:
https://github.com/jrsoftware/issrc/blob/main/Files/Languages/ChineseSimplified.isl
It retains its original maintainer notices. The project uses it with Inno
Setup 6.7.3 because that compiler version does not ship this translation.
