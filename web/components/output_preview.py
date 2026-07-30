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
Output preview components for web UI (right column)
"""

import base64
import json
import os
from pathlib import Path

import streamlit as st
from loguru import logger

from web.i18n import tr, get_language
from pixelle_video.models.progress import ProgressEvent
from pixelle_video.config import config_manager


# [PIXELLE-CUSTOM] Background generation + a self-refreshing "Active Tasks"
# panel. Generation used to run as a single blocking `run_async()` call
# inside this button's script run — meaning it died the moment the user
# reloaded the page, switched to another page (e.g. History), or otherwise
# caused Streamlit to abandon this script run (Streamlit always stops the
# currently running script for a session before starting a new one; this is
# not something a try/except here can catch). It also meant the user could
# not start a second video while the first was still generating.
#
# Now the pipeline coroutine is handed to a background thread with its own
# event loop (pixelle_video.services.task_manager.run_in_background), fully
# decoupled from this script's lifecycle. Progress is written to a small
# per-task `progress.json` sidecar file (since a background thread must not
# touch `st.*` widgets directly — Streamlit's rendering is not thread-safe
# across threads other than the one running the current script). This
# function polls that file + the task's metadata.json (already written as
# "running"/"completed"/"failed", see standard.py/linear.py) from
# st.session_state["pv_active_tasks"], which survives page reloads because
# Streamlit session_state persists across a same-session reconnect.
def _format_progress_message(progress_data: dict) -> str:
    event_type = progress_data.get("event_type", "")
    if not event_type:
        return tr("progress.starting")
    if event_type == "frame_step":
        action_text = tr(f"progress.step_{progress_data.get('action')}")
        message = tr(
            "progress.frame_step",
            current=progress_data.get("frame_current"),
            total=progress_data.get("frame_total"),
            step=progress_data.get("step"),
            action=action_text,
        )
    elif event_type == "processing_frame":
        message = tr(
            "progress.frame",
            current=progress_data.get("frame_current"),
            total=progress_data.get("frame_total"),
        )
    else:
        message = tr(f"progress.{event_type}")
    if progress_data.get("extra_info"):
        message = f"{message} - {progress_data['extra_info']}"
    return message


def _load_task_metadata(task_id: str):
    from pixelle_video.utils.os_util import get_output_path
    meta_path = os.path.join(get_output_path(task_id), "metadata.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@st.fragment(run_every="2s")
def render_active_tasks_panel(pixelle_video):
    """Self-refreshing panel: shows every task the user submitted this
    session, independent of page reloads/navigation, without blocking the
    rest of the page (a Streamlit fragment reruns on its own schedule).

    Reload testing showed st.session_state["pv_active_tasks"] does not
    reliably survive every reload/reconnect in practice, so this also
    rediscovers any on-disk task still marked "running" (persisted by
    setup_environment) and merges it in — belt and suspenders, since the
    background thread itself is already fully independent of session_state
    either way."""
    from pixelle_video.services.task_manager import load_task_progress
    from web.utils.async_helpers import run_async

    active = list(st.session_state.get("pv_active_tasks", []))
    try:
        running = run_async(pixelle_video.history.get_task_list(
            page=1, page_size=50, status="running",
        ))
        for t in running.get("tasks", []):
            if t["task_id"] not in active:
                active.append(t["task_id"])
    except Exception as e:
        logger.debug(f"Failed to rediscover running tasks: {e}")

    if not active:
        return

    st.markdown(f"**{tr('task.active_panel_title')}**")
    still_active = []
    for task_id in active:
        metadata = _load_task_metadata(task_id)
        status = (metadata or {}).get("status", "running")
        title = (metadata or {}).get("input", {}).get("title") or task_id

        with st.container(border=True):
            dismissed = False
            if status == "completed":
                st.success(f"✅ {title}")
                video_path = (metadata.get("result") or {}).get("video_path")
                if video_path and os.path.exists(video_path):
                    st.video(video_path)
                dismissed = st.button(tr("task.dismiss"), key=f"pv_dismiss_{task_id}")
            elif status == "failed":
                st.error(f"❌ {title}: {metadata.get('error', '')}")
                dismissed = st.button(tr("task.dismiss"), key=f"pv_dismiss_{task_id}")
            else:
                progress_data = load_task_progress(task_id) or {}
                st.markdown(f"⏳ **{title}**")
                st.progress(min(progress_data.get("progress", 0.0), 0.99))
                st.caption(_format_progress_message(progress_data))

            if not dismissed:
                still_active.append(task_id)

    st.session_state["pv_active_tasks"] = still_active
# [/PIXELLE-CUSTOM]


def render_output_preview(pixelle_video, video_params):
    """Render output preview section (right column)"""
    # Check if batch mode
    is_batch = video_params.get("batch_mode", False)
    
    if is_batch:
        # Batch generation mode
        render_batch_output(pixelle_video, video_params)
    else:
        # Single video generation mode (original logic)
        render_single_output(pixelle_video, video_params)


def render_single_output(pixelle_video, video_params):
    """Render single video generation output (original logic, unchanged)"""
    # Extract parameters from video_params dict
    # [PIXELLE-CUSTOM] keep a reference to the original params (remix_* fields)
    # before `video_params` gets reassigned to the whitelisted dict below.
    original_params = video_params
    # [/PIXELLE-CUSTOM]
    text = video_params.get("text", "")
    mode = video_params.get("mode", "generate")
    title = video_params.get("title")
    n_scenes = video_params.get("n_scenes", 5)
    split_mode = video_params.get("split_mode", "paragraph")
    bgm_path = video_params.get("bgm_path")
    bgm_volume = video_params.get("bgm_volume", 0.2)
    
    tts_mode = video_params.get("tts_inference_mode", "local")
    selected_voice = video_params.get("tts_voice")
    tts_speed = video_params.get("tts_speed")
    tts_workflow_key = video_params.get("tts_workflow")
    ref_audio_path = video_params.get("ref_audio")
    
    frame_template = video_params.get("frame_template")
    custom_values_for_video = video_params.get("template_params", {})
    workflow_key = video_params.get("media_workflow")
    api_video_params = video_params.get("api_video_params")
    prompt_prefix = video_params.get("prompt_prefix", "")
    zoom_effect = video_params.get("zoom_effect", False)  # [PIXELLE-CUSTOM]
    narration_style_notes = video_params.get("narration_style_notes", "")  # [PIXELLE-CUSTOM]
    enable_pause_dash = video_params.get("enable_pause_dash", True)  # [PIXELLE-CUSTOM]
    enable_scene_grouping = video_params.get("enable_scene_grouping", False)  # [PIXELLE-CUSTOM]
    target_image_count = video_params.get("target_image_count")  # [PIXELLE-CUSTOM]

    with st.container(border=True):
        st.markdown(f"**{tr('section.video_generation')}**")
        
        # Check if system is configured
        if not config_manager.validate():
            st.warning(tr("settings.not_configured"))
        
        # Generate Button
        if st.button(tr("btn.generate"), type="primary", use_container_width=True):
            # Validate system configuration
            if not config_manager.validate():
                st.error(tr("settings.not_configured"))
                st.stop()

            # Validate input
            if not text:
                st.error(tr("error.input_required"))
                st.stop()

            # [PIXELLE-CUSTOM] Remix mode requires a valid narration-per-scene match
            if mode == "remix" and not original_params.get("remix_narrations"):
                st.error(tr("remix.invalid_narrations"))
                st.stop()
            # [/PIXELLE-CUSTOM]

            from pixelle_video.utils.template_util import get_template_type
            if frame_template and get_template_type(frame_template) == "video" and not workflow_key:
                st.error(
                    "请选择视频生成工作流或 API 视频模型后再生成。"
                    if get_language() == "zh_CN"
                    else "Please select a video workflow or API video model before generating."
                )
                st.stop()

            # [PIXELLE-CUSTOM] Submit to a background thread instead of
            # blocking this script run — see the big comment above
            # render_active_tasks_panel() for why.
            from pixelle_video.utils.os_util import create_task_id
            from pixelle_video.services.task_manager import run_in_background, save_task_progress

            task_id = create_task_id()

            def progress_callback(event: ProgressEvent, _task_id=task_id):
                save_task_progress(
                    _task_id,
                    progress=event.progress,
                    event_type=event.event_type,
                    frame_current=event.frame_current,
                    frame_total=event.frame_total,
                    step=event.step,
                    action=event.action,
                    extra_info=event.extra_info,
                )

            # Note: media_width and media_height are auto-determined from template
            gen_kwargs = {
                "text": text,
                "mode": mode,
                "title": title if title else None,
                "n_scenes": n_scenes,
                "split_mode": split_mode,
                "media_workflow": workflow_key,
                "api_video_params": api_video_params,
                "zoom_effect": zoom_effect,  # [PIXELLE-CUSTOM]
                "frame_template": frame_template,
                "prompt_prefix": prompt_prefix,
                "narration_style_notes": narration_style_notes,  # [PIXELLE-CUSTOM]
                "enable_pause_dash": enable_pause_dash,  # [PIXELLE-CUSTOM]
                "enable_scene_grouping": enable_scene_grouping,  # [PIXELLE-CUSTOM]
                "target_image_count": target_image_count,  # [PIXELLE-CUSTOM]
                "bgm_path": bgm_path,
                "bgm_volume": bgm_volume if bgm_path else 0.2,
                "progress_callback": progress_callback,
                "media_width": st.session_state.get('template_media_width'),
                "media_height": st.session_state.get('template_media_height'),
                "task_id": task_id,
            }
            if mode == "remix":
                gen_kwargs["remix_narrations"] = original_params.get("remix_narrations")
                gen_kwargs["remix_source_frames"] = original_params.get("remix_source_frames")
            gen_kwargs["tts_inference_mode"] = tts_mode
            if tts_mode == "local":
                gen_kwargs["tts_voice"] = selected_voice
                gen_kwargs["tts_speed"] = tts_speed
            else:  # comfyui
                gen_kwargs["tts_workflow"] = tts_workflow_key
                if ref_audio_path:
                    gen_kwargs["ref_audio"] = str(ref_audio_path)
            if custom_values_for_video:
                gen_kwargs["template_params"] = custom_values_for_video

            def _coro_factory(kwargs=gen_kwargs):
                return pixelle_video.generate_video(**kwargs)

            run_in_background(_coro_factory, name=f"pixelle-gen-{task_id}")

            active_tasks = st.session_state.setdefault("pv_active_tasks", [])
            if task_id not in active_tasks:
                active_tasks.append(task_id)

            st.success(tr("task.submitted"))
            st.rerun()
            # [/PIXELLE-CUSTOM]

    # [PIXELLE-CUSTOM] Live status for every task submitted this session —
    # keeps working across page reloads/navigation and while other tasks
    # are started, since generation no longer blocks this script.
    render_active_tasks_panel(pixelle_video)
    # [/PIXELLE-CUSTOM]


def render_batch_output(pixelle_video, video_params):
    """Render batch generation output (minimal, redirect to History)"""
    topics = video_params.get("topics", [])
    
    with st.container(border=True):
        st.markdown(f"**{tr('batch.section_generation')}**")
        
        # Check if topics are provided
        if not topics:
            st.warning(tr("batch.no_topics"))
            return
        
        # Check system configuration
        if not config_manager.validate():
            st.warning(tr("settings.not_configured"))
            return
        
        batch_count = len(topics)
        
        # Display batch info
        st.info(tr("batch.prepare_info", count=batch_count))
        
        # Estimated time (optional)
        estimated_minutes = batch_count * 3  # Assume 3 minutes per video
        st.caption(tr("batch.estimated_time", minutes=estimated_minutes))
        
        # Generate button with batch semantics
        if st.button(
            tr("batch.generate_button", count=batch_count),
            type="primary",
            use_container_width=True,
            help=tr("batch.generate_help")
        ):
            # Prepare shared config
            shared_config = {
                "title_prefix": video_params.get("title_prefix"),
                "n_scenes": video_params.get("n_scenes") or 5,
                "media_workflow": video_params.get("media_workflow"),
                "api_video_params": video_params.get("api_video_params"),
                "frame_template": video_params.get("frame_template"),
                "prompt_prefix": video_params.get("prompt_prefix") or "",
                "bgm_path": video_params.get("bgm_path"),
                "bgm_volume": video_params.get("bgm_volume") or 0.2,
                "tts_inference_mode": video_params.get("tts_inference_mode") or "local",
                "media_width": video_params.get("media_width"),
                "media_height": video_params.get("media_height"),
            }
            # Add TTS parameters based on mode (only add non-None values)
            if shared_config["tts_inference_mode"] == "local":
                tts_voice = video_params.get("tts_voice")
                tts_speed = video_params.get("tts_speed")
                if tts_voice:
                    shared_config["tts_voice"] = tts_voice
                if tts_speed:
                    shared_config["tts_speed"] = tts_speed
            else:  # comfyui
                tts_workflow = video_params.get("tts_workflow")
                if tts_workflow:
                    shared_config["tts_workflow"] = tts_workflow
                ref_audio = video_params.get("ref_audio")
                if ref_audio:
                    shared_config["ref_audio"] = str(ref_audio)
            
            # Add template parameters
            if video_params.get("template_params"):
                shared_config["template_params"] = video_params["template_params"]
            
            # UI containers
            overall_progress_container = st.container()
            current_task_container = st.container()
            
            # Overall progress UI
            overall_progress_bar = overall_progress_container.progress(0)
            overall_status = overall_progress_container.empty()
            
            # Current task progress UI
            current_task_title = current_task_container.empty()
            current_task_progress = current_task_container.progress(0)
            current_task_status = current_task_container.empty()
            
            # Overall progress callback
            def update_overall_progress(current, total, topic):
                progress = (current - 1) / total
                overall_progress_bar.progress(progress)
                overall_status.markdown(
                    f"📊 **{tr('batch.overall_progress')}**: {current}/{total} ({int(progress * 100)}%)"
                )
            
            # Single task progress callback factory
            def make_task_progress_callback(task_idx, topic):
                def callback(event: ProgressEvent):
                    # Display current task title
                    current_task_title.markdown(f"🎬 **{tr('batch.current_task')} {task_idx}**: {topic}")
                    
                    # Update task detailed progress
                    if event.event_type == "frame_step":
                        action_key = f"progress.step_{event.action}"
                        action_text = tr(action_key)
                        message = tr(
                            "progress.frame_step",
                            current=event.frame_current,
                            total=event.frame_total,
                            step=event.step,
                            action=action_text
                        )
                    elif event.event_type == "processing_frame":
                        message = tr(
                            "progress.frame",
                            current=event.frame_current,
                            total=event.frame_total
                        )
                    else:
                        message = tr(f"progress.{event.event_type}")
                    
                    current_task_progress.progress(event.progress)
                    current_task_status.text(message)
                
                return callback
            
            # Execute batch generation
            from web.utils.batch_manager import SimpleBatchManager
            import time
            
            batch_manager = SimpleBatchManager()
            start_time = time.time()
            
            batch_result = batch_manager.execute_batch(
                pixelle_video=pixelle_video,
                topics=topics,
                shared_config=shared_config,
                overall_progress_callback=update_overall_progress,
                task_progress_callback_factory=make_task_progress_callback
            )
            
            total_time = time.time() - start_time
            
            # Clear progress displays
            overall_progress_bar.progress(1.0)
            overall_status.markdown(f"✅ **{tr('batch.completed')}**")
            current_task_title.empty()
            current_task_progress.empty()
            current_task_status.empty()
            
            # Display results summary
            st.markdown("---")
            st.markdown(f"**{tr('batch.results_title')}**")
            
            col1, col2, col3 = st.columns(3)
            col1.metric(tr("batch.total"), batch_result["total_count"])
            col2.metric(f"✅ {tr('batch.success')}", batch_result["success_count"])
            col3.metric(f"❌ {tr('batch.failed')}", batch_result["failed_count"])
            
            # Display total time
            minutes = int(total_time / 60)
            seconds = int(total_time % 60)
            st.caption(f"⏱️ {tr('batch.total_time')}: {minutes}{tr('batch.minutes')}{seconds}{tr('batch.seconds')}")
            
            # Redirect to History page
            st.markdown("---")
            st.success(tr("batch.success_message"))
            st.info(tr("batch.view_in_history"))
            
            # Button to go to History page using JavaScript URL navigation
            st.markdown(
                f"""
                <a href="/History" target="_blank">
                    <button style="
                        width: 100%;
                        padding: 0.5rem 1rem;
                        background-color: white;
                        color: rgb(49, 51, 63);
                        border: 1px solid rgba(49, 51, 63, 0.2);
                        border-radius: 0.5rem;
                        cursor: pointer;
                        font-size: 1rem;
                        font-weight: 400;
                        text-align: center;
                    ">
                        📚 {tr('batch.goto_history')}
                    </button>
                </a>
                """,
                unsafe_allow_html=True
            )
            
            # Show failed tasks if any
            if batch_result["errors"]:
                st.markdown("---")
                st.markdown(f"#### {tr('batch.failed_list')}")
                
                for item in batch_result["errors"]:
                    with st.expander(f"🔴 {tr('batch.task')} {item['index']}: {item['topic']}", expanded=False):
                        st.error(f"**{tr('batch.error')}**: {item['error']}")
                        
                        # Detailed error (collapsed)
                        with st.expander(tr("batch.error_detail")):
                            st.code(item['traceback'], language="python")
    
