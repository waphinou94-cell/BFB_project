"""
Agent BforBank — Squelette de base (Phase 2)

Agent conversationnel sans outils. Sert de fondation pour les phases suivantes
où les tools RAG et Text-to-SQL seront greffés sur ce graph.

Lancement : uv run python src/agent/agent.py
"""

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph

from src.config import settings
from src.llm_factory import get_llm

# ─────────────────────────────────────────────
# Prompt système
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un assistant IA copilote pour les conseillers clientèle de BforBank.

Ton rôle est d'aider les conseillers à traiter rapidement et précisément les demandes clients.
Tu as accès (prochainement) à deux sources d'information :
- Les procédures internes BforBank (remboursement de frais, litiges, oppositions carte, solvabilité)
- L'historique transactionnel des clients en base de données

Pour l'instant, réponds en te basant sur tes connaissances générales bancaires.
Indique clairement quand tu aurais besoin de données client ou de procédures précises pour répondre.

Réponds toujours en français, de manière professionnelle et concise.
"""


# ─────────────────────────────────────────────
# Construction du graph LangGraph
# ─────────────────────────────────────────────
def build_graph() -> StateGraph:
    llm = get_llm()

    def call_model(state: MessagesState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("model", call_model)
    graph.add_edge(START, "model")
    graph.add_edge("model", END)

    return graph.compile()


# ─────────────────────────────────────────────
# CLI interactif
# ─────────────────────────────────────────────
def main() -> None:
    agent = build_graph()
    conversation_history = []

    print("\n🏦 BforBank Agent — Copilote Conseiller")
    print(f"   Modèle : {settings.llm_model} [{settings.llm_provider}]")
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

        result = agent.invoke({"messages": conversation_history})

        # Mise à jour de l'historique avec la réponse complète
        conversation_history = result["messages"]

        ai_message = result["messages"][-1]
        print(f"\n🤖 Agent : {ai_message.content}")
        print("─" * 60)


if __name__ == "__main__":
    main()
