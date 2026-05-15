' More-D-Admin — Silent launcher (no console window at all)
' Double-click this file for a completely clean launch.

Option Explicit

Dim Shell, FSO, ScriptDir, PythonW, Python, MainPy

Set Shell     = CreateObject("WScript.Shell")
Set FSO       = CreateObject("Scripting.FileSystemObject")
ScriptDir     = FSO.GetParentFolderName(WScript.ScriptFullName)
MainPy        = ScriptDir & "\main.py"

' ── Find pythonw.exe ──────────────────────────────────────────
Dim Candidates(12)
Candidates(0)  = Shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe")
Candidates(1)  = Shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe")
Candidates(2)  = Shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe")
Candidates(3)  = Shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\Python\Python310\pythonw.exe")
Candidates(4)  = "C:\Python313\pythonw.exe"
Candidates(5)  = "C:\Python312\pythonw.exe"
Candidates(6)  = "C:\Python311\pythonw.exe"
Candidates(7)  = "C:\Python310\pythonw.exe"
Candidates(8)  = Shell.ExpandEnvironmentStrings("%ProgramFiles%\Python313\pythonw.exe")
Candidates(9)  = Shell.ExpandEnvironmentStrings("%ProgramFiles%\Python312\pythonw.exe")
Candidates(10) = Shell.ExpandEnvironmentStrings("%ProgramFiles%\Python311\pythonw.exe")
Candidates(11) = Shell.ExpandEnvironmentStrings("%ProgramFiles%\Python310\pythonw.exe")
Candidates(12) = ""

PythonW = ""
Dim i
For i = 0 To 11
    If FSO.FileExists(Candidates(i)) Then
        PythonW = Candidates(i)
        Exit For
    End If
Next

' ── Fall back to PATH pythonw ─────────────────────────────────
If PythonW = "" Then
    On Error Resume Next
    Dim result
    result = Shell.Run("where pythonw", 0, True)
    On Error GoTo 0
    If result = 0 Then
        PythonW = "pythonw"
    End If
End If

' ── If still not found, try launch.bat ───────────────────────
If PythonW = "" Then
    Dim LaunchBat
    LaunchBat = ScriptDir & "\launch.bat"
    If FSO.FileExists(LaunchBat) Then
        Shell.Run """" & LaunchBat & """", 1, False
    Else
        MsgBox "Python not found." & vbCrLf & vbCrLf & _
               "Please install Python 3.11+ from https://python.org" & vbCrLf & _
               "Tick 'Add Python to PATH' during installation.", _
               vbCritical, "More-D-Admin"
    End If
    WScript.Quit
End If

' ── Check dependencies are installed ─────────────────────────
Dim CheckCmd
CheckCmd = """" & PythonW & """ -c ""import customtkinter, psutil"""
Dim rc
rc = Shell.Run(CheckCmd, 0, True)

If rc <> 0 Then
    ' Dependencies missing — run batch installer first
    Dim SetupBat
    SetupBat = ScriptDir & "\launch.bat"
    If FSO.FileExists(SetupBat) Then
        Shell.Run """" & SetupBat & """", 1, True
    End If
End If

' ── Launch the app (window=0 = hidden, bWaitOnReturn=False) ──
Shell.Run """" & PythonW & """ """ & MainPy & """", 0, False

WScript.Quit
