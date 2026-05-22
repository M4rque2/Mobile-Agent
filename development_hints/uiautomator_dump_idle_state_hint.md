# UIAutomator Dump Idle-State Hint

## Context
While dumping Android UI XML with:

- adb shell uiautomator dump <remote_path>

we observed intermittent failures:

- ERROR: could not get idle state.

## What We Verified
Two XML files captured from the same app page (video page) were compared.

Result:
- Node count remained the same.
- Layout structure remained the same.
- Only time/progress-related text fields changed between dumps.

Conclusion:
- The main risk is not "video page" itself.
- The risk is continuously changing UI elements (for example playback progress/time), which can prevent UIAutomator from reaching an idle state.

## Practical Guidance
1. Prefer dumping when UI is as stable as possible (pause video, no overlays, no transitions).
2. Add retry + delay logic in scripts.
3. Validate remote XML exists before pulling.
4. Fail fast with clear errors when dump does not produce a file.
5. Optionally test compressed mode:
   - adb shell uiautomator dump --compressed <remote_path>

## Suggested Script Behavior
- Generate timestamped file names per run.
- Dump on device.
- Check remote file exists.
- Pull to local output folder.
- Optionally delete remote file to simulate "move".
- Verify local file exists before reporting success.
