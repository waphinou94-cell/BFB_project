"""
Agent BforBank — Mode ReAct (LangGraph prebuilt)

create_react_agent implémente automatiquement la boucle observe → think → act.
Le LLM décide librement de l'ordre et de la combinaison des outils.
"""

from langgraph.prebuilt import create_react_agent

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
3. Synthétise une réponse argumentée qui croise les deux sources si nécessaire
4. Cite toujours la source de procédure utilisée (lien Confluence)

Réponds toujours en français, de manière professionnelle et concise."""


def build_react_agent():
    llm = get_llm()
    tools = [retrieve_procedures, query_client_data]
    return create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)
