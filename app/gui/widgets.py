import customtkinter as ctk
from tkinter import TclError

from . import theme


def create_info_label(parent, text):
    """Single full-width text row (kept for compatibility)."""

    label = theme.label(parent, text, size=14, anchor="w")

    label.pack(
        fill="x",
        padx=20,
        pady=5
    )

    return label


# -----------------------------------------
# DIALOG FOUNDATION
# -----------------------------------------

def create_modal(parent, title, width, height, accent=None):
    """
    Shared shell for every popup: themed, centred over the main
    window, closes on Escape, and grabs input once it is visible
    (grab_set right after creation can fail on some platforms).
    Returns the CTkToplevel; callers add their own content.
    """

    window = ctk.CTkToplevel(parent)

    window.title(title)
    window.configure(fg_color=theme.SURFACE)
    window.resizable(False, False)

    try:
        root = parent.winfo_toplevel()

        x = root.winfo_rootx() + (root.winfo_width() - width) // 2
        y = root.winfo_rooty() + (root.winfo_height() - height) // 2

        window.geometry(f"{width}x{height}+{max(x, 0)}+{max(y, 0)}")
        window.transient(root)

    except TclError:
        window.geometry(f"{width}x{height}")

    def take_focus():
        try:
            window.lift()
            window.focus_force()
            window.grab_set()
        except TclError:
            pass  # window was closed before it became visible

    window.after(120, take_focus)
    window.bind("<Escape>", lambda event: window.destroy())

    if accent:
        ctk.CTkFrame(
            window,
            height=4,
            corner_radius=0,
            fg_color=accent
        ).pack(fill="x")

    return window


def _message_dialog(parent, title, message, accent):

    window = create_modal(parent, title, 420, 210, accent=accent)

    theme.label(
        window,
        title,
        size=16,
        weight="bold"
    ).pack(
        pady=(22, 6)
    )

    theme.label(
        window,
        message,
        size=13,
        color=theme.TEXT_MUTED,
        wraplength=360,
        justify="center"
    ).pack(
        padx=20,
        pady=(0, 18)
    )

    theme.primary_button(
        window,
        "OK",
        window.destroy,
        width=100
    ).pack()

    window.bind("<Return>", lambda event: window.destroy())


def show_error(parent, message):

    _message_dialog(parent, "Error", message, theme.DANGER)


def show_info(parent, title, message):
    """Informational popup -- same layout as show_error, custom title."""

    _message_dialog(parent, title, message, theme.ACCENT)


def show_confirm(parent, message, on_yes):
    """
    Modal Yes/No confirmation (used for Delete Class / Delete
    Student). Calls `on_yes()` only if the user picks Yes -- picking
    No, pressing Escape or closing the dialog does nothing. Yes is
    drawn in the danger colour because every use is destructive.
    """

    window = create_modal(parent, "Confirm", 420, 210, accent=theme.DANGER)

    theme.label(
        window,
        "Are you sure?",
        size=16,
        weight="bold"
    ).pack(
        pady=(22, 6)
    )

    theme.label(
        window,
        message,
        size=13,
        color=theme.TEXT_MUTED,
        wraplength=360,
        justify="center"
    ).pack(
        padx=20,
        pady=(0, 18)
    )

    def handle_yes():
        window.destroy()
        on_yes()

    row = ctk.CTkFrame(window, fg_color="transparent")

    row.pack()

    ctk.CTkButton(
        row,
        text="Yes",
        width=100,
        height=36,
        corner_radius=8,
        font=theme.font(13, "bold"),
        fg_color=theme.DANGER,
        hover_color="#FCA5A5",
        text_color="#2A0A0A",
        command=handle_yes
    ).pack(
        side="left",
        padx=8
    )

    theme.secondary_button(
        row,
        "No",
        window.destroy,
        width=100,
        height=36
    ).pack(
        side="left",
        padx=8
    )


def show_prompt(parent, title, label_text, on_submit):
    """
    Small popup that asks for one line of text (naming a Rule Engine
    preset). Calls `on_submit(text)` only if the professor presses
    Save (or Enter) with a non-blank value; Cancel/closing does
    nothing.
    """

    window = create_modal(parent, title, 400, 240, accent=theme.ACCENT)

    theme.label(
        window,
        label_text,
        size=14,
        weight="bold",
        wraplength=340
    ).pack(
        pady=(22, 10),
        padx=24,
        anchor="w"
    )

    entry = theme.text_entry(window)

    entry.pack(
        fill="x",
        padx=24,
        pady=(0, 6)
    )

    error_label = theme.error_label(window)

    error_label.pack(
        fill="x",
        padx=24,
        pady=(0, 8)
    )

    def handle_save():

        text = entry.get().strip()

        if not text:
            error_label.configure(text="Please enter a name.")
            return

        window.destroy()
        on_submit(text)

    entry.bind("<Return>", lambda event: handle_save())

    row = ctk.CTkFrame(window, fg_color="transparent")

    row.pack(pady=(4, 16))

    theme.primary_button(
        row,
        "Save",
        handle_save,
        width=100,
        height=36
    ).pack(
        side="left",
        padx=8
    )

    theme.secondary_button(
        row,
        "Cancel",
        window.destroy,
        width=100,
        height=36
    ).pack(
        side="left",
        padx=8
    )

    window.after(200, entry.focus)


def show_note_dialog(parent, initial_text, on_save):
    """
    Popup for adding/editing a single photo's note. Calls
    `on_save(text)` only if the professor presses Save; Cancel/
    closing the dialog discards any typed changes.
    """

    window = create_modal(parent, "Photo Note", 460, 330, accent=theme.ACCENT)

    theme.label(
        window,
        "Photo note",
        size=16,
        weight="bold"
    ).pack(
        anchor="w",
        padx=24,
        pady=(20, 2)
    )

    theme.muted(
        window,
        "Saved with this photo and included in the results export."
    ).pack(
        anchor="w",
        padx=24,
        pady=(0, 10)
    )

    textbox = ctk.CTkTextbox(
        window,
        height=130,
        corner_radius=8,
        font=theme.font(13),
        fg_color=theme.SURFACE_ALT,
        border_width=1,
        border_color=theme.BORDER,
        text_color=theme.TEXT
    )

    textbox.pack(
        fill="both",
        expand=True,
        padx=24,
        pady=(0, 14)
    )

    if initial_text:
        textbox.insert("1.0", initial_text)

    def handle_save():
        text = textbox.get("1.0", "end").strip()
        window.destroy()
        on_save(text)

    row = ctk.CTkFrame(window, fg_color="transparent")

    row.pack(pady=(0, 16))

    theme.primary_button(
        row,
        "Save",
        handle_save,
        width=100,
        height=36
    ).pack(
        side="left",
        padx=8
    )

    theme.secondary_button(
        row,
        "Cancel",
        window.destroy,
        width=100,
        height=36
    ).pack(
        side="left",
        padx=8
    )

    window.after(200, textbox.focus)
