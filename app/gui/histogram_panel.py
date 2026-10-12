from tkinter import Canvas

from ..core.histogram import get_histogram
from . import theme

CHANNEL_COLORS = {
    "r": "#FF6B6B",
    "g": "#5CE08F",
    "b": "#5CA8FF",
}


class HistogramPanel:
    """
    RGB histogram drawn on a plain tkinter Canvas. Same API as
    before (`HistogramPanel(parent)`, `.update(image)`); it now also
    redraws itself when the window is resized instead of keeping a
    stale width.
    """

    def __init__(self, parent):

        self.histogram = None

        self.canvas = Canvas(
            parent,
            height=110,
            bg=theme.BG,
            highlightthickness=1,
            highlightbackground=theme.BORDER
        )

        self.canvas.pack(
            side="bottom",
            fill="x",
            padx=14,
            pady=(0, 14)
        )

        self.canvas.bind("<Configure>", lambda event: self.draw())

    def update(self, image):

        self.histogram = get_histogram(image)

        self.draw()

    def draw(self):

        self.canvas.delete("all")

        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if width <= 1 or height <= 1:
            width, height = 400, 110

        # faint quarter guides
        for fraction in (0.25, 0.5, 0.75):
            x = width * fraction
            self.canvas.create_line(x, 0, x, height, fill=theme.SURFACE_ALT)

        self.canvas.create_text(
            8,
            6,
            text="HISTOGRAM",
            anchor="nw",
            fill=theme.TEXT_FAINT,
            font=("TkDefaultFont", 8, "bold")
        )

        if self.histogram is None:
            return

        for channel, color in CHANNEL_COLORS.items():

            values = self.histogram[channel]
            max_value = max(values) or 1

            points = []

            for i, value in enumerate(values):
                x = i * (width / 256)
                y = height - (value / max_value) * (height - 4)

                points.append(x)
                points.append(y)

            if len(points) >= 4:
                self.canvas.create_line(
                    *points,
                    fill=color,
                    width=1,
                    smooth=True
                )
