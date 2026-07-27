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
[PIXELLE-CUSTOM] Channel Preset UI (reduced scope)

Save/load a named preset covering: TTS voice+speed, TTS workflow,
image/video generation workflow (source+selection), prompt prefix,
number of scenes, and per-template custom parameters (dynamic keys).

NOT covered (documented limitation): frame template selection itself
(template gallery) — pick the same template manually after loading a
preset for its custom parameters to actually apply.
"""

import streamlit as st

from web.i18n import tr
from pixelle_video.utils.channel_presets import (
    PRESET_KEYS,
    DYNAMIC_KEY_PREFIXES,
    list_presets,
    load_preset,
    save_preset,
    delete_preset,
)


_PENDING_KEY = "_channel_preset_pending"  # [PIXELLE-CUSTOM]


def apply_pending_channel_preset():
    """
    [PIXELLE-CUSTOM] Must be called at the very top of the page script, before
    ANY widget (in any column/section) is instantiated for this run.

    Why: Streamlit raises an exception if you assign st.session_state[key]
    for a widget that has *already* been instantiated earlier in the same
    script run. render_channel_preset_section() lives in the middle column,
    which renders AFTER the left column (e.g. the n_scenes slider) — so
    setting those keys directly from the Load button handler would crash.
    Instead, Load just stages the data here; this function applies it on
    the following rerun, before the left column (or anything else) runs.
    """
    pending = st.session_state.pop(_PENDING_KEY, None)
    if pending:
        for key, value in pending["values"].items():
            st.session_state[key] = value
        _queue_toast("success", tr("channel_preset.load_success", name=pending["name"]))

    if st.session_state.pop("_channel_preset_reset_select", None):
        st.session_state["channel_preset_select"] = "—"


_TOAST_KEY = "_channel_preset_toast"  # [PIXELLE-CUSTOM]


def _queue_toast(kind: str, message: str):
    """
    [PIXELLE-CUSTOM] Stage a success/warning message to show on the NEXT run.

    Why: calling st.success(...) immediately before st.rerun() in the same
    script run almost never gets a chance to paint before the rerun wipes it
    out, so the user sees no confirmation at all (looks like the button did
    nothing, even though the action — save/edit/delete — actually succeeded).
    """
    st.session_state[_TOAST_KEY] = {"kind": kind, "message": message}


def _show_pending_toast():
    toast = st.session_state.pop(_TOAST_KEY, None)
    if toast:
        (st.success if toast["kind"] == "success" else st.warning)(toast["message"])


def render_channel_preset_section():
    """Render the Channel Preset save/load section (call before TTS/style widgets)."""
    with st.container(border=True):
        st.markdown(f"**{tr('channel_preset.section_title')}**")
        st.caption(tr("channel_preset.scope_note"))
        _show_pending_toast()

        presets = list_presets()
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            selected = st.selectbox(
                tr("channel_preset.select_label"),
                options=["—"] + presets,
                key="channel_preset_select",
                label_visibility="collapsed",
            )
        with col2:
            load_clicked = st.button(
                tr("channel_preset.load_button"),
                key="channel_preset_load_btn",
                use_container_width=True,
                disabled=(selected == "—"),
            )
        with col3:
            # [PIXELLE-CUSTOM] Edit = overwrite the selected preset with whatever
            # is currently set in the widgets above (no need to retype its name).
            edit_clicked = st.button(
                tr("channel_preset.edit_button"),
                key="channel_preset_edit_btn",
                use_container_width=True,
                disabled=(selected == "—"),
            )
        with col4:
            delete_clicked = st.button(
                tr("channel_preset.delete_button"),
                key="channel_preset_delete_btn",
                use_container_width=True,
                disabled=(selected == "—"),
            )

        if load_clicked and selected != "—":
            data = load_preset(selected)
            # [PIXELLE-CUSTOM] Stage for apply_pending_channel_preset() to apply
            # on the next rerun, rather than setting session_state here directly
            # (see apply_pending_channel_preset docstring for why).
            st.session_state[_PENDING_KEY] = {"name": selected, "values": data}
            st.rerun()

        if edit_clicked and selected != "—":
            values = _collect_current_values()
            save_preset(selected, values)
            _queue_toast("success", tr("channel_preset.edit_success", name=selected))
            st.rerun()

        if delete_clicked and selected != "—":
            st.session_state["cp_confirm_delete_preset"] = selected
            st.rerun()

        if st.session_state.get("cp_confirm_delete_preset") == selected and selected != "—":
            st.warning(tr("channel_preset.delete_confirm", name=selected))
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button(tr("channel_preset.delete_confirm_button"), key="cp_preset_delete_confirm_btn", use_container_width=True, type="primary"):
                    delete_preset(selected)
                    st.session_state.pop("cp_confirm_delete_preset", None)
                    # [PIXELLE-CUSTOM] Can't set "channel_preset_select" here — that
                    # widget already rendered earlier in this same run. Stage the
                    # reset for apply_pending_channel_preset() to apply next run.
                    st.session_state["_channel_preset_reset_select"] = True
                    _queue_toast("success", tr("channel_preset.delete_success", name=selected))
                    st.rerun()
            with cancel_col:
                if st.button(tr("channel_preset.delete_cancel_button"), key="cp_preset_delete_cancel_btn", use_container_width=True):
                    st.session_state.pop("cp_confirm_delete_preset", None)
                    st.rerun()

        with st.expander(tr("channel_preset.save_expander_title"), expanded=False):
            new_name = st.text_input(
                tr("channel_preset.name_label"),
                key="channel_preset_new_name",
            )
            if st.button(tr("channel_preset.save_button"), key="channel_preset_save_btn", use_container_width=True):
                if not new_name.strip():
                    st.warning(tr("channel_preset.name_required"))
                else:
                    saved_name = save_preset(new_name, _collect_current_values())
                    _queue_toast("success", tr("channel_preset.save_success", name=saved_name))
                    st.rerun()


def _collect_current_values() -> dict:
    """[PIXELLE-CUSTOM] Snapshot current widget values covered by the preset."""
    values = {key: st.session_state.get(key) for key in PRESET_KEYS if key in st.session_state}
    # Capture dynamic per-template custom parameter widgets too.
    for state_key, state_value in st.session_state.items():
        if any(state_key.startswith(prefix) for prefix in DYNAMIC_KEY_PREFIXES):
            values[state_key] = state_value
    return values
