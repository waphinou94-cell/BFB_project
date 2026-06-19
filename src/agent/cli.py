"""
CLI BforBank Agent — Point d'entrée unifié

Usage :
    uv run python src/agent/cli.py                   # ReAct par défaut
    uv run python src/agent/cli.py --mode react
    uv run python src/agent/cli.py --mode langgraph
"""

import argparse
import os

from langchain_core.messages import HumanMessage

from src.config import settings

# Expose les clés Langfuse en variables d'environnement pour que le SDK les lise
if settings.langfuse_enabled:
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

from langfuse.decorators import langfuse_context, observe  # noqa: E402


def _extract_text(content) -> str:
    """Normalise le contenu LLM : Gemini/Vertex renvoie parfois une liste de blocs."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            p if isinstance(p, str) else p.get("text", "") if isinstance(p, dict) else ""
            for p in content
        )
    return str(content)


# ─────────────────────────────────────────────
# Tracing d'un nœud LangGraph comme span enfant
# ─────────────────────────────────────────────

@observe()
def _trace_node(node_name: str, state_update: dict) -> None:
    """Crée un span Langfuse pour un nœud du graph."""
    msgs = state_update.get("messages", [])
    last = msgs[-1] if msgs else None
    langfuse_context.update_current_observation(
        name=node_name,
        input={"node": node_name, "n_messages": len(msgs)},
        output={"content": _extract_text(last.content)[:1000]} if last else {},
        metadata={
            "message_type": type(last).__name__ if last else None,
            "tool_calls": bool(getattr(last, "tool_calls", None)),
        },
    )


# ─────────────────────────────────────────────
# Exécution d'un tour de conversation
# ─────────────────────────────────────────────

def _run_turn(agent, messages: list, mode: str) -> list:
    result = agent.invoke({"messages": messages})
    return result["messages"]


def _run_turn_traced(agent, messages: list, mode: str) -> list:
    @observe(name=f"bforbank-{mode}")
    def _inner():
        # stream_mode="updates" → {node_name: state_update} à chaque nœud exécuté
        accumulated = list(messages)
        for event in agent.stream({"messages": messages}, stream_mode="updates"):
            for node_name, state_update in event.items():
                if node_name.startswith("__"):
                    continue
                _trace_node(node_name, state_update)
                if "messages" in state_update:
                    accumulated.extend(state_update["messages"])
        return accumulated

    return _inner()


# ─────────────────────────────────────────────
# CLI principal
# ─────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="BforBank Agent CLI")
    parser.add_argument(
        "--mode",
        choices=["react", "langgraph"],
        default="react",
        help="Stratégie d'agent : react (prebuilt) ou langgraph (StateGraph custom)",
    )
    args = parser.parse_args()

    if args.mode == "react":
        from src.agent.agent_react import build_react_agent
        agent = build_react_agent()
    else:
        from src.agent.agent_langgraph import build_langgraph_agent
        agent = build_langgraph_agent()

    run_turn = _run_turn_traced if settings.langfuse_enabled else _run_turn

    conversation_history: list = []

    print(f"\n🏦 BforBank Agent — Mode : {args.mode.upper()}")
    print(f"   Modèle : {settings.llm_model} [{settings.llm_provider}]")
    if settings.langfuse_enabled:
        print(f"   Traces : {settings.langfuse_host}")
    print("   Tapez 'exit' ou 'quit' pour quitter.\n")
    print("─" * 60)

    while True:
        try:
            user_input = input("\n👤 Conseiller : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nAu revoir.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Au revoir.")
            break

        conversation_history.append(HumanMessage(content=user_input))
        conversation_history = run_turn(agent, conversation_history, args.mode)

        print(f"\n🤖 Agent : {_extract_text(conversation_history[-1].content)}")
        print("─" * 60)


if __name__ == "__main__":
    main()
