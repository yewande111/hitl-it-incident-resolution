"""Step 15: fill in the page numbers in the Contents, List of Figures and List of Tables.

Script 12 cannot work out page numbers, and Word on a Mac does not always offer to update the
lists when the file is opened. This asks Microsoft Word to open "Dissertation - Full Draft.docx",
update the three lists and save, so the page numbers are already there for the reader.
Word marks the refreshed lists as US English, so the whole text is then set to English (UK)
to keep the British spelling check.
If the draft is open in Word it is closed first (without saving), so close it yourself first
if you have made changes in Word that you want to keep.

Needs Microsoft Word on a Mac. Run from the Project folder after step 12:
    python3 code/15_update_contents_in_word.py
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DRAFT = ROOT / "Dissertation - Full Draft.docx"

SCRIPT = '''
on run argv
    set p to item 1 of argv
    set nm to item 2 of argv
    tell application "Microsoft Word"
        close (every document whose name is nm) saving no
        open file name p
        set d to active document
        set n to count of tables of contents of d
        repeat with i from 1 to n
            update table of contents i of d
        end repeat
        set language ID of (text object of d) to english uk
        save d
        return n
    end tell
end run
'''

if __name__ == "__main__":
    mac_path = "MacOs" + str(DRAFT).replace("/", ":")      # Word wants an old style Mac path
    out = subprocess.run(["osascript", "-", mac_path, DRAFT.name], input=SCRIPT,
                         capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(out.stderr.strip())
    print(f"updated {out.stdout.strip()} lists in {DRAFT.name} and saved it")
