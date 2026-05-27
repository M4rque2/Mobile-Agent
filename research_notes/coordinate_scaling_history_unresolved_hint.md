# Coordinate Scaling and Prompt Inconsistency Note

## Context
This note records the current investigation result for:

- why MobileAgent introduced coordinate scaling rules,
- which version first introduced 0-1000 normalization,
- whether papers provide an explicit rationale.
- how this repository currently handles screenshot resizing and action-coordinate scaling.

## Current Conclusion
1. In repository implementations, 0-1000 coordinate mapping appears explicitly in Mobile-Agent-v3 and is maintained/defaulted in Mobile-Agent-v3.5 runners.
2. In Mobile-Agent-v1/v2 code paths, this 0-1000 mapping is not the primary convention:
   - v1 mainly uses normalized ratio to screen conversion,
   - v2 mainly executes absolute pixel coordinates from action space.
3. In paper-level text (v1/v2/v3 reports), there is no clear theoretical justification section dedicated to "why 0-1000" as a canonical design choice.
4. In this repository, the intended runtime behavior appears to be:
   - ask the model to output action coordinates in a normalized 0-1000 action space,
   - scale those coordinates to the real Android device resolution before executing ADB actions.
5. The current prompt wording is misleading because it says "The screen's resolution is 1000x1000" instead of saying "Use normalized 0-1000 action coordinates."
6. Therefore, this question remains partially unresolved at theory/documentation level:
   - implementation evidence exists,
   - explicit paper rationale is not clearly stated.
   It is also now a concrete runtime-consistency issue in this codebase.

## Current Code Path Snapshot

### 1. ADB screenshot capture keeps original device pixels

`agent_io.py` captures screenshots with:

```python
adb exec-out screencap -p
```

The bytes are written directly to disk. For the XHS run:

```text
tasks/xhs_note_collection/2026-05-27_14-49-31/screenshot/screenshot_2.png
original screenshot size: 1440 x 3120
```

### 2. LLM request resizes the screenshot, but not to 1000x1000

`llm_client.py:image_to_data_url()` opens the screenshot and calls:

```python
smart_resize(
    image.height,
    image.width,
    factor=28,
    min_pixels=3136,
    max_pixels=1003520,
)
```

Then it sends the resized image as base64 `image_url`.

For the same XHS screenshot:

```text
original screenshot: 1440 x 3120
image sent to LLM:    672 x 1456
scale factor:         0.4667
```

So the model does not receive a 1000x1000 image. It receives a portrait image whose aspect ratio is preserved and whose total pixels are constrained.

### 3. System prompt says "screen resolution is 1000x1000"

`agent.py:SYSTEM_PROMPT` currently says:

```text
* The screen's resolution is 1000x1000.
```

This is misleading. The actual device screen is not 1000x1000, and the resized image sent to the LLM is not 1000x1000.

The intended meaning is probably:

```text
Use normalized action coordinates from 0 to 1000 on both axes.
The runtime will scale those action coordinates to the real device resolution.
```

The prompt/schema also describes coordinates as "pixels from the edge", which conflicts with the intended normalized coordinate protocol.

### 4. Action coordinates are scaled after model output

`agent.py` parses the model response, then calls:

```python
action_parameter = rescale_coordinates(action_parameter, image.width, image.height)
```

`agent_io.py:rescale_coordinates()` currently supports three cases:

1. If every coordinate is in `[0, 1000]`, treat it as normalized 1000-space and scale to screenshot/device pixels.
2. If coordinates are already within the screenshot width/height, treat them as absolute pixels and execute directly.
3. If coordinates exceed device resolution, guess a source resolution and rescale.

This tolerance makes the runtime robust, but it also hides protocol violations and produces ambiguous logs.

## Concrete Inconsistency Found in XHS Run

From:

```text
research_notes/run_2026-05-27 14-49-32.log
```

Step 1:

```text
MODEL OUTPUT coordinate: [496, 939]
ACTION logged:           [714, 2929]
```

This was treated as normalized 0-1000 and scaled to a 1440x3120 screenshot.

Step 2:

```text
MODEL OUTPUT coordinate:  [793, 1648]
MODEL OUTPUT coordinate2: [229, 1648]
ACTION logged:            [793, 1648] -> [229, 1648]
```

Here the model output `y=1648`, which violates the 0-1000 normalized protocol. Because `1648` is still within the physical screenshot height `3120`, the executor treated it as absolute pixels and did not scale it.

This means one run can contain mixed coordinate spaces:

- normalized action coordinates,
- resized-image-like coordinates,
- physical-device-like coordinates.

The model receives a `672x1456` image, the prompt says `1000x1000`, and the executor may accept `1440x3120` physical coordinates. These three coordinate frames are not consistently represented to the model or in logs.

## Repository Evidence Snapshot
- v3 README mentions relative coordinates 0-1000 and mapping to actual resolution.
- v3 code contains `/ 1000 * width` and `/ 1000 * height` conversion before action execution.
- v3.5 README states GUI-Owl 1.5 outputs relative coordinates (0-1000) by default.
- v3.5 mobile/computer runners contain normalized-to-pixel rescaling logic.

## Paper Survey Snapshot
Surveyed papers/reports:

- arXiv:2401.16158 (Mobile-Agent v1)
- arXiv:2406.01014 (Mobile-Agent v2)
- arXiv:2508.15144 (Mobile-Agent-v3 technical report)

Observed pattern:

- Papers focus on operation space, planning/reflection architecture, grounding, and online environment performance.
- Action formats are described (for example Tap/Swipe with coordinates), but no explicit dedicated argument was found that formalizes why 0-1000 is chosen over other normalization schemes.

## Why This Is Marked Unresolved
The upstream engineering behavior is clear in code and README, but the deeper design rationale is not explicitly documented in the surveyed paper text.

Separately, this repository has a clear local issue:

- screenshot resizing uses model-friendly aspect-preserving dimensions,
- the system prompt describes a fake 1000x1000 "screen resolution",
- the action executor accepts both normalized and absolute coordinates,
- logs currently print only the executed/mutated action under `[ACTION]`, not both raw model action and scaled action.

This makes it hard to know which coordinate space the model intended and whether failures come from model grounding, prompt wording, resize behavior, or executor scaling.

## Recommended Follow-Up
1. Rewrite the system prompt:
   - replace "The screen's resolution is 1000x1000" with "Use normalized action coordinates in [0,1000] on both axes."
   - remove "pixels" wording from coordinate schema descriptions.
   - explicitly say "do not use screenshot pixels, device pixels, or resized image pixels."
2. Decide executor policy:
   - strict mode: reject coordinates outside `[0,1000]` and request a retry;
   - compatibility mode: keep accepting absolute coordinates but log the detected coordinate space.
3. Improve logs:
   - log `model_action_raw`,
   - log `coordinate_space_detected`,
   - log `executed_action_scaled`.
4. Add a small trace field in LLM requests:
   - original screenshot size,
   - image size sent to LLM,
   - expected action coordinate space.

## Suggested Next Research Step
If needed later, continue with:

1. commit-history level trace in upstream MobileAgent repository to identify first introducing commit and commit message rationale,
2. issue/discussion/blog/changelog search from maintainers for explicit explanation,
3. benchmark protocol docs (for example AndroidWorld/OSWorld related tooling docs) to verify whether 1000-space is inherited convention,
4. controlled A/B run comparing strict normalized-only coordinates vs compatibility-mode mixed coordinate handling.
