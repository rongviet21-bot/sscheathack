@echo off
setlocal
py -m pip install --upgrade pip pyinstaller
py -m PyInstaller --noconfirm --clean --onefile --windowed --name sscheathack sscheathack.py
if exist dist\sscheathack.exe (
  echo Build complete: dist\sscheathack.exe
) else (
  echo Build failed. Check the output above.
)
pause
