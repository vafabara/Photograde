"""
Ctrl+V support for the screens where photos are added (new feature:
paste an image from the clipboard).

GUI helpers only -- reading the clipboard and saving the image live in
core/clipboard.py and storage/pasted_images.py.
"""

import tkinter as tk
from tkinter import TclError

# Command-v is the macOS shortcut; Tk accepts the other two everywhere.
PASTE_SEQUENCES = ("<Control-v>", "<Control-V>", "<Command-v>")


def focus_in_text_input(widget):
    """
    True if the keyboard focus is in an entry or text box. There,
    Ctrl+V is also the normal "paste text" shortcut, so a clipboard
    that holds text must not trigger a "no image" message.
    """

    try:
        focused = widget.focus_get()
    except (KeyError, TclError):
        return False

    return isinstance(focused, (tk.Entry, tk.Text))


class PasteShortcut:
    """
    Calls `command(in_text_input)` when Ctrl+V is pressed in the
    window that contains `owner`, and removes the binding again when
    `owner` is destroyed -- so a screen that has been replaced never
    reacts to Ctrl+V.

    `in_text_input` tells the command whether the focus is in a text
    field (see focus_in_text_input).
    """

    def __init__(self, owner, command):

        self.owner = owner
        self.command = command
        self.root = owner.winfo_toplevel()
        self.bindings = []

        for sequence in PASTE_SEQUENCES:
            try:
                funcid = self.root.bind(sequence, self.on_key, add="+")
            except TclError:
                continue

            self.bindings.append((sequence, funcid))

        owner.bind("<Destroy>", self.remove, add="+")

    def on_key(self, event=None):

        if not self.owner.winfo_exists():
            return

        self.command(focus_in_text_input(self.owner))

    def remove(self, event=None):

        for sequence, funcid in self.bindings:
            try:
                self.root.unbind(sequence, funcid)
            except TclError:
                pass

        self.bindings = []
