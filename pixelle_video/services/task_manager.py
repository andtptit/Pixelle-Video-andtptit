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
[PIXELLE-CUSTOM] Background task runner.

Runs an async coroutine in a dedicated background thread with its own event
loop, fully decoupled from the Streamlit script that submitted it. This is
what lets video generation survive a page reload, page navigation, or tab
switch (previously: Streamlit stops the current script's execution the
moment the session moves on to a new run, silently abandoning any
in-progress generation), and lets multiple generations run concurrently.

The submitting Streamlit script does not block on the result — it should
track the task by its task_id and poll on-disk state (task metadata +
progress sidecar file, see PersistenceService) across reruns/reloads to
show status. This is a plain module-level global (not st.session_state),
so it lives for the lifetime of the server process, unaffected by any one
session's reruns.
"""

import asyncio
import json
import os
import sys
import threading
from typing import Callable, Coroutine, Any, Optional
from loguru import logger


def run_in_background(coro_factory: Callable[[], Coroutine[Any, Any, Any]], name: str = "pixelle-task") -> threading.Thread:
    """
    Start `coro_factory()` in a new background thread with its own event
    loop. Returns immediately; does not wait for completion.

    Args:
        coro_factory: A zero-arg callable returning the coroutine to run.
            Must be zero-arg (not the coroutine itself) because a coroutine
            object can only be awaited once, and needs to be created inside
            the new thread/loop, not the caller's.
        name: Thread name, for debugging/logging.
    """

    def _runner():
        # On Windows, the default SelectorEventLoop cannot launch subprocesses
        # (raises NotImplementedError) — Playwright's browser is launched as
        # a subprocess, needed for HTML frame rendering. A brand new thread
        # has no inherited event loop policy quirks from Streamlit/Tornado,
        # but still defaults to Selector on this platform unless a Proactor
        # loop is created explicitly (same reasoning as web/utils/async_helpers.run_async).
        if sys.platform == "win32":
            loop = asyncio.ProactorEventLoop()
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(coro_factory())
        except Exception as e:
            # The pipeline itself persists failure status (see
            # LinearVideoPipeline.handle_exception); this is a last-resort
            # log in case something goes wrong before/outside that.
            logger.error(f"Background task '{name}' failed: {e}")
        finally:
            loop.close()

    thread = threading.Thread(target=_runner, name=name, daemon=True)
    thread.start()
    return thread


# ============================================================================
# Progress sidecar file — a small `progress.json` next to each task's
# metadata.json, updated frequently (once per pipeline progress event) so a
# reconnecting session (after reload/navigation) can show live-ish progress
# without needing to be the same script run that started the task. Kept
# separate from metadata.json (which only changes a handful of times per
# task: running -> completed/failed) to avoid rewriting the larger file on
# every single progress tick.
# ============================================================================

def _progress_path(task_id: str) -> str:
    from pixelle_video.utils.os_util import get_output_path
    return get_output_path(task_id, "progress.json")


def save_task_progress(task_id: str, progress: float, event_type: str, **extra):
    """Best-effort, synchronous write — called directly from a pipeline's
    progress_callback, which is a plain sync callable, not awaited."""
    try:
        with open(_progress_path(task_id), "w", encoding="utf-8") as f:
            json.dump({"progress": progress, "event_type": event_type, **extra}, f)
    except Exception as e:
        logger.debug(f"Failed to write progress sidecar for {task_id}: {e}")


def load_task_progress(task_id: str) -> Optional[dict]:
    path = _progress_path(task_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
