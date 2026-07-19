# LibreOffice Material update privacy

LibreOffice Material can check this repository's latest normal GitHub Release for a Windows x64 update. The check requests the public `windows-update-manifest.xml` release asset and therefore shares the ordinary network information needed for an HTTPS request with GitHub, such as the requesting IP address, request time, and LibreOffice update user agent.

The updater does not upload documents, document contents, filenames, profile data, or telemetry. Automatic checking can be disabled under **Tools > Options > LibreOffice > Online Update**.

When an update is available, LibreOffice Material downloads only the manifest's tag-specific canonical MSI from `codingmachineedge/libreoffice-material`. It verifies the declared byte count and SHA-256 after the file is closed and again immediately before installation. Installation is never silent: the updater asks for explicit confirmation, with **No** as the default, before starting the interactive Windows Installer.

Release packages are currently unsigned. Hash verification detects accidental corruption or replacement that does not match the published manifest, but it is not a substitute for publisher code signing and cannot protect against compromise of the GitHub repository itself.
