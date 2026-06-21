"""Tool Text-to-SQL avec boucle de self-correction (max 3 tentatives)."""

import psycopg
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool

from src.config import settings
from src.llm_factory import get_llm
from src.tools.schema_inspector import get_schema

_SQL_GENERATION_PROMPT = """Tu es un expert SQL PostgreSQL pour une base bancaire.
Génère UNIQUEMENT une requête SQL valide — pas de markdown, pas d'explication, juste le SQL.

Schéma disponible :
{schema}

Règles :
- Utilise uniquement les tables et colonnes du schéma ci-dessus
- Pour chercher un client par nom ou prénom, utilise ILIKE (insensible à la casse)
- montant négatif = débit, montant positif = crédit
- Nomme les colonnes de résultat explicitement (évite SELECT *)
- Si la question porte sur plusieurs clients, utilise un JOIN ou une sous-requête"""

_SQL_CORRECTION_PROMPT = """La requête SQL suivante a échoué. Génère une version corrigée.
Renvoie UNIQUEMENT le SQL corrigé — pas de markdown, pas d'explication.

SQL ayant échoué :
{sql}

Erreur PostgreSQL :
{error}

Question originale : {question}"""


def _conn_string() -> str:
    return settings.database_url.replace("postgresql+psycopg://", "postgresql://")


def _extract_text(content) -> str:
    """Normalise le contenu LLM : Gemini renvoie parfois une liste de blocs."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                parts.append(part.get("text", ""))
        return "".join(parts).strip()
    return str(content).strip()


def _generate_sql(llm, question: str) -> str:
    messages = [
        SystemMessage(content=_SQL_GENERATION_PROMPT.format(schema=get_schema())),
        HumanMessage(content=question),
    ]
    return _extract_text(llm.invoke(messages).content)


def _correct_sql(llm, sql: str, error: str, question: str) -> str:
    messages = [
        SystemMessage(
            content=_SQL_CORRECTION_PROMPT.format(sql=sql, error=error, question=question)
        ),
    ]
    return _extract_text(llm.invoke(messages).content)


def _execute_sql(sql: str) -> list[dict]:
    with psycopg.connect(_conn_string()) as conn:
        cur = conn.execute(sql)
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# Colonnes PII de la table clients — jamais transmises au LLM
# Le LLM n'en a pas besoin : il connaît déjà le client via la question du conseiller
_PII_COLUMNS = {"nom", "prenom", "email", "telephone", "date_naissance"}


def _strip_pii(rows: list[dict]) -> list[dict]:
    return [{k: v for k, v in row.items() if k not in _PII_COLUMNS} for row in rows]


def _format_rows(rows: list[dict]) -> str:
    if not rows:
        return "La requête n'a retourné aucun résultat."
    return "\n".join(" | ".join(f"{k}: {v}" for k, v in row.items()) for row in rows)


@tool
def query_client_data(question: str) -> str:
    """Interroge la base de données transactionnelle BforBank pour répondre à une question sur un client.

    Utiliser pour toute question nécessitant des données réelles : solde, historique
    de transactions, analyse financière, détection d'anomalies sur un compte client.

    Args:
        question: Question en langage naturel sur les données client.

    Returns:
        Les données extraites de la base de données, ou un message d'erreur si
        la requête échoue après 3 tentatives de self-correction.
    """
    llm = get_llm()
    sql = _generate_sql(llm, question)
    last_error = ""

    for attempt in range(3):
        try:
            rows = _strip_pii(_execute_sql(sql))
            result = _format_rows(rows)
            return f"SQL exécuté (tentative {attempt + 1}):\n```sql\n{sql}\n```\n\nRésultats:\n{result}"
        except Exception as e:
            last_error = str(e)
            if attempt < 2:
                sql = _correct_sql(llm, sql, last_error, question)

    return (
        f"Échec après 3 tentatives de self-correction.\n"
        f"Dernière erreur : {last_error}\n"
        f"Dernier SQL :\n```sql\n{sql}\n```"
    )
