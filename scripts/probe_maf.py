#!/usr/bin/env python3
"""Probe the installed Microsoft Agent Framework (MAF) wheel to pin the rc1 API
surface Phase 4 depends on (plan §9). READ-ONLY introspection — it imports the
package and inspects signatures, but never instantiates an agent, opens a network
connection, or needs credentials.

Run it in the environment where `agent-framework` is installed:

    python scripts/probe_maf.py

Then paste the "=== PIN THESE (copy back) ===" block back so the Phase-4 wiring
targets the real names (ChatAgent vs Agent, run/run_stream vs run(stream=True),
AgentThread vs Session, eval symbols, etc.).
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil

# Submodules worth searching in addition to the top-level package.
SUBMODULES = [
    "agent_framework",
    "agent_framework.foundry",
    "agent_framework.observability",
    "agent_framework.openai",
    "agent_framework.azure",
]

# Candidate symbols per §9 topic. We report which name actually exists.
TOPICS: dict[str, list[str]] = {
    "Agent class": ["ChatAgent", "Agent", "ChatClientAgent", "ChatClientProtocol"],
    "Run / streaming": ["AgentResponse", "AgentResponseUpdate", "ResponseStream"],
    "Thread / session": ["AgentThread", "Session", "ChatMessageStoreProtocol"],
    "Tools": ["tool", "FunctionTool", "FunctionInvocationContext", "ai_function"],
    "Middleware": [
        "AgentMiddleware",
        "FunctionMiddleware",
        "ChatMiddleware",
        "AgentRunContext",
        "AgentContext",
        "ChatContext",
        "agent_middleware",
        "function_middleware",
        "chat_middleware",
    ],
    "Workflows": [
        "WorkflowBuilder",
        "Executor",
        "WorkflowContext",
        "AgentExecutor",
        "handler",
        "executor",
    ],
    "Structured output": ["ChatResponse", "ChatMessage", "ChatResponseUpdate"],
    "Observability": [
        "configure_otel_providers",
        "setup_observability",
        "get_tracer",
        "enable_instrumentation",
    ],
    "Evaluation": [
        "evaluate_agent",
        "evaluate_workflow",
        "EvalItem",
        "EvalResults",
        "LocalEvaluator",
        "evaluator",
        "keyword_check",
        "tool_called_check",
        "tool_calls_present",
        "tool_call_args_match",
        "ExpectedToolCall",
        "ConversationSplit",
        "EvalNotPassedError",
    ],
    "Foundry evals": ["FoundryEvals", "FoundryChatClient"],
}

# Substrings to enumerate from each namespace so we catch renamed symbols.
SCAN_SUBSTRINGS = [
    "agent",
    "thread",
    "session",
    "middleware",
    "context",
    "tool",
    "eval",
    "workflow",
]


def _load_modules() -> dict[str, object]:
    loaded: dict[str, object] = {}
    for name in SUBMODULES:
        try:
            loaded[name] = importlib.import_module(name)
        except Exception as e:  # noqa: BLE001
            loaded[name] = e
    return loaded


def _find(symbol: str, modules: dict[str, object]) -> tuple[str, object] | None:
    for mod_name, mod in modules.items():
        if isinstance(mod, Exception):
            continue
        if hasattr(mod, symbol):
            return mod_name, getattr(mod, symbol)
    return None


def _sig(obj: object) -> str:
    try:
        if inspect.isclass(obj):
            return f"class {obj.__name__}{inspect.signature(obj.__init__)}".replace("(self, ", "(")
        if callable(obj):
            return f"{getattr(obj, '__name__', 'callable')}{inspect.signature(obj)}"
        return type(obj).__name__
    except (ValueError, TypeError):
        return f"<{type(obj).__name__}, signature unavailable>"


def main() -> int:
    print("=== Microsoft Agent Framework — rc1 API probe ===\n")

    try:
        af = importlib.import_module("agent_framework")
    except Exception as e:  # noqa: BLE001
        print(f"agent-framework is NOT importable here: {e!r}")
        print("Run this in the environment where `pip install agent-framework` succeeded.")
        return 1

    version = getattr(af, "__version__", "unknown")
    print(f"agent_framework version: {version}")
    modules = _load_modules()
    for name, mod in modules.items():
        state = "ok" if not isinstance(mod, Exception) else f"MISSING ({type(mod).__name__})"
        print(f"  submodule {name}: {state}")
    print()

    pins: dict[str, str] = {}

    for topic, names in TOPICS.items():
        print(f"--- {topic} ---")
        first_found = None
        for symbol in names:
            hit = _find(symbol, modules)
            if hit:
                mod_name, obj = hit
                print(f"  [FOUND] {symbol:<28} in {mod_name}")
                if inspect.isclass(obj) or callable(obj):
                    print(f"          {_sig(obj)}")
                if first_found is None:
                    first_found = f"{mod_name}.{symbol}"
            else:
                print(f"  [   - ] {symbol}")
        if first_found:
            pins[topic] = first_found
        print()

    # Detail probes for the two highest-risk symbols.
    print("--- ChatAgent/Agent constructor + run methods ---")
    for cls_name in ("ChatAgent", "Agent"):
        hit = _find(cls_name, modules)
        if not hit:
            continue
        _, cls = hit
        print(f"  {cls_name}.__init__: {_sig(cls)}")
        for meth in ("run", "run_stream", "get_new_thread", "create_session"):
            if hasattr(cls, meth):
                try:
                    print(f"    .{meth}{inspect.signature(getattr(cls, meth))}")
                except (ValueError, TypeError):
                    print(f"    .{meth}(...)")
    print()

    # Enumerate anything we might have missed.
    print("--- namespace scan (names containing key substrings) ---")
    top = modules.get("agent_framework")
    if not isinstance(top, Exception):
        allnames = sorted(n for n in dir(top) if not n.startswith("_"))
        for sub in SCAN_SUBSTRINGS:
            hits = [n for n in allnames if sub in n.lower()]
            print(f"  *{sub}*: {', '.join(hits) if hits else '(none)'}")
    print()

    # Is there a fake/test chat client shipped?
    print("--- fake/test chat client search ---")
    found_fake = []
    top = modules.get("agent_framework")
    if not isinstance(top, Exception):
        for _, modname, _ in pkgutil.walk_packages(
            getattr(top, "__path__", []), "agent_framework."
        ):
            low = modname.lower()
            if any(k in low for k in ("test", "fake", "mock", "stub")):
                found_fake.append(modname)
    fake_msg = (
        ", ".join(found_fake) if found_fake else "(none found — write a ChatClientProtocol stub)"
    )
    print(f"  candidate modules: {fake_msg}")
    print()

    print("=== PIN THESE (copy back) ===")
    print(f"maf_version = {version!r}")
    for topic, pin in pins.items():
        print(f"{topic!r}: {pin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
