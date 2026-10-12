import customtkinter as ctk

from . import theme
from .histogram_panel import HistogramPanel
from .widgets import show_note_dialog

# Space the preview must leave free for the histogram + note bar +
# margins, so the photo always fits inside the viewer.
RESERVED_HEIGHT = 230
RESERVED_WIDTH = 40
MAX_SOURCE_SIZE = 1600

PLACEHOLDER_TEXT = "No image selected\n\nDrag & drop a photo here"


class ImageViewer:
    """
    Left side of the grading screen: the photograph (scaled to fit
    the available space and re-fitted on window resize), a note bar
    for the current photo, and the RGB histogram.

    Same public contract as before: `ImageViewer(parent, on_drop,
    on_note_save)`, `.update(image, image_record)`. The note itself
    is persisted by App into that photo's ClassPhotoEntry -- this
    widget only renders it and reports edits via on_note_save.
    """

    def __init__(self, parent, on_drop=None, on_note_save=None):

        self.on_note_save = on_note_save
        self.image_record = None

        self.frame = ctk.CTkFrame(
            parent,
            corner_radius=12,
            fg_color=theme.SURFACE,
            border_width=1,
            border_color=theme.BORDER
        )

        self.frame.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.current_image = None
        self.image_tk = None

        self._source = None          # downscaled copy used for display
        self._last_fit = None
        self._resize_job = None

        self.create_preview(on_drop)

        self.frame.bind("<Configure>", self.on_configure)

    def create_preview(self, on_drop):

        self.histogram = HistogramPanel(self.frame)
        self.create_note_bar()

        self.preview_label = ctk.CTkLabel(
            self.frame,
            text=PLACEHOLDER_TEXT,
            text_color=theme.TEXT_FAINT,
            font=theme.font(16)
        )

        self.preview_label.pack(
            fill="both",
            expand=True,
            padx=16,
            pady=16
        )

        if on_drop:
            self.frame.drop_target_register("DND_Files")
            self.frame.dnd_bind(
                "<<Drop>>",
                on_drop
            )

    def create_note_bar(self):
        """
        Clicking it opens a small dialog to add/edit a note for
        whichever photo is currently on screen.
        """

        self.note_bar = ctk.CTkButton(
            self.frame,
            text="Add note...",
            anchor="w",
            height=36,
            corner_radius=8,
            font=theme.font(13),
            fg_color=theme.SURFACE_ALT,
            hover_color=theme.SURFACE_HOVER,
            border_width=1,
            border_color=theme.BORDER,
            text_color=theme.TEXT_MUTED,
            command=self.open_note_dialog
        )

        self.note_bar.pack(
            side="bottom",
            fill="x",
            padx=14,
            pady=(0, 10)
        )

    def open_note_dialog(self):

        if self.image_record is None:
            return

        current_note = self.image_record.note or ""

        def handle_save(new_note):

            self.image_record.note = new_note
            self.refresh_note_bar()

            if self.on_note_save:
                self.on_note_save(self.image_record, new_note)

        show_note_dialog(
            self.frame,
            current_note,
            on_save=handle_save
        )

    def refresh_note_bar(self):

        if self.image_record and self.image_record.note:
            preview = self.image_record.note.strip().splitlines()[0][:60]
            self.note_bar.configure(
                text=f"Note:  {preview}",
                text_color=theme.TEXT
            )
        else:
            self.note_bar.configure(
                text="Add note...",
                text_color=theme.TEXT_MUTED
            )

    # -----------------------------------------
    # RENDERING
    # -----------------------------------------

    def update(self, image, image_record=None):

        self.image_record = image_record

        self.current_image = image.copy()

        # Keep a bounded copy for display so re-fitting on resize
        # stays fast even for very large photos.
        self._source = image.copy()
        self._source.thumbnail((MAX_SOURCE_SIZE, MAX_SOURCE_SIZE))

        self._last_fit = None
        self.render_preview()

        self.histogram.update(self.current_image)
        self.refresh_note_bar()

    def available_size(self):

        width = self.frame.winfo_width()
        height = self.frame.winfo_height()

        if width <= 1 or height <= 1:
            return 500, 500

        return (
            max(width - RESERVED_WIDTH, 200),
            max(height - RESERVED_HEIGHT, 200)
        )

    def render_preview(self):

        if self._source is None:
            return

        fit = self.available_size()

        if self._last_fit and all(
            abs(a - b) < 8 for a, b in zip(fit, self._last_fit)
        ):
            return

        self._last_fit = fit

        image = self._source.copy()
        image.thumbnail(fit)

        self.image_tk = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size
        )

        self.preview_label.configure(
            image=self.image_tk,
            text=""
        )

    def on_configure(self, event=None):
        """Debounced re-fit when the window is resized."""

        if self._source is None:
            return

        if self._resize_job is not None:
            self.frame.after_cancel(self._resize_job)

        self._resize_job = self.frame.after(150, self.render_preview)
