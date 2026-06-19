"""
CLI BforBank Agent — Point d'entrée unifié

Usage :
    uv run python src/agent/cli.py                   # ReAct par défaut
    uv run python src/agent/cli.py --mode react
    uv run python src/agent/cli.py --mode langgraph
"""

import argparse

from langchain_core.messages import HumanMessage

from src.config import settings


def _get_langfuse_callback():
    """Retourne le callback Langfuse si configuré, sinon None."""
    if not settings.langfuse_enabled:
        return None
    from langfuse.callback import CallbackHandler
    return CallbackHandler(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


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

    langfuse_cb = _get_langfuse_callback()
    run_config = {"callbacks": [langfuse_cb]} if langfuse_cb else {}

    conversation_history: list = []

    print(f"\n🏦 BforBank Agent — Mode : {args.mode.upper()}")
    print(f"   Modèle : {settings.llm_model} [{settings.llm_provider}]")
    if langfuse_cb:
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
        result = agent.invoke({"messages": conversation_history}, config=run_config)
        conversation_history = result["messages"]

        print(f"\n🤖 Agent : {result['messages'][-1].content}")
        print("─" * 60)


if __name__ == "__main__":
    main()
