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

from langfuse.decorators import observe  # noqa: E402


def _run_turn(agent, messages: list, mode: str) -> list:
    result = agent.invoke({"messages": messages})
    return result["messages"]


def _run_turn_traced(agent, messages: list, mode: str) -> list:
    @observe(name=f"bforbank-agent-{mode}")
    def _inner():
        result = agent.invoke({"messages": messages})
        return result["messages"]
    return _inner()


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

        print(f"\n🤖 Agent : {conversation_history[-1].content}")
        print("─" * 60)


if __name__ == "__main__":
    main()
