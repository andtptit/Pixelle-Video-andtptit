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
Content input components for web UI (left column)
"""

import streamlit as st

from web.i18n import tr
from web.utils.async_helpers import get_project_version, run_async


# [PIXELLE-CUSTOM] Script Preview & Edit — lets the user generate the narration
# script alone (cheap: 1 LLM call, no image/video/TTS cost) and hand-edit it
# before committing to full video generation.
async def _generate_script_preview(pixelle_video, topic: str, n_scenes: int):
    from pixelle_video.utils.content_generators import generate_narrations_from_topic, generate_title

    narrations = await generate_narrations_from_topic(
        pixelle_video.llm,
        topic=topic,
        n_scenes=n_scenes,
    )
    title = await generate_title(pixelle_video.llm, topic, strategy="auto")
    return narrations, title
# [/PIXELLE-CUSTOM]


# [PIXELLE-CUSTOM] Remix — reuse the images/videos from a previously generated
# video and only lightly edit the narration text (wording/tone), so no new
# image/video generation cost is incurred, only a fresh TTS pass.
async def _list_remix_candidates(pixelle_video, limit: int = 30):
    result = await pixelle_video.history.get_task_list(
        page=1, page_size=limit, status="completed",
        sort_by="created_at", sort_order="desc",
    )
    return result.get("tasks", [])


async def _load_remix_source(pixelle_video, task_id: str):
    return await pixelle_video.history.get_task_detail(task_id)


async def _rewrite_remix_narrations(pixelle_video, narrations: list, instruction: str) -> list:
    """Rewrite narrations in a different angle/tone while keeping the exact
    same line count and staying on-topic per line, since each line stays
    paired with a fixed, already-generated image/video by index."""
    from pixelle_video.utils.content_generators import _parse_json

    n = len(narrations)
    numbered = "\n".join(f"{i + 1}. {line}" for i, line in enumerate(narrations))
    direction = instruction.strip() if instruction and instruction.strip() else (
        "một cách diễn đạt/giọng văn khác, mới mẻ hơn"
    )
    prompt = f"""Dưới đây là kịch bản gồm {n} câu thoại cho 1 video ngắn, mỗi câu ứng với 1 cảnh đã có sẵn hình ảnh/video minh họa (không thể đổi cảnh hay thứ tự):

{numbered}

Hãy viết lại TOÀN BỘ {n} câu theo hướng: {direction}.

Yêu cầu bắt buộc:
- Giữ ĐÚNG {n} câu, không thêm/bớt dòng nào.
- Mỗi câu mới vẫn phải mô tả/phù hợp với chủ đề của câu gốc ở đúng vị trí tương ứng (vì hình ảnh của cảnh đó không đổi).
- Chỉ đổi cách diễn đạt/giọng văn/góc nhìn, không đổi chủ thể của từng cảnh.

