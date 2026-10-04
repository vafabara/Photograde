"""
Persistence for application Settings (new feature: Settings).

Mirrors storage/rule_presets.py: one small JSON file, no database.
It lives next to rule_presets.json (inside classes/), which is
already git-ignored. load_all_classes() only looks at sub-folders,
so a settings.json file there is never mistaken for a class.

Settings are *defaults and preferences only*. They are never written
into a ClassRecord, so changing them cannot alter an existing class.
"""

import json
from dataclasses import dataclass, asdict

from ..core.tolerance import MAX_TOLERANCE_PERCENT
from .class_storage import CLASSES_DIR

SETTINGS_FILE = CLASSES_DIR / "settings.json"

THEMES = ("Dark", "Light", "System")
EXPORT_FORMATS = ("Excel", "CSV", "JSON")

# Tolerance is edited as a percentage (15 = 15%) but the Rule Engine
# stores a fraction (0.15), the same unit as MAX_TOLERANCE_PERCENT.
MIN_TOLERANCE_PERCENT = 0
MAX_TOLERANCE_SETTING = 50


class SettingsStorageError(Exception):
    """Raised when settings cannot be saved."""


@dataclass
class AppSettings:
    theme: str = "Dark"
    system_weight: int = 50
    teacher_weight: int = 50
    tolerance_percent: float = MAX_TOLERANCE_PERCENT * 100
    export_format: str = "Excel"
    confirm_delete: bool = True
    show_exif: bool = True

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """
        Builds settings from saved JSON, field by field: a missing or
        invalid value falls back to its default instead of failing,
        so an old or hand-edited file can never break startup.
        """

        defaults = cls()

        theme = data.get("theme")
        if theme not in THEMES:
            theme = defaults.theme

        export_format = data.get("export_format")
        if export_format not in EXPORT_FORMATS:
            export_format = defaults.export_format

        system = data.get("system_weight")
        teacher = data.get("teacher_weight")
        valid_split = (
            isinstance(system, int) and isinstance(teacher, int)
            and not isinstance(system, bool) and not isinstance(teacher, bool)
            and system >= 0 and teacher >= 0 and system + teacher == 100
        )
        if not valid_split:
            system, teacher = defaults.system_weight, defaults.teacher_weight

        tolerance = data.get("tolerance_percent")
        if (
            isinstance(tolerance, bool)
            or not isinstance(tolerance, (int, float))
            or not MIN_TOLERANCE_PERCENT <= tolerance <= MAX_TOLERANCE_SETTING
        ):
            tolerance = defaults.tolerance_percent

        confirm_delete = data.get("confirm_delete")
        if not isinstance(confirm_delete, bool):
            confirm_delete = defaults.confirm_delete

        show_exif = data.get("show_exif")
        if not isinstance(show_exif, bool):
            show_exif = defaults.show_exif

        return cls(
            theme=theme,
            system_weight=system,
            teacher_weight=teacher,
            tolerance_percent=tolerance,
            export_format=export_format,
            confirm_delete=confirm_delete,
            show_exif=show_exif,
        )


def load_settings():
    """Missing or corrupt file -> default settings, never an error."""

    if not SETTINGS_FILE.exists():
        return AppSettings()

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return AppSettings.from_dict(data)

    except (json.JSONDecodeError, OSError, AttributeError):
        return AppSettings()


def save_settings(settings):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, indent=2)

    except OSError as error:
        raise SettingsStorageError(f"Could not save settings: {error}")