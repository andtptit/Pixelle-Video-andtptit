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
[PIXELLE-CUSTOM] Scene grouping prompt

Decides which consecutive narrations should share a single AI-generated
image, to cut image-generation cost on long scripts. This prompt only
decides GROUPING (a partition of scene indices) — it does not write new
image prompts; the first scene of each group's own image prompt (already
generated separately) is reused for the whole group.
"""


SCENE_GROUPING_PROMPT = """# Role Definition
You are a video editing assistant deciding how to group narration scenes so that visually/thematically continuous scenes can share a single illustration, while scenes with a clear change of subject, moment, or emotion get their own image.

# Input
There are {n_scenes} narration scenes, numbered 0 to {n_scenes_minus_1}, in order:

{numbered_narrations}

# Grouping Rules (Must Follow)
1. Each group must contain one or more CONSECUTIVE scene indices (e.g. [0,1,2] is valid; [0,2] is NOT valid — never skip an index).
2. Every index from 0 to {n_scenes_minus_1} must appear in exactly one group, covering all scenes in order, no gaps, no duplicates.
3. No single group may contain more than {max_group_size} scenes.
4. Aim for approximately {target_image_count} groups in total (this is a target, not a hard requirement — rule 3 takes priority if they conflict).
5. Only group scenes together when they describe the same visual moment, scene, or continuation of the same idea/mood. Give a scene its own group whenever the subject, setting, or emotional beat clearly changes — never group just to hit the target count.

# Output Format
Strictly output the following JSON, no explanations:
```json
{{
  "groups": [[0, 1], [2], [3, 4, 5]]
}}
```

Now decide the grouping. Only output JSON, no other content.
"""


def build_scene_grouping_prompt(
    narrations: list[str],
    target_image_count: int,
    max_group_size: int,
) -> str:
    """
    Build the scene-grouping decision prompt.

    Args:
        narrations: List of narration texts (already generated)
        target_image_count: Desired total number of image groups (soft target)
        max_group_size: Hard cap on how many consecutive scenes one group may contain

    Returns:
        Formatted prompt
    """
    numbered_narrations = "\n".join(
        f"{i}: {narration}" for i, narration in enumerate(narrations)
    )
    return SCENE_GROUPING_PROMPT.format(
        n_scenes=len(narrations),
        n_scenes_minus_1=len(narrations) - 1,
        numbered_narrations=numbered_narrations,
        target_image_count=target_image_count,
        max_group_size=max_group_size,
    )
