import customtkinter as ctk
from PIL import Image

from . import theme
from .histogram_panel import HistogramPanel
from .widgets import show_note_dialog

# Space the preview must leave free for the histogram + note bar +
# margins, so the photo always fits inside the viewer.
RESERVED_HEIGHT = 270
RESERVED_WIDTH = 40
MAX_SOURCE_SIZE = 1600

# Zoom is relative to the "fit" view (1.0 = the whole photo fits in the
# viewer). It can go up to ZOOM_MAX_PIXEL_SCALE screen pixels per photo
# pixel (4x magnification), which is enough to check focus and noise.
ZOOM_STEP = 1.25
ZOOM_MAX_PIXEL_SCALE = 4.0

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

    Zoom (new feature): the strip above the photo has - / + / Fit /
    100% buttons; the mouse wheel zooms around the pointer, dragging
    pans a zoomed photo, and double-click toggles between Fit and a
    closer look. The normal (fit) view is drawn exactly as before from
    the downscaled copy; once zoomed in, the visible part is cropped
    from the FULL-resolution photo and resized once, so detail is not
    lost. Each new photo starts at Fit. Zoom only changes how the
    photo is drawn -- nothing about the grading is touched.
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

        # Zoom state: zoom 1.0 = fit. (_center_x, _center_y) is the
        # point of the full-resolution photo shown in the middle of
        # the viewer; it only matters while zoomed in.
        self.zoom = 1.0
        self._center_x = 0.0
        self._center_y = 0.0
        self._drag_start = None

        self.create_preview(on_drop)

        self.frame.bind("<Configure>", self.on_configure)

    def create_zoom_bar(self):
        """Small strip above the photo: - + Fit 100% and the zoom level."""

        bar = ctk.CTkFrame(self.frame, fg_color="transparent")

        bar.pack(
            side="top",
            fill="x",
            padx=14,
            pady=(10, 0)
        )

        theme.muted(bar, "Zoom", size=12).pack(side="left")

        self.zoom_out_button = theme.ghost_button(
            bar, "−", self.zoom_out, width=32, height=26
        )
        self.zoom_out_button.pack(side="left", padx=(8, 0))

        self.zoom_in_button = theme.ghost_button(
            bar, "+", self.zoom_in, width=32, height=26
        )
        self.zoom_in_button.pack(side="left", padx=(2, 0))

        theme.ghost_button(
            bar, "Fit", self.zoom_fit, width=40, height=26
        ).pack(side="left", padx=(2, 0))

        theme.ghost_button(
            bar, "100%", self.zoom_actual, width=48, height=26
        ).pack(side="left", padx=(2, 0))

        self.zoom_label = theme.muted(bar, "", size=12)
        self.zoom_label.pack(side="left", padx=(10, 0))

        theme.muted(
            bar,
            "Scroll to zoom • drag to pan • double-click to toggle",
            size=11
        ).pack(side="right")

    def create_preview(self, on_drop):

        self.histogram = HistogramPanel(self.frame)
        self.create_note_bar()
        self.create_zoom_bar()

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

        self.preview_label.bind("<MouseWheel>", self.on_mouse_wheel)
        self.preview_label.bind("<Button-4>", self.on_mouse_wheel)   # Linux
        self.preview_label.bind("<Button-5>", self.on_mouse_wheel)   # Linux
        self.preview_label.bind("<ButtonPress-1>", self.on_drag_start)
        self.preview_label.bind("<B1-Motion>", self.on_drag_move)
        self.preview_label.bind("<ButtonRelease-1>", self.on_drag_end)
        self.preview_label.bind("<Double-Button-1>", self.on_double_click)

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

        # Every photo starts at Fit.
        self.zoom = 1.0
        self._center_x = self.current_image.width / 2
        self._center_y = self.current_image.height / 2
        self._drag_start = None

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

        if self.zoom > 1.0:
            self.render_zoomed()
            return

        fit = self.available_size()

        self.update_zoom_label(fit)

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

    # -----------------------------------------
    # ZOOM
    # -----------------------------------------

    def fit_scale(self, available=None):
        """Screen pixels per photo pixel when the whole photo fits."""

        if self.current_image is None:
            return 1.0

        width, height = available or self.available_size()

        return min(
            width / self.current_image.width,
            height / self.current_image.height
        )

    def max_zoom(self, fit):
        """Highest zoom: ZOOM_MAX_PIXEL_SCALE pixels per photo pixel."""

        return max(1.0, ZOOM_MAX_PIXEL_SCALE / fit)

    def view_geometry(self, zoom, available=None):
        """
        What `zoom` shows: (scale, left, top, width, height) where
        scale is screen pixels per photo pixel and the rest is the
        visible box in full-resolution photo pixels, kept inside the
        photo around the current centre.
        """

        photo_w, photo_h = self.current_image.size
        view_w, view_h = available or self.available_size()

        scale = self.fit_scale((view_w, view_h)) * zoom

        width = min(view_w / scale, photo_w)
        height = min(view_h / scale, photo_h)

        left = min(max(self._center_x - width / 2, 0), photo_w - width)
        top = min(max(self._center_y - height / 2, 0), photo_h - height)

        return scale, left, top, width, height

    def render_zoomed(self, quick=False):
        """
        Draws the visible part of the full-resolution photo. `quick`
        uses cheaper resampling while the photo is being dragged; a
        full-quality redraw follows when the mouse is released.
        """

        available = self.available_size()
        scale, left, top, width, height = self.view_geometry(self.zoom, available)

        box = (
            round(left),
            round(top),
            min(round(left + width), self.current_image.width),
            min(round(top + height), self.current_image.height),
        )

        crop = self.current_image.crop(box)

        size = (
            max(1, round(crop.width * scale)),
            max(1, round(crop.height * scale)),
        )

        image = crop.resize(
            size,
            Image.Resampling.BILINEAR if quick else Image.Resampling.LANCZOS
        )

        self.image_tk = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=image.size
        )

        self.preview_label.configure(
            image=self.image_tk,
            text=""
        )

        self._last_fit = None

        self.update_zoom_label(available)

    def update_zoom_label(self, available=None):

        if self.current_image is None:
            self.zoom_label.configure(text="")
            return

        percent = round(self.fit_scale(available) * self.zoom * 100)

        self.zoom_label.configure(
            text=f"{percent}%" + ("  (fit)" if self.zoom <= 1.0 else "")
        )

    def set_zoom(self, zoom, anchor=None, quick=False):
        """
        Zoom to `zoom` (clamped). `anchor` is the pointer position
        (x, y) inside the preview: the photo point under it stays
        under it while zooming. Without one, the centre stays put.
        """

        if self._source is None or self.current_image is None:
            return

        available = self.available_size()
        zoom = min(max(zoom, 1.0), self.max_zoom(self.fit_scale(available)))

        if zoom == self.zoom:
            return

        if anchor is not None:

            # Photo point under the pointer before the change ...
            point = self.photo_point_at(*anchor, available)

            self.zoom = zoom

            if zoom > 1.0 and point is not None:
                # ... and the centre that keeps it under the pointer.
                scale, _, _, width, height = self.view_geometry(zoom, available)

                label_w = self.preview_label.winfo_width()
                label_h = self.preview_label.winfo_height()

                offset_x = anchor[0] - label_w / 2
                offset_y = anchor[1] - label_h / 2

                self._center_x = point[0] - offset_x / scale
                self._center_y = point[1] - offset_y / scale
        else:
            self.zoom = zoom

        if self.zoom <= 1.0:
            self._center_x = self.current_image.width / 2
            self._center_y = self.current_image.height / 2
            self._last_fit = None

        self.render_preview()

    def photo_point_at(self, x, y, available):
        """
        The full-resolution photo point shown at preview position
        (x, y), or None if the preview has no real size yet.
        """

        label_w = self.preview_label.winfo_width()
        label_h = self.preview_label.winfo_height()

        if label_w <= 1 or label_h <= 1:
            return None

        scale, left, top, width, height = self.view_geometry(self.zoom, available)

        # The (cropped) image is centred in the preview label.
        shown_w = width * scale
        shown_h = height * scale

        offset_x = x - (label_w - shown_w) / 2
        offset_y = y - (label_h - shown_h) / 2

        offset_x = min(max(offset_x, 0), shown_w)
        offset_y = min(max(offset_y, 0), shown_h)

        return left + offset_x / scale, top + offset_y / scale

    def zoom_in(self):
        self.set_zoom(self.zoom * ZOOM_STEP)

    def zoom_out(self):
        self.set_zoom(self.zoom / ZOOM_STEP)

    def zoom_fit(self):
        """Back to the normal view: the whole photo, centred."""

        self.set_zoom(1.0)

    def zoom_actual(self):
        """100%: one photo pixel per screen pixel (or as close as allowed)."""

        if self.current_image is None:
            return

        self.set_zoom(1.0 / self.fit_scale())

    def on_mouse_wheel(self, event):

        if self._source is None:
            return

        # Windows/macOS give event.delta; Linux sends Button-4/5.
        zoom_in = event.num == 4 or getattr(event, "delta", 0) > 0

        factor = ZOOM_STEP if zoom_in else 1 / ZOOM_STEP

        self.set_zoom(self.zoom * factor, anchor=(event.x, event.y))

    def on_double_click(self, event):

        if self._source is None:
            return

        if self.zoom > 1.0:
            self.zoom_fit()
        else:
            self.set_zoom(
                min(2.0, self.max_zoom(self.fit_scale())),
                anchor=(event.x, event.y)
            )

    def on_drag_start(self, event):

        if self.zoom > 1.0:
            self._drag_start = (event.x, event.y, self._center_x, self._center_y)

    def on_drag_move(self, event):

        if self._drag_start is None or self.zoom <= 1.0:
            return

        start_x, start_y, center_x, center_y = self._drag_start

        scale = self.fit_scale() * self.zoom

        self._center_x = center_x - (event.x - start_x) / scale
        self._center_y = center_y - (event.y - start_y) / scale

        self.render_zoomed(quick=True)

    def on_drag_end(self, event):

        if self._drag_start is not None:
            self._drag_start = None
            self.render_zoomed()

