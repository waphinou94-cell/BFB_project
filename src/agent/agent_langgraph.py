"""
Agent BforBank — Mode LangGraph (StateGraph custom)

Implémente la même logique que le mode ReAct mais avec un StateGraph explicite :
chaque nœud et chaque arête conditionnelle est visible et modifiable.

Différence clé vs ReAct :
- Flux de contrôle entièrement défini par le développeur
- Facilité pour ajouter des nœuds spécialisés (ex: nœud de synthèse dédié,
  garde-fous PII, logging structuré par étape)
- Le graphe Mermaid est exportable pour la documentation
"""

from typing import Literal

from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from src.llm_factory import get_llm
from src.tools.rag_tool import retrieve_procedures
from src.tools.sql_tool import query_client_data

SYSTEM_PROMPT = """Tu es un assistant IA copilote pour les conseillers clientèle de BforBank.

Ton rôle : aider les conseillers à traiter rapidement et précisément les demandes clients.

Tu disposes de deux outils :
- `retrieve_procedures` : recherche les procédures internes BforBank (règles métier, politiques de remboursement, litiges, opposition carte, solvabilité)
- `query_client_data` : interroge la base transactionnelle (solde, historique des transactions, données client)

Pour chaque demande :
1. Identifie si tu as besoin de procédures, de données client, ou des deux
2. Utilise les outils dans l'ordre le plus pertinent
3. Dans ta réponse finale, structure ta synthèse :
   - Procédure applicable (avec lien Confluence)
   - Données client pertinentes
   - Recommandation pour le conseiller

Réponds toujours en français, de manière professionnelle et concise."""

_TOOLS = [retrieve_procedures, query_client_data]


def _should_use_tools(state: MessagesState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


def build_langgraph_agent():
    llm = get_llm().bind_tools(_TOOLS)
    tool_node = ToolNode(_TOOLS)

    def call_model(state: MessagesState) -> dict:
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
        return {"messages": [llm.invoke(messages)]}

    graph = StateGraph(MessagesState)
    graph.add_node("call_model", call_model)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "call_model")
    graph.add_conditional_edges("call_model", _should_use_tools)
    graph.add_edge("tools", "call_model")

    return graph.compile()
