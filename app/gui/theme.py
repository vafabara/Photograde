"""
PhotoGrade design system (GUI only).

Every colour, font and reusable widget style lives here, so every
screen looks like the same application and a visual change is made
in one place instead of in ten files.

Direction: a calm "darkroom" look -- near-black graphite surfaces so
the student's photograph stays the brightest thing on screen, one
warm amber accent for primary actions and progress, and the
traffic-light colours reserved for their real meaning (Rule Engine
status: green / yellow / red).

No business logic in this module -- it only builds widgets.
"""

import customtkinter as ctk

# -----------------------------------------
# PALETTE
# -----------------------------------------

BG = "#0E1014"             # window background
SURFACE = "#161920"        # cards / panels
SURFACE_ALT = "#1D212A"    # inputs, rows inside cards
SURFACE_HOVER = "#262B37"  # hover state for rows / buttons
BORDER = "#2B303B"

TEXT = "#E9ECF2"
TEXT_MUTED = "#9099AB"
TEXT_FAINT = "#6B7385"

ACCENT = "#F5A524"        # primary action / progress / highlights
ACCENT_HOVER = "#FFB840"
ACCENT_FG = "#1A1203"     # text on top of ACCENT (high contrast)

SUCCESS = "#4ADE80"
WARNING = "#FACC15"
DANGER = "#F87171"

# Dark tints used behind coloured text (pills, banners)
TINTS = {
    SUCCESS: "#14301F",
    WARNING: "#33290C",
    DANGER: "#2E181A",
    ACCENT: "#33240A",
    TEXT_MUTED: SURFACE_ALT,
}


# -----------------------------------------
# BASICS
# -----------------------------------------

def apply_theme():
    """Call once, before the root window is created."""

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")


def font(size=13, weight="normal"):
    return ctk.CTkFont(size=size, weight=weight)


def label(parent, text="", size=13, weight="normal", color=TEXT, **kwargs):
    return ctk.CTkLabel(
        parent,
        text=text,
        font=font(size, weight),
        text_color=color,
        **kwargs
    )


def muted(parent, text="", size=12, **kwargs):
    return label(parent, text, size=size, color=TEXT_MUTED, **kwargs)


def page(parent, padx=32, pady=24):
    """The padded container every full-screen view builds into."""

    frame = ctk.CTkFrame(parent, fg_color="transparent")

    frame.pack(
        fill="both",
        expand=True,
        padx=padx,
        pady=pady
    )

    return frame


def card(parent, **kwargs):
    options = dict(
        fg_color=SURFACE,
        corner_radius=12,
        border_width=1,
        border_color=BORDER,
    )
    options.update(kwargs)

    return ctk.CTkFrame(parent, **options)


def divider(parent):
    return ctk.CTkFrame(parent, height=1, fg_color=BORDER)


# -----------------------------------------
# BUTTONS  (primary > secondary > ghost; danger for destructive)
# -----------------------------------------

def primary_button(parent, text, command=None, width=140, height=38, **kwargs):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=8,
        font=font(13, "bold"),
        fg_color=ACCENT,
        hover_color=ACCENT_HOVER,
        text_color=ACCENT_FG,
        **kwargs
    )


def secondary_button(parent, text, command=None, width=120, height=38, **kwargs):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=8,
        font=font(13),
        fg_color=SURFACE_ALT,
        hover_color=SURFACE_HOVER,
        border_width=1,
        border_color=BORDER,
        text_color=TEXT,
        **kwargs
    )


def ghost_button(parent, text, command=None, width=80, height=30, **kwargs):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=8,
        font=font(12),
        fg_color="transparent",
        hover_color=SURFACE_HOVER,
        text_color=TEXT_MUTED,
        **kwargs
    )


def danger_button(parent, text, command=None, width=80, height=30, **kwargs):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        width=width,
        height=height,
        corner_radius=8,
        font=font(12),
        fg_color="transparent",
        hover_color=TINTS[DANGER],
        text_color=DANGER,
        **kwargs
    )


# -----------------------------------------
# INPUTS
# -----------------------------------------

def text_entry(parent, **kwargs):
    """CTkEntry with the app style and a visible (amber) focus ring."""

    options = dict(
        height=36,
        corner_radius=8,
        font=font(13),
        fg_color=SURFACE_ALT,
        border_width=1,
        border_color=BORDER,
        text_color=TEXT,
        placeholder_text_color=TEXT_FAINT,
    )
    options.update(kwargs)

    entry = ctk.CTkEntry(parent, **options)

    entry.bind("<FocusIn>", lambda event: entry.configure(border_color=ACCENT))
    entry.bind("<FocusOut>", lambda event: entry.configure(border_color=BORDER))

    return entry


