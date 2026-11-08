"""
Reading photos from the system clipboard (new feature: paste an
image with Ctrl+V when adding a student's photos).

Uses Pillow's ImageGrab, so no new dependency: it returns a bitmap
(a screenshot, "Copy image" in a browser, ...) or, on some systems,
the list of files that were copied in the file manager.

No CustomTkinter dependency here (spec section 8) -- same rule as
the rest of core/.
"""

from pathlib import Path

from PIL import Image, ImageGrab


class ClipboardError(ValueError):
    """Raised when the clipboard cannot be read at all."""


def grab_clipboard_photos():
    """
    Look at the clipboard and return what photo content it holds:

      ("image", PIL.Image)   -- a bitmap
      ("files", [Path, ...]) -- file paths copied from a file manager
      None                   -- nothing usable (empty, or text etc.)

    Raises ClipboardError (with a message ready to show) only when
    the clipboard cannot be read on this system, e.g. a Linux
    desktop without xclip / wl-clipboard.
    """

    try:
        content = ImageGrab.grabclipboard()

    except NotImplementedError:
        raise ClipboardError(
            "Pasting images is not supported on this system. On Linux, "
            "install xclip (X11) or wl-clipboard (Wayland)."
        )

    except Exception:
        raise ClipboardError("Could not read the clipboard.")

    if isinstance(content, Image.Image):
        return ("image", content)

    if isinstance(content, (list, tuple)) and content:
        return ("files", [Path(item) for item in content])

    return None
