DEC-001
Decision: Build Windows exe on Windows Server 2012 R2 (native Windows VM or CI runner matching host)
Chosen Option: Windows VM build
Confidence: 85
Alternatives: Cross-compile with mingw-w64 from Linux; Windows container build (larger effort and host-kernel coupling)
Reasoning: The repository's batonogov devcontainer and Dockerfile are Linux-oriented (apt, .debs, X11) and cannot produce reliably compatible Win2012R2 artifacts; native Windows build ensures CRT/kernel compatibility.
Reversibility: High
Timestamp: 2026-02-12T21:49:23Z