Trả về JSON đúng định dạng: {{"narrations": ["câu 1", "câu 2", ...]}} với đúng {n} phần tử, không kèm chữ nào khác ngoài JSON."""

    response = await pixelle_video.llm(prompt=prompt, temperature=0.9, max_tokens=2000)
    result = _parse_json(response)
    new_narrations = result.get("narrations") or []
    if len(new_narrations) != n:
        raise ValueError(
            f"Model trả về {len(new_narrations)} câu, cần đúng {n} câu — thử lại hoặc chỉnh sửa tay."
        )
    return new_narrations


def _render_remix_section(pixelle_video) -> dict:
    st.caption(tr("remix.hint"))

    candidates = run_async(_list_remix_candidates(pixelle_video))
    if not candidates:
        st.info(tr("remix.no_candidates"))
        return {
            "batch_mode": False, "mode": "remix", "text": "", "title": "",
            "n_scenes": 0, "split_mode": "paragraph",
            "remix_narrations": [], "remix_source_frames": [],
        }

    options = {t["task_id"]: f"{t.get('title') or t['task_id']} ({t.get('n_frames', 0)} scenes)" for t in candidates}
    selected_task_id = st.selectbox(
        tr("remix.select_task"),
        options=list(options.keys()),
        format_func=lambda tid: options[tid],
        key="remix_task_id",
    )

    load_clicked = st.button(tr("remix.load_button"), key="remix_load_btn", use_container_width=True)
    if load_clicked:
        detail = run_async(_load_remix_source(pixelle_video, selected_task_id))
        storyboard = detail.get("storyboard") if detail else None
        if not storyboard or not storyboard.frames:
            st.error(tr("remix.load_failed"))
        else:
            st.session_state["remix_loaded_task_id"] = selected_task_id
            st.session_state["remix_title"] = storyboard.title or ""
            st.session_state["remix_source_frames"] = [
                {
                    "media_type": f.media_type,
                    "image_path": f.image_path,
                    "video_path": f.video_path,
                }
                for f in storyboard.frames
            ]
            st.session_state["remix_narrations_default"] = [f.narration for f in storyboard.frames]
            # [PIXELLE-CUSTOM] Bump the widget-key version so the title/narration
            # widgets below are recreated fresh with the new value=... Streamlit
            # keeps a widget's *frontend* value pinned to its key across reruns
            # (that's how in-progress edits survive a rerun), so re-popping the
            # same key does NOT force a refresh — st.rerun() re-syncs the stale
            # browser value straight back into session_state before our code
            # even runs. Changing the key is the only reliable way to force a
            # widget to pick up a new value= programmatically.
            st.session_state["remix_version"] = st.session_state.get("remix_version", 0) + 1
            # [/PIXELLE-CUSTOM]

    if st.session_state.get("remix_loaded_task_id") and st.session_state.get("remix_source_frames"):
        source_frames = st.session_state["remix_source_frames"]
        n_scenes = len(source_frames)
        version = st.session_state.get("remix_version", 0)  # [PIXELLE-CUSTOM]

        # [PIXELLE-CUSTOM] Show the loaded scenes (thumbnail + narration) so the
        # user can see exactly what media each narration line is paired with.
        st.markdown(f"**{tr('remix.scenes_preview_title', n=n_scenes)}**")
        default_narrations = st.session_state.get("remix_narrations_default", [])
        cols_per_row = 4
        for row_start in range(0, n_scenes, cols_per_row):
            row_frames = list(enumerate(source_frames))[row_start:row_start + cols_per_row]
            cols = st.columns(len(row_frames))
            for col, (i, frame) in zip(cols, row_frames):
                with col:
                    media_path = frame.get("video_path") if frame.get("media_type") == "video" else frame.get("image_path")
                    try:
                        if frame.get("media_type") == "video" and media_path:
                            st.video(media_path)
                        elif media_path:
                            st.image(media_path, use_container_width=True)
                        else:
                            st.caption(tr("remix.no_media"))
                    except Exception:
                        st.caption(tr("remix.media_load_failed"))
                    caption = default_narrations[i][:40] + "..." if i < len(default_narrations) and len(default_narrations[i]) > 40 else (default_narrations[i] if i < len(default_narrations) else "")
                    st.caption(f"**#{i + 1}** {caption}")
        # [/PIXELLE-CUSTOM]

        title_key = f"remix_title_input_{version}"  # [PIXELLE-CUSTOM]
        st.text_input(
            tr("script_preview.title_label"),
            value=st.session_state.get("remix_title", ""),
            key=title_key,
        )

        # [PIXELLE-CUSTOM] Rewrite button — ask the LLM to rewrite the narration
        # in a different angle/tone while keeping the exact same scene count,
        # so the reused images/videos still line up 1:1 with each line.
        rewrite_instruction = st.text_input(
            tr("remix.rewrite_instruction_label"),
            placeholder=tr("remix.rewrite_instruction_placeholder"),
            key="remix_rewrite_instruction",
        )
        narration_key = f"remix_narrations_input_{version}"
        if st.button(tr("remix.rewrite_button"), key="remix_rewrite_btn", use_container_width=True):
            current_text = st.session_state.get(narration_key) or "\n".join(default_narrations)
            current_lines = [line.strip() for line in current_text.split("\n") if line.strip()]
            with st.spinner(tr("remix.rewriting")):
                try:
                    rewritten = run_async(
                        _rewrite_remix_narrations(pixelle_video, current_lines, rewrite_instruction)
                    )
                    st.session_state["remix_narrations_default"] = rewritten
                    # Bump version so the text_area below is a *new* widget on
                    # rerun and actually picks up `rewritten` as its value=.
                    st.session_state["remix_version"] = version + 1
                    st.success(tr("remix.rewrite_success"))
                    st.rerun()
                except Exception as e:
                    st.error(tr("remix.rewrite_failed", error=str(e)))
        # [/PIXELLE-CUSTOM]

        st.text_area(
            tr("remix.narration_label"),
            value="\n".join(st.session_state.get("remix_narrations_default", [])),
            height=250,
            key=narration_key,
            help=tr("remix.narration_help"),
        )
        edited_lines = [
            line.strip() for line in
            st.session_state.get(narration_key, "").split("\n")
            if line.strip()
        ]
        if len(edited_lines) != n_scenes:
            st.warning(tr("remix.line_count_mismatch", expected=n_scenes, actual=len(edited_lines)))

        return {
            "batch_mode": False,
            "mode": "remix",
            "text": "\n".join(edited_lines),
            "title": st.session_state.get(title_key, ""),
            "n_scenes": n_scenes,
            "split_mode": "paragraph",
            "remix_narrations": edited_lines if len(edited_lines) == n_scenes else None,
            "remix_source_frames": st.session_state["remix_source_frames"],
        }

    return {
        "batch_mode": False, "mode": "remix", "text": "", "title": "",
        "n_scenes": 0, "split_mode": "paragraph",
        "remix_narrations": None, "remix_source_frames": [],
    }
# [/PIXELLE-CUSTOM]


def render_content_input(pixelle_video=None):
    """Render content input section (left column) with batch support"""
    with st.container(border=True):
        st.markdown(f"**{tr('section.content_input')}**")
        
        # ====================================================================
        # Step 1: Batch mode toggle (highest priority)
        # ====================================================================
        batch_mode = st.checkbox(
            tr("batch.mode_label"),
            value=False,
            help=tr("batch.mode_help")
        )
        
        if not batch_mode:
            # [PIXELLE-CUSTOM] Remix mode toggle — reuse a previous video's
            # images/videos, only lightly edit the narration wording.
            remix_active = False
            if pixelle_video is not None:
                remix_active = st.checkbox(
                    tr("remix.enable"),
                    value=False,
                    key="remix_enable",
                    help=tr("remix.enable_help"),
                )
            if remix_active:
                with st.container(border=True):
                    st.markdown(f"**{tr('remix.section_title')}**")
                    return _render_remix_section(pixelle_video)
            # [/PIXELLE-CUSTOM]

            # ================================================================
            # Single task mode (original logic, unchanged)
            # ================================================================
            # Processing mode selection
            mode = st.radio(
                "Processing Mode",
                ["generate", "fixed"],
                horizontal=True,
                format_func=lambda x: tr(f"mode.{x}"),
                label_visibility="collapsed"
            )
            
            # Text input (unified for both modes)
            text_placeholder = tr("input.topic_placeholder") if mode == "generate" else tr("input.content_placeholder")
            text_height = 120 if mode == "generate" else 200
            text_help = tr("input.text_help_generate") if mode == "generate" else tr("input.text_help_fixed")
            
            text = st.text_area(
                tr("input.text"),
                placeholder=text_placeholder,
                height=text_height,
                help=text_help
            )
            
            # Split mode selector (only show in fixed mode)
            if mode == "fixed":
                split_mode_options = {
                    "paragraph": tr("split.mode_paragraph"),
                    "line": tr("split.mode_line"),
                    "sentence": tr("split.mode_sentence"),
                }
                split_mode = st.selectbox(
                    tr("split.mode_label"),
                    options=list(split_mode_options.keys()),
                    format_func=lambda x: split_mode_options[x],
                    index=0,  # Default to paragraph mode
                    help=tr("split.mode_help")
                )
            else:
                split_mode = "paragraph"  # Default for generate mode (not used)
            
            # Title input (optional for both modes)
            title = st.text_input(
                tr("input.title"),
                placeholder=tr("input.title_placeholder"),
                help=tr("input.title_help")
            )
            
            # Number of scenes (only show in generate mode)
            if mode == "generate":
                n_scenes = st.slider(
                    tr("video.frames"),
                    min_value=3,
                    max_value=30,
                    value=5,
                    help=tr("video.frames_help"),
                    label_visibility="collapsed",
                    key="std_n_scenes"  # [PIXELLE-CUSTOM] targetable by Channel Preset
                )
                st.caption(tr("video.frames_label", n=n_scenes))
            else:
                # Fixed mode: n_scenes is ignored, set default value
                n_scenes = 5
                st.info(tr("video.frames_fixed_mode_hint"))

            # [PIXELLE-CUSTOM] Script Preview & Edit (generate mode only) ----------
            final_mode, final_text, final_title, final_split_mode = mode, text, title, split_mode
            if mode == "generate" and pixelle_video is not None:
                with st.expander(tr("script_preview.section_title"), expanded=False):
                    st.caption(tr("script_preview.hint"))

                    has_preview = bool(st.session_state.get("sp_narrations"))
                    col_gen, col_clear = st.columns([3, 1])
                    with col_gen:
                        gen_label = tr("script_preview.regenerate_button") if has_preview else tr("script_preview.generate_button")
                        gen_clicked = st.button(gen_label, key="sp_generate_btn", use_container_width=True)
                    with col_clear:
                        if has_preview and st.button(tr("script_preview.clear_button"), key="sp_clear_btn", use_container_width=True):
                            for k in ("sp_narrations", "sp_title", "sp_script_input", "sp_title_input"):
                                st.session_state.pop(k, None)
                            st.rerun()

                    if gen_clicked:
                        if not text.strip():
                            st.warning(tr("script_preview.empty_topic_warning"))
                        else:
                            with st.spinner(tr("script_preview.generating")):
                                try:
                                    narrations, gen_title = run_async(
                                        _generate_script_preview(pixelle_video, text, n_scenes)
                                    )
                                    st.session_state["sp_narrations"] = narrations
                                    st.session_state["sp_title"] = gen_title
                                    # Drop stale widget state so the text_area/text_input
                                    # below re-initialize from the freshly generated values
                                    # instead of showing a previous (possibly edited) draft.
                                    st.session_state.pop("sp_script_input", None)
                                    st.session_state.pop("sp_title_input", None)
                                    st.success(tr("script_preview.success"))
                                except Exception as e:
                                    st.error(tr("script_preview.error", error=str(e)))

                    if st.session_state.get("sp_narrations"):
                        st.text_input(
                            tr("script_preview.title_label"),
                            value=st.session_state.get("sp_title", ""),
                            key="sp_title_input",
                        )
                        st.text_area(
                            tr("script_preview.narration_label"),
                            value="\n\n".join(st.session_state["sp_narrations"]),
                            height=250,
                            key="sp_script_input",
                        )
                        st.caption(tr("script_preview.using_edited_notice"))

                        edited_script = st.session_state.get("sp_script_input", "")
                        if edited_script.strip():
                            # Hand off to "fixed" mode so Generate Video uses this
                            # exact (possibly hand-edited) script as-is, with no
                            # further AI rewriting of the narration text.
                            final_mode = "fixed"
                            final_text = edited_script
                            final_split_mode = "paragraph"
                            if not final_title:
                                final_title = st.session_state.get("sp_title_input", "")
            # [/PIXELLE-CUSTOM] -----------------------------------------------------

            return {
                "batch_mode": False,
                "mode": final_mode,
                "text": final_text,
                "title": final_title,
                "n_scenes": n_scenes,
                "split_mode": final_split_mode
            }
        
        else:
            # ================================================================
            # Batch mode (simplified YAGNI version)
            # ================================================================
            st.markdown(f"**{tr('batch.section_title')}**")
            
            # Batch rules info
            st.info(f"""
