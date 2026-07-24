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
Async helper functions for web UI
"""

import asyncio
import sys
import tomllib
from pathlib import Path

from loguru import logger


def run_async(coro):
    """Run async coroutine in sync context"""
    if sys.platform == "win32":
        # Streamlit/Tornado may switch the global asyncio policy to
        # WindowsSelectorEventLoopPolicy, which breaks subprocess-based
        # libraries such as Playwright on Windows. Use an explicit
        # Proactor loop here so this sync bridge does not depend on the
        # ambient global policy.
        loop = asyncio.ProactorEventLoop()
        try:
            return loop.run_until_complete(coro)
        finally:
            # [PIXELLE-CUSTOM] Do NOT close the shared HTMLFrameGenerator
            # browser here. Streamlit runs each session in its own thread,
            # so run_async() calls from different sessions/reruns (e.g. a
            # page reload firing some unrelated async call) can overlap in
            # wall-clock time. The browser is a *process-wide* singleton
            # (HTMLFrameGenerator._browser); closing it here mid-flight was
            # yanking it out from under a still-running video generation in
            # another thread, crashing that task with
            # "TargetClosedError: ... browser has been closed" (confirmed
            # by reproducing: F5 during Quick Create generation reliably
            # killed the in-progress task). HTMLFrameGenerator._ensure_browser()
            # already detects a stale/cross-loop browser and recreates it
            # lazily and safely, so an explicit close-after-every-call here
            # is both redundant and unsafe. The browser now simply lives for
            # the lifetime of the server process.
            loop.close()
            # [/PIXELLE-CUSTOM]
    return asyncio.run(coro)


def get_project_version():
    """Get project version from pyproject.toml"""
    try:
        # Get project root (web parent directory)
        web_dir = Path(__file__).resolve().parent.parent
        project_root = web_dir.parent
        pyproject_path = project_root / "pyproject.toml"
        
        if pyproject_path.exists():
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)
                return pyproject_data.get("project", {}).get("version", "Unknown")
    except Exception as e:
        logger.warning(f"Failed to read version from pyproject.toml: {e}")
    return "Unknown"

