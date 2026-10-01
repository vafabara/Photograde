import json
from pathlib import Path

from ..core.rules import RuleEngineConfig
from .class_storage import CLASSES_DIR

PRESETS_FILE = CLASSES_DIR / "rule_presets.json"


class RulePresetError(Exception):
    """Raised when a preset operation fails."""


def load_presets():
    """
    Returns {name: RuleEngineConfig}. A missing or corrupt file is
    treated as "no presets saved yet" rather than an error -- same
    tolerance class_storage.load_all_classes() has for a bad class
    folder.
    """

    if not PRESETS_FILE.exists():
        return {}

    try:
        with open(PRESETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        return {
            name: RuleEngineConfig.from_dict(config_data)
            for name, config_data in data.items()
        }

    except (json.JSONDecodeError, OSError, KeyError):
        return {}


def _write_presets(presets):
    """
    Persist the full {name: RuleEngineConfig} dict back to disk.
    Shared by save_preset / delete_preset / rename_preset so the
    on-disk format is defined in exactly one place.
    """

    try:
        CLASSES_DIR.mkdir(parents=True, exist_ok=True)

        data = {
            preset_name: preset_config.to_dict()
            for preset_name, preset_config in presets.items()
        }

        with open(PRESETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    except OSError as error:
        raise RulePresetError(f"Could not save preset: {error}")


def save_preset(name, config):
    """
    Save/overwrite one named preset (`config` is a RuleEngineConfig)
    and persist the full preset file back to disk immediately, so
    the Rule Engine screen's preset list is accurate the moment it's
    reloaded.
    """

    presets = load_presets()
    presets[name] = config

    _write_presets(presets)


def delete_preset(name):
    """
    Remove one named preset and persist the rest unchanged. A name
    that isn't there is treated as already deleted (no error, and
    nothing is rewritten).
    """

    presets = load_presets()

    if name not in presets:
        return

    del presets[name]

    _write_presets(presets)


def rename_preset(old_name, new_name):
    """
    Rename a preset, keeping its RuleEngineConfig and its position in
    the list exactly as they were. Raises RulePresetError if the new
    name is blank, the old preset no longer exists, or another preset
    already uses the new name (so a rename can never silently
    overwrite a different preset).
    """

    new_name = new_name.strip()

    if not new_name:
        raise RulePresetError("Please enter a name.")

    presets = load_presets()

    if old_name not in presets:
        raise RulePresetError("That preset no longer exists.")

    if new_name == old_name:
        return

    if new_name in presets:
        raise RulePresetError(f'A preset named "{new_name}" already exists.')

    renamed = {
        (new_name if name == old_name else name): config
        for name, config in presets.items()
    }

    _write_presets(renamed)
