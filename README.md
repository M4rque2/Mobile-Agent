# GUI Agent

Mobile-Agent is an early-stage research and engineering project for understanding and building GUI agents, with an initial focus on Android devices.

We assume the reader is already familiar with coding agents such as Claude Code, Codex, Gemini CLI, or similar tools. Those agents are strong when the task can be solved by reading files, editing code, running commands, and checking tests. They can sometimes be forced into a GUI-agent style workflow by giving them computer-use tools: take a screenshot, inspect the interface, click, type, observe again, and continue.

But that is not what coding agents naturally optimize for. When they can solve a problem by writing code, calling an API, changing a file, or using a command-line shortcut, they usually will. That is often the right behavior for software engineering, but it is different from doing work through a graphical interface the way a human user does.

GUI agents are AI systems designed around that human-like interaction loop: observe the screen, understand the visible state, choose a UI action, execute it, then observe again. The interface is not a fallback when code access is unavailable; it is the primary environment.

Recent progress in multimodal models has made this idea more realistic, but the field is still early. We know GUI agents can sometimes interpret screenshots, follow instructions, and execute useful actions. We do not yet know how to make them consistently reliable, safe, measurable, and efficient across real applications.

This repository starts from that gap. We want to study what is already working, identify what remains unclear, and build a practical workspace for mobile GUI-agent experiments.

## Why This Repo Exists

I created this research repository to build GUI agents that work with multimodal models and help people handle tedious, repeated work inside graphical interfaces.

Maybe MCP, CLI tools, APIs, and deeper software integrations will replace much of this in the future. I hope they do. But today, I and the people I work with still have a lot of work trapped inside GUI interfaces: periodic checks, form filling, app operations, visual inspection, repetitive mobile workflows, and tasks that are simple for a human but expensive in time and attention.

I do not want to wait for someone else to automate all of it. I do not want to keep spending my life on repetitive UI work. So this project is an attempt to build the automation layer ourselves: observe the interface, reason with a multimodal model, act through the GUI, and keep improving the loop until it becomes useful.

## What We Know

Several things are becoming clear from current GUI-agent research:

- **The screen is a useful interface.** A model that can read screenshots and UI text can often infer what the user wants and where the next action should happen.
- **Action grounding matters.** It is not enough for a model to describe an action. The system must translate intent into coordinates, gestures, text input, app navigation, or structured accessibility actions.
- **Traces are essential.** GUI-agent failures are hard to understand without screenshots, model outputs, actions, timing, and intermediate states.
- **Benchmarks are improving but incomplete.** Existing tasks help compare agents, but they rarely capture all the messiness of real apps, dynamic content, login state, latency, and unexpected UI changes.
- **The model is only one part of the system.** Prompting, perception, memory, action schemas, verification, recovery, and environment control can matter as much as raw model capability.

## What We Don't Know

Important questions are still open:

- **Reliability:** How do we make agents complete long, multi-step tasks without drifting, repeating actions, or getting stuck?
- **Generalization:** How well can an agent transfer from benchmark apps to real apps with unfamiliar layouts and dynamic content?
- **Evaluation:** What should count as success when a task has many valid paths, partial progress, or ambiguous end states?
- **Safety:** How should agents handle irreversible actions, private data, payments, account changes, or destructive operations?
- **Efficiency:** How can agents reduce model calls, latency, and unnecessary exploration while still remaining robust?
- **Human collaboration:** When should an agent ask for help, request confirmation, or expose its uncertainty?

## Current Industrial Status

The industrial picture is moving quickly, but a rough pattern is visible.

