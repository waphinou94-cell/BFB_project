"""
Agent BforBank — Mode LangGraph (StateGraph fan-out conditionnel)

Architecture :
  router → rag_node  ↘
         → sql_node   → synthesis
         → synthesis  (direct, sans outil)

En mode "both", rag_node et sql_node tournent en parallèle.
Trade-off assumé : vitesse max, mais la query RAG est construite
depuis la question initiale — sans voir les résultats SQL.
Idéal pour les questions où les deux besoins sont explicites d'emblée.
"""

from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel
from typing_extensions import TypedDict

from src.llm_factory import get_llm
from src.indexer.retriever import retrieve
from src.tools.sql_tool import query_client_data

# ─── State ────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages:     Annotated[list, add_messages]
    route:        str
    rag_query:    str
    sql_question: str
    rag_result:   str
    sql_result:   str


# ─── Prompts ──────────────────────────────────────────────────────────────────

_ROUTER_PROMPT = """Tu es le routeur d'un agent bancaire. Analyse la question et décide quels outils utiliser.

Outils disponibles :
- "rag"    : procédures internes BforBank (remboursement frais, litige CB, opposition carte, solvabilité)
- "sql"    : données client en base (solde, transactions, historique)
- "both"   : les deux outils nécessaires
- "direct" : réponse sans outil (question générale)

Si tu choisis "rag" ou "both", fournis une rag_query précise pour la recherche documentaire.
Si tu choisis "sql" ou "both", reformule la question pour la requête SQL."""

_SYNTHESIS_PROMPT = """Tu es un assistant IA copilote pour les conseillers clientèle de BforBank.

Synthétise une réponse argumentée à partir des informations disponibles.
Cite la procédure de référence si disponible (lien Confluence).
Réponds en français, de manière professionnelle et concise.

{context}"""


# ─── Router schema ────────────────────────────────────────────────────────────

class RouteDecision(BaseModel):
    route:        Literal["rag", "sql", "both", "direct"]
    rag_query:    str = ""
    sql_question: str = ""


# ─── Nodes ────────────────────────────────────────────────────────────────────

def _make_router(llm):
    router_llm = llm.with_structured_output(RouteDecision)

    def router(state: AgentState) -> dict:
        question = state["messages"][-1].content
        decision = router_llm.invoke([
            SystemMessage(content=_ROUTER_PROMPT),
            HumanMessage(content=question),
        ])
        return {
            "route":        decision.route,
            "rag_query":    decision.rag_query or question,
            "sql_question": decision.sql_question or question,
        }
    return router


def rag_node(state: AgentState) -> dict:
    results = retrieve(state["rag_query"], k=5)
    if not results:
        return {"rag_result": "Aucune procédure trouvée."}
    parts = [
        f"### Procédure {i+1} [Source: {r['source']}]\n{r['content']}"
        for i, r in enumerate(results)
    ]
    return {"rag_result": "\n\n---\n\n".join(parts)}


def sql_node(state: AgentState) -> dict:
    result = query_client_data.invoke(state["sql_question"])
    return {"sql_result": result}


def _make_synthesis(llm):
    def synthesis(state: AgentState) -> dict:
        question = state["messages"][-1].content
        parts = []
        if state.get("rag_result"):
            parts.append(f"## Procédures BforBank\n{state['rag_result']}")
        if state.get("sql_result"):
            parts.append(f"## Données client\n{state['sql_result']}")
        context = "\n\n".join(parts) if parts else "Aucune donnée disponible."

        response = llm.invoke([
            SystemMessage(content=_SYNTHESIS_PROMPT.format(context=context)),
            HumanMessage(content=question),
        ])
        return {"messages": [response]}
    return synthesis


# ─── Routing function ─────────────────────────────────────────────────────────

def _route(state: AgentState) -> list[str]:
    route = state["route"]
    if route == "rag":
        return ["rag_node"]
    elif route == "sql":
        return ["sql_node"]
    elif route == "both":
        return ["rag_node", "sql_node"]   # exécution parallèle
    else:
        return ["synthesis"]


# ─── Graph ────────────────────────────────────────────────────────────────────

def build_langgraph_agent():
    llm = get_llm()

    graph = StateGraph(AgentState)
    graph.add_node("router",    _make_router(llm))
    graph.add_node("rag_node",  rag_node)
    graph.add_node("sql_node",  sql_node)
    graph.add_node("synthesis", _make_synthesis(llm))

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", _route, ["rag_node", "sql_node", "synthesis"])
    graph.add_edge("rag_node",  "synthesis")
    graph.add_edge("sql_node",  "synthesis")
    graph.add_edge("synthesis", END)

    return graph.compile()
