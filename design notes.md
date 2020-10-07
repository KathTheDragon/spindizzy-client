Could store character description/properties client-side and have client-side character editing & puppet creation
- If you're connected, hitting 'save' would immediately generate all the commands for making the changes
- If you're not, then the next time you connect it goes and does that
- If you happen to use the MUCK character editor yourself, it'll detect it and automatically update the offline copy

Can use `root.after(delay, func)` to keep the output pane updated within tkinter
