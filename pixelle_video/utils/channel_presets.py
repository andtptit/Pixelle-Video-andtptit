# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
[PIXELLE-CUSTOM] Channel Preset storage

Minimal-scope preset: saves/loads TTS voice+speed, TTS workflow, media
workflow (per image/video source+selection), image prompt prefix,
narration style notes, and scene-grouping settings, so users running
multiple channels can switch between them without manually re-picking
these settings each time.

Deliberately out of scope (documented limitation, not a bug):
- Frame template (chosen via the template gallery) is NOT included.
- Per-template custom parameters are NOT included.
"""

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

PRESET_DIR = Path("channel_presets")

# Fixed session_state keys this preset covers
PRESET_KEYS = [
    "tts_inference_mode",
    "tts_local_voice",
    "tts_local_speed",
    "tts_workflow_select",
    "standard_image_workflow_source",
    "standard_image_workflow_source_select",
    "standard_video_workflow_source",
    "standard_video_workflow_source_select",
    "style_prompt_prefix",
    "narration_style_notes",
    "enable_pause_dash",
    "enable_scene_grouping",
    "target_image_count",
    "std_n_scenes",
    "preview_title",
    "preview_image",
    "preview_text",
]

# Per-template custom parameter widgets use dynamic keys (one per param name),
# e.g. "video_custom_title_color". Any session_state key with this prefix is
# captured/restored alongside the fixed PRESET_KEYS above. Only meaningful if
# the same frame template is selected again after loading the preset (frame
# template selection itself is out of scope for this preset).
DYNAMIC_KEY_PREFIXES = ["video_custom_"]


def _safe_filename(name: str) -> str:
    name = name.strip()
    name = re.sub(r"[^\w\-\. À-￿]", "_", name)
    # [PIXELLE-CUSTOM] Canonicalize to NFC. exFAT stores filenames byte-exact
    # (unlike APFS/HFS+, which compare Unicode-normalization-insensitively),
    # and macOS sometimes writes accented filenames as NFD (e.g. Vietnamese
    # "ê" as "e" + combining circumflex). Without normalizing, a freshly
    # constructed NFC path can silently fail to match an NFD file already on
    # disk (or vice versa), causing spurious FileNotFoundError / phantom
    # duplicate entries. See _find_preset_file() for the matching lookup.
    name = unicodedata.normalize("NFC", name)
    return name or "preset"


def _find_preset_file(name: str) -> Optional[Path]:
    """
    [PIXELLE-CUSTOM] Find the real on-disk path for `name`, matching by
    NFC-normalized filename regardless of which Unicode normalization form is
    actually stored on disk. Returns the *actual* matched path (not a freshly
    constructed guess), so callers can safely open/overwrite/delete it.
    """
    if not PRESET_DIR.exists():
        return None
    target = f"{_safe_filename(name)}.json"
    for entry in os.scandir(PRESET_DIR):
        if entry.name.startswith("._"):
            continue
        if unicodedata.normalize("NFC", entry.name) == target:
            return Path(entry.path)
    return None


def list_presets() -> List[str]:
    if not PRESET_DIR.exists():
        return []
    # Filter out macOS AppleDouble shadow files (e.g. "._foo.json") that some
    # filesystems (exFAT/network shares) generate alongside the real file.
    names = []
    for entry in os.scandir(PRESET_DIR):
        if entry.name.startswith("._") or not entry.name.endswith(".json"):
            continue
        names.append(unicodedata.normalize("NFC", entry.name)[:-len(".json")])
    return sorted(names)


def load_preset(name: str) -> Dict[str, Any]:
    path = _find_preset_file(name)
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_preset(name: str, values: Dict[str, Any]) -> str:
    PRESET_DIR.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(name)
    # Overwrite the existing file in whatever form it's actually stored in,
    # instead of blindly writing a fresh NFC path (which would leave a stale
    # duplicate behind if the existing file happens to be stored as NFD).
    path = _find_preset_file(name) or (PRESET_DIR / f"{filename}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(values, f, indent=2, ensure_ascii=False)
    return filename


def delete_preset(name: str) -> bool:
    path = _find_preset_file(name)
    if path and path.exists():
        path.unlink()
        return True
    return False