**{tr('batch.rules_title')}**
- ✅ {tr('batch.rule_1')}
- ✅ {tr('batch.rule_2')}
- ✅ {tr('batch.rule_3')}
            """)
            
            # Batch topics input
            text_input = st.text_area(
                tr("batch.topics_label"),
                height=300,
                placeholder=tr("batch.topics_placeholder"),
                help=tr("batch.topics_help")
            )
            
            # Split topics by newline
            if text_input:
                # Simple split by newline, filter empty lines
                topics = [
                    line.strip() 
                    for line in text_input.strip().split('\n') 
                    if line.strip()
                ]
                
                if topics:
                    # Check count limit
                    if len(topics) > 100:
                        st.error(tr("batch.count_error", count=len(topics)))
                        topics = []
                    else:
                        st.success(tr("batch.count_success", count=len(topics)))
                        
                        # Preview topics list
                        with st.expander(tr("batch.preview_title"), expanded=False):
                            for i, topic in enumerate(topics, 1):
                                st.markdown(f"`{i}.` {topic}")
                else:
                    topics = []
            else:
                topics = []
            
            st.markdown("---")
            
            # Title prefix (optional)
            title_prefix = st.text_input(
                tr("batch.title_prefix_label"),
                placeholder=tr("batch.title_prefix_placeholder"),
                help=tr("batch.title_prefix_help")
            )
            
            # Number of scenes (unified for all videos)
            n_scenes = st.slider(
                tr("batch.n_scenes_label"),
                min_value=3,
                max_value=30,
                value=5,
                help=tr("batch.n_scenes_help")
            )
            st.caption(tr("batch.n_scenes_caption", n=n_scenes))
            
            # Config info
            st.info(f"📌 {tr('batch.config_info')}")
            
            return {
                "batch_mode": True,
                "topics": topics,
                "mode": "generate",  # Fixed to AI generate content
                "title_prefix": title_prefix,
                "n_scenes": n_scenes,
            }


def render_bgm_section(key_prefix=""):
    """Render BGM selection section"""
    with st.container(border=True):
        st.markdown(f"**{tr('section.bgm')}**")
        
        with st.expander(tr("help.feature_description"), expanded=False):
            st.markdown(f"**{tr('help.what')}**")
            st.markdown(tr("bgm.what"))
            st.markdown(f"**{tr('help.how')}**")
            st.markdown(tr("bgm.how"))
        
        # Dynamically scan bgm folder for music files (merged from bgm/ and data/bgm/)
        from pixelle_video.utils.os_util import list_resource_files
        
        try:
            all_files = list_resource_files("bgm")
            # Filter to audio files only
            audio_extensions = ('.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg')
            bgm_files = sorted([f for f in all_files if f.lower().endswith(audio_extensions)])
        except Exception as e:
            st.warning(f"Failed to load BGM files: {e}")
            bgm_files = []
        
        # Add special "None" option
        bgm_options = [tr("bgm.none")] + bgm_files
        
        # Default to "default.mp3" if exists, otherwise first option
        default_index = 0
        if "default.mp3" in bgm_files:
            default_index = bgm_options.index("default.mp3")
        
        bgm_choice = st.selectbox(
            "BGM",
            bgm_options,
            index=default_index,
            label_visibility="collapsed",
            key=f"{key_prefix}bgm_selector"
        )
        
        # BGM volume slider (only show when BGM is selected)
        if bgm_choice != tr("bgm.none"):
            bgm_volume = st.slider(
                tr("bgm.volume"),
                min_value=0.0,
                max_value=0.5,
                value=0.2,
                step=0.01,
                format="%.2f",
                key=f"{key_prefix}bgm_volume_slider",
                help=tr("bgm.volume_help")
            )
        else:
            bgm_volume = 0.2  # Default value when no BGM selected
        
        # BGM preview button (only if BGM is not "None")
        if bgm_choice != tr("bgm.none"):
            if st.button(tr("bgm.preview"), key=f"{key_prefix}preview_bgm", use_container_width=True):
                from pixelle_video.utils.os_util import get_resource_path, resource_exists
                try:
                    if resource_exists("bgm", bgm_choice):
                        bgm_file_path = get_resource_path("bgm", bgm_choice)
                        st.audio(bgm_file_path)
                    else:
                        st.error(tr("bgm.preview_failed", file=bgm_choice))
                except Exception as e:
                    st.error(f"{tr('bgm.preview_failed', file=bgm_choice)}: {e}")
        
        # Use full filename for bgm_path (including extension)
        bgm_path = None if bgm_choice == tr("bgm.none") else bgm_choice
    
    return {
        "bgm_path": bgm_path,
        "bgm_volume": bgm_volume
    }


def render_version_info():
    """Render version info and GitHub link"""
    with st.container(border=True):
        st.markdown(f"**{tr('version.title')}**")
        version = get_project_version()
        github_url = "https://github.com/AIDC-AI/Pixelle-Video"
        
        # Version and GitHub link in one line
        github_url = "https://github.com/AIDC-AI/Pixelle-Video"
        badge_url = "https://img.shields.io/github/stars/AIDC-AI/Pixelle-Video"

        st.markdown(
            f'{tr("version.current")}: `{version}` &nbsp;&nbsp; '
            f'<a href="{github_url}" target="_blank">'
            f'<img src="{badge_url}" alt="GitHub stars" style="vertical-align: middle;">'
            f'</a>',
            unsafe_allow_html=True)

