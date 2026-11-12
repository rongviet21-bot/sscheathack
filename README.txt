sscheathack.exe - Windows build

1. Install Python 3.10+ on Windows and enable the Python launcher (py).
2. Open this folder in File Explorer.
3. Double-click build_windows.bat.
4. The executable will be created at dist\sscheathack.exe.

Features:
- English / Vietnamese interface toggle.
- Scan accessible drives or Minecraft-related folders.
- Inspect JAR archive entry names and embedded text metadata for known client/module signatures.
- Monitor Minecraft log files for newly appended lines.
- Export local JSON/TXT findings.

Important limitations:
- This is an indicator scanner, not a definitive cheat detector.
- AutoTotem / AutoCart cannot reliably be proven from ordinary Minecraft logs alone.
- No remote upload, stealth, credential collection, file modification, or deletion.
- Permission-denied paths are skipped. Full-disk scans can take a long time.
- A filename, hidden attribute, or string match is not proof of cheating.
