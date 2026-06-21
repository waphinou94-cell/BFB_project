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

    # Construire input et output selon le type de nœud
    tool_calls = getattr(last, "tool_calls", None) or []

    if tool_calls:
        # Nœud LLM qui décide d'appeler des tools
        # (state_update ne contient que l'AIMessage produit, pas l'historique en entrée)
        node_input = {}
        node_output = {
            "tool_calls": [
                {"name": tc["name"], "args": tc.get("args", {})}
                for tc in tool_calls
            ]
        }
        meta = {"has_tool_calls": True, "tools": [tc["name"] for tc in tool_calls]}
    elif last and type(last).__name__ == "ToolMessage":
        # Nœud tools : on regroupe les résultats par nom d'outil
        tool_results = {
            m.name: _extract_text(m.content)[:500]
            for m in msgs
            if type(m).__name__ == "ToolMessage" and hasattr(m, "name")
        }
        node_input = {"tool_names": list(tool_results.keys())}
        node_output = tool_results
        meta = {"has_tool_calls": False, "tools": list(tool_results.keys())}
    else:
        # Nœud LLM de synthèse finale (pas de tool_calls)
        node_input = {}
        node_output = {"answer": _extract_text(last.content)[:1000] if last else ""}
        meta = {"has_tool_calls": False}

    langfuse_context.update_current_observation(
        name=node_name,
        input=node_input,
        output=node_output,
        metadata=meta,
    )


# ─────────────────────────────────────────────
# Exécution d'un tour de conversation
# ─────────────────────────────────────────────

def _run_turn(agent, messages: list, mode: str) -> list:
    result = agent.invoke({"messages": messages})
    return result["messages"]


@observe()
def _run_turn_traced(agent, messages: list, mode: str) -> list:
    # Nom dynamique via update (pattern fiable Langfuse 2.x, évite le bug name=null
    # causé par @observe(name=...) appliqué sur une inner function/closure)
    user_input = _extract_text(messages[-1].content) if messages else ""
    langfuse_context.update_current_observation(
        name=f"bforbank-{mode}",
        input={"question": user_input},
        metadata={"mode": mode},
    )
    langfuse_context.update_current_trace(tags=[mode])

    accumulated = list(messages)
    for event in agent.stream({"messages": messages}, stream_mode="updates"):
        for node_name, state_update in event.items():
            if node_name.startswith("__"):
                continue
            _trace_node(node_name, state_update)
            if "messages" in state_update:
                accumulated.extend(state_update["messages"])

    # Output sur la trace racine = réponse finale
    if accumulated:
        langfuse_context.update_current_observation(
            output={"answer": _extract_text(accumulated[-1].content)[:1000]}
        )
    return accumulated


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