OpenAI has official computer-use support. Its API documentation describes a `computer` tool where the model looks at screenshots, returns UI actions such as clicking, typing, or scrolling, and the client executes those actions in a browser or computer environment ([OpenAI Computer Use](https://developers.openai.com/api/docs/guides/tools-computer-use)). OpenAI also ships Codex workflows that can be steered from a phone, but the phone is used as a remote control and review surface for Codex work running elsewhere, not as evidence of a phone-GUI-use model that directly operates Android or iOS apps ([Work with Codex from anywhere](https://openai.com/index/work-with-codex-from-anywhere/)). I have not found an official OpenAI phone-use product comparable to the Android-focused systems below.

Anthropic is not only focused on coding. Claude has an official computer-use tool that provides screenshot, mouse, keyboard, and desktop automation capability through an agent loop ([Claude Computer Use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool)). This is important prior work, though it is framed around desktop environments rather than mobile phone control.

Google also has an official Gemini Computer Use capability. The Gemini API documentation describes browser-control agents that use screenshots and generate UI actions such as mouse clicks and keyboard input ([Gemini Computer Use](https://ai.google.dev/gemini-api/docs/computer-use)). This is strong evidence that Google is active in GUI automation, but the documented focus is browser/computer use rather than phone-use automation.

Chinese AI companies and labs appear especially active in mobile and general GUI agents:

- **Alibaba / Qwen ecosystem:** GUI-Owl and Mobile-Agent-v3 target GUI automation across desktop and mobile environments, with reported results on AndroidWorld and OSWorld ([Mobile-Agent-v3 / GUI-Owl](https://arxiv.org/abs/2508.15144)).
- **ByteDance:** UI-TARS is an open-source multimodal GUI agent line for automated GUI interaction; the project describes UI-TARS-1.5 and UI-TARS-2 as agent models for GUI, game, code, and tool-use tasks ([UI-TARS](https://github.com/bytedance/UI-TARS)).
- **OpenCUA / Meituan-related work:** OpenCUA provides open foundations for computer-use agents, including AgentNet data/tooling. Its repository also acknowledges contributions from the Meituan EvoCUA team for vLLM integration ([OpenCUA](https://github.com/xlang-ai/OpenCUA)).
- **Zhipu / Z.ai:** AutoGLM explicitly focuses on web browser and Android GUI scenarios as foundation-agent environments for real-world GUI interaction ([AutoGLM](https://www.zhipuai.cn/v1/autoglm)).

So the corrected view is: the top-tier U.S. labs are active in computer and browser use, while the strongest public emphasis on phone-use and Android GUI agents currently seems to come from Chinese teams and open research projects.

Smartphone GUI agents still appear less researched and less mature than desktop or browser agents. That gap is the main reason this repository starts with mobile, and especially Android. Phones contain many of the repetitive GUI workflows we actually want to automate, but they also add constraints that make the problem harder: small screens, touch gestures, app switching, mobile keyboards, permissions, dynamic layouts, and deeply stateful apps.

This project will focus on that smartphone-agent gap.

## What We Want To Build

Mobile devices are a natural but difficult environment for GUI agents: apps are visual, stateful, latency-sensitive, and often have no stable programmatic API. A mobile agent therefore needs more than a model call. It needs a full loop around perception, planning, action execution, recovery, and evaluation.

Mobile-Agent is intended to grow into that loop.

At a high level, we want Mobile-Agent to provide:

- **Android device control** through ADB for screenshots, taps, swipes, text input, app launches, and system navigation.
- **Multimodal model adapters** so different vision-language models can be tested behind a common interface.
- **Action planning and execution utilities** that turn model decisions into reliable device operations.
- **Task traces and logs** for debugging what the agent saw, decided, executed, and observed next.
- **Benchmark integration** for comparing agents across repeatable mobile tasks.
- **Experiment harnesses** that make it easy to run, inspect, and reproduce mobile-agent trials.

## Project Direction

This project starts from a simple premise: a useful mobile agent should be measurable, debuggable, and modular.

Measurable means we should be able to run the same task more than once and compare results. Debuggable means every step in the agent loop should leave enough evidence for a human to understand failures. Modular means we should be able to swap models, prompts, planners, perception strategies, and action executors without rewriting the whole system.

The initial focus is Android because ADB gives us a realistic control surface for screenshots and UI actions. The longer-term direction may include broader mobile environments, richer UI understanding, human-in-the-loop correction, and safer execution policies.

## Expected Agent Loop

The core loop we want to support looks like this:

1. Capture the current device state.
2. Convert the screen and optional UI metadata into model-ready context.
3. Ask a model or policy to choose the next action.
4. Validate and execute the action on the device.
5. Record screenshots, actions, model outputs, and errors.
6. Decide whether the task is complete, failed, or should continue.

This loop should be simple enough for quick experiments, but structured enough to support serious evaluation.

## Current Status

The repository is just starting. The README describes the intended direction before the main implementation lands.

Planned areas of work include:

- defining the project layout;
- adding the ADB interaction layer;
- adding model adapter interfaces;
- designing an action schema;
- creating trace storage for experiments;
- adding example tasks;
- wiring a first end-to-end agent run;
- documenting setup and usage.

## Who This Is For

This project is for people interested in mobile GUI agents, Android automation, multimodal model evaluation, and agent benchmarking. It may be useful to researchers testing model behavior, engineers building automation harnesses, or anyone trying to understand how agents behave in real mobile interfaces.

## Non-Goals For Now

To keep the project focused, the first versions are not trying to be:

- a production device farm;
- a general replacement for Appium or UIAutomator;
- a no-code automation product;
- a benchmark leaderboard by itself;
- a fully autonomous system for sensitive personal-device operations.

The near-term priority is a clean, inspectable research workspace.

## Repository Structure

The structure is still being defined. A likely direction is:

```text
Mobile-Agent/
  README.md
  mobile_agent/        # Core library code
  scripts/             # Local run and experiment scripts
  examples/            # Example tasks and agent runs
  traces/              # Local task traces, usually gitignored
  tests/               # Unit and integration tests
  docs/                # Design notes and project documentation
```

This may change as the implementation becomes clearer.

## Contributing

The best early contributions are clarifying the agent loop, improving the action schema, adding small reproducible Android tasks, and making experiment traces easier to inspect.

Before adding large features, prefer opening a design note or issue that explains:

- what mobile-agent problem the change solves;
- what assumptions it makes about Android devices, models, or benchmarks;
- how the behavior can be tested or reproduced;
- what trace output should exist when something fails.

## License

See [LICENSE](LICENSE).