def error_label(parent, **kwargs):
    return label(parent, "", size=12, color=DANGER, anchor="w", **kwargs)


# -----------------------------------------
# SMALL BUILDING BLOCKS
# -----------------------------------------

def pill(parent, text, color=TEXT_MUTED):
    """Small rounded status tag. `color` is the text colour."""

    return ctk.CTkLabel(
        parent,
        text=f"  {text}  ",
        font=font(11, "bold"),
        text_color=color,
        fg_color=TINTS.get(color, SURFACE_ALT),
        corner_radius=10,
        height=22,
    )


def progress_bar(parent, value=0.0, width=120, color=ACCENT):
    bar = ctk.CTkProgressBar(
        parent,
        width=width,
        height=6,
        corner_radius=3,
        fg_color=BORDER,
        progress_color=color,
    )

    bar.set(value)

    return bar


def stat_tile(parent, caption, value, highlight=False):
    """Big number with a small caption underneath (summary rows)."""

    tile = ctk.CTkFrame(
        parent,
        fg_color=SURFACE_ALT,
        corner_radius=10
    )

    label(
        tile,
        value,
        size=22,
        weight="bold",
        color=ACCENT if highlight else TEXT
    ).pack(
        padx=20,
        pady=(12, 0)
    )

    muted(tile, caption).pack(
        padx=20,
        pady=(0, 12)
    )

    return tile


def screen_header(parent, title, subtitle=None, on_back=None, back_text="Back", back_width=96):
    """
    Title (+ optional subtitle) with an optional Back button on the
    left. Returns the header frame so a screen can pack extra
    actions on its right side.
    """

    header = ctk.CTkFrame(parent, fg_color="transparent")

    header.pack(
        fill="x",
        pady=(0, 20)
    )

    if on_back:
        secondary_button(
            header,
            f"←  {back_text}",
            on_back,
            width=back_width,
            height=34
        ).pack(
            side="left",
            padx=(0, 16)
        )

    text_column = ctk.CTkFrame(header, fg_color="transparent")

    text_column.pack(side="left")

    label(
        text_column,
        title,
        size=24,
        weight="bold",
        anchor="w"
    ).pack(anchor="w")

    if subtitle:
        muted(
            text_column,
            subtitle,
            size=13,
            anchor="w"
        ).pack(anchor="w")

    return header


SETUP_STEPS = ["Class", "Students", "Photos", "Rules"]


def setup_steps(parent, current):
    """
    Slim step indicator for the class-creation flow
    (1 Class > 2 Students > 3 Photos > 4 Rules). `current` is 1-based.
    """

    row = ctk.CTkFrame(parent, fg_color="transparent")

    row.pack(
        anchor="w",
        pady=(0, 16)
    )

    for number, name in enumerate(SETUP_STEPS, start=1):

        if number == current:
            color, weight = ACCENT, "bold"
        elif number < current:
            color, weight = TEXT, "normal"
        else:
            color, weight = TEXT_FAINT, "normal"

        label(
            row,
            f"{number}  {name}",
            size=12,
            weight=weight,
            color=color
        ).pack(side="left")

        if number < len(SETUP_STEPS):
            label(
                row,
                "   ›   ",
                size=12,
                color=TEXT_FAINT
            ).pack(side="left")

    return row


def make_clickable(widgets, command, target=None, normal=SURFACE_ALT, hover=SURFACE_HOVER):
    """
    Make a group of widgets behave like one clickable row: any click
    on them calls `command()`, and `target` (the row frame) gets a
    hover highlight. Buttons placed inside the row are simply left
    out of `widgets`, so they keep their own behaviour.
    """

    def pointer_inside():

        if target is None:
            return False

        try:
            x, y = target.winfo_pointerxy()
            under = target.winfo_containing(x, y)
        except (KeyError, Exception):
            return False

        while under is not None:
            if under is target:
                return True
            under = getattr(under, "master", None)

        return False

    def on_enter(event=None):
        if target is not None:
            target.configure(fg_color=hover)

    def on_leave(event=None):
        if target is not None and not pointer_inside():
            target.configure(fg_color=normal)

    for widget in widgets:
        widget.bind("<Button-1>", lambda event: command())
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
