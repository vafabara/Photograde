import customtkinter as ctk


def create_info_label(parent, text):

    label = ctk.CTkLabel(
        parent,
        text=text,
        font=ctk.CTkFont(size=14),
        anchor="w"
    )

    label.pack(
        fill="x",
        padx=20,
        pady=5
    )

    return label


def show_error(parent, message):

    error_window = ctk.CTkToplevel(parent)

    error_window.title("Error")
    error_window.geometry("400x180")
    error_window.resizable(False, False)

    label = ctk.CTkLabel(
        error_window,
        text=message,
        font=ctk.CTkFont(size=15),
        wraplength=340
    )

    label.pack(pady=(35, 20))

    button = ctk.CTkButton(
        error_window,
        text="OK",
        width=100,
        command=error_window.destroy
    )

    button.pack()


def show_info(parent, title, message):
    """
    Simple informational popup (new feature: Class Results page --
    Export "Coming Soon"). Same layout as show_error, but with a
    caller-provided title since this isn't necessarily an error.
    """

    info_window = ctk.CTkToplevel(parent)

    info_window.title(title)
    info_window.geometry("400x180")
    info_window.resizable(False, False)

    label = ctk.CTkLabel(
        info_window,
        text=message,
        font=ctk.CTkFont(size=15),
        wraplength=340
    )

    label.pack(pady=(35, 20))

    button = ctk.CTkButton(
        info_window,
        text="OK",
        width=100,
        command=info_window.destroy
    )

    button.pack()


def show_confirm(parent, message, on_yes, on_no=None):
    """
    Modal Yes/No confirmation dialog (new feature: Delete Class /
    Delete Student confirmations). Calls `on_yes()` only if the user
    picks Yes.

    `on_no` is optional (new feature: Unsaved Exit Warning). When it
    is given, it is called if the user picks No -- needed when "No"
    means "leave anyway" rather than "cancel". Without it, No does
    nothing, exactly as before. Closing the dialog with the window's
    X button never calls either callback.
    """

    confirm_window = ctk.CTkToplevel(parent)

    confirm_window.title("Confirm")
    confirm_window.geometry("400x180")
    confirm_window.resizable(False, False)
    confirm_window.grab_set()

    label = ctk.CTkLabel(
        confirm_window,
        text=message,
        font=ctk.CTkFont(size=15),
        wraplength=340,
        justify="center"
    )

    label.pack(pady=(35, 20))

    def handle_yes():
        confirm_window.destroy()
        on_yes()

    def handle_no():
        confirm_window.destroy()

        if on_no:
            on_no()

    button_row = ctk.CTkFrame(
        confirm_window,
        fg_color="transparent"
    )

    button_row.pack()

    ctk.CTkButton(
        button_row,
        text="Yes",
        width=100,
        fg_color="#1F8F4C",
        hover_color="#27AE60",
        command=handle_yes
    ).pack(
        side="left",
        padx=10
    )

    ctk.CTkButton(
        button_row,
        text="No",
        width=100,
        fg_color="transparent",
        hover_color="#3a1f1f",
        border_color="#FF6B6B",
        border_width=1,
        command=handle_no
    ).pack(
        side="left",
        padx=10
    )


def show_prompt(parent, title, label_text, on_submit):
    """
    Small popup that asks for one line of text (new feature: Rule
    Engine Presets -- naming a preset before saving it). Same
    Toplevel/grab_set/button-row shape as show_confirm and
    show_note_dialog. Calls `on_submit(text)` only if the professor
    presses Save with a non-blank value; Cancel/closing the dialog
    does nothing.
    """

    prompt_window = ctk.CTkToplevel(parent)

    prompt_window.title(title)
    prompt_window.geometry("380x200")
    prompt_window.resizable(False, False)
    prompt_window.grab_set()

    ctk.CTkLabel(
        prompt_window,
        text=label_text,
        font=ctk.CTkFont(size=14, weight="bold"),
        wraplength=320
    ).pack(pady=(25, 10), padx=20)

    entry = ctk.CTkEntry(prompt_window)

    entry.pack(
        fill="x",
        padx=20,
        pady=(0, 10)
    )

    error_label = ctk.CTkLabel(
        prompt_window,
        text="",
        text_color="#FF6B6B"
    )

    error_label.pack(pady=(0, 5))

    def handle_save():

        text = entry.get().strip()

        if not text:
            error_label.configure(text="Please enter a name.")
            return

        prompt_window.destroy()
        on_submit(text)

    button_row = ctk.CTkFrame(
        prompt_window,
        fg_color="transparent"
    )

    button_row.pack(pady=(5, 15))

    ctk.CTkButton(
        button_row,
        text="Save",
        width=100,
        fg_color="#1F8F4C",
        hover_color="#27AE60",
        command=handle_save
    ).pack(
        side="left",
        padx=10
    )

    ctk.CTkButton(
        button_row,
        text="Cancel",
        width=100,
        fg_color="transparent",
        hover_color="#3a1f1f",
        border_color="#FF6B6B",
        border_width=1,
        text_color="#FF6B6B",
        command=prompt_window.destroy
    ).pack(
        side="left",
        padx=10
    )


def show_note_dialog(parent, initial_text, on_save):
    """
    Small popup for adding/editing a single photo's note (new
    feature: Photo Notes). Calls `on_save(text)` only if the
    professor presses Save; Cancel/closing the dialog discards any
    typed changes.
    """

    note_window = ctk.CTkToplevel(parent)

    note_window.title("Photo Note")
    note_window.geometry("420x280")
    note_window.resizable(False, False)
    note_window.grab_set()

    ctk.CTkLabel(
        note_window,
        text="Photo Note",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#7CFFB2"
    ).pack(pady=(20, 10))

    textbox = ctk.CTkTextbox(
        note_window,
        height=130
    )

    textbox.pack(
        fill="both",
        expand=True,
        padx=20,
        pady=(0, 15)
    )

    if initial_text:
        textbox.insert("1.0", initial_text)

    def handle_save():
        text = textbox.get("1.0", "end").strip()
        note_window.destroy()
        on_save(text)

    button_row = ctk.CTkFrame(
        note_window,
        fg_color="transparent"
    )

    button_row.pack(pady=(0, 15))

    ctk.CTkButton(
        button_row,
        text="Save",
        width=100,
        fg_color="#1F8F4C",
        hover_color="#27AE60",
        command=handle_save
    ).pack(
        side="left",
        padx=10
    )

    ctk.CTkButton(
        button_row,
        text="Cancel",
        width=100,
        fg_color="transparent",
        hover_color="#3a1f1f",
        border_color="#FF6B6B",
        border_width=1,
        text_color="#FF6B6B",
        command=note_window.destroy
    ).pack(
        side="left",
        padx=10
    )