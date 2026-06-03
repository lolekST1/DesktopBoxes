' Uruchamia DesktopBoxes bez okna konsoli (dwuklik na tym pliku).
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = "pythonw.exe"
shell.CurrentDirectory = scriptDir
shell.Run """" & pyw & """ """ & scriptDir & "\main.py""", 0, False
