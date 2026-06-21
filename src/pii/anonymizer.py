"""
Protection PII — masquage avant envoi aux APIs LLM.

Approche : recognizers pattern-based (regex) + deny-list de noms connus.
Même logique que Microsoft Presidio (pattern recognizers), sans la dépendance
spacy qui n'est pas encore compatible Python 3.14.

En production sur Python ≤ 3.13 : remplacer par Presidio + fr_core_news_sm
pour la détection NER des noms propres inconnus.
"""

import re
from dataclasses import dataclass, field


# Entités détectées et leurs patterns regex
_PATTERNS: dict[str, str] = {
    "IBAN":      r'\b[A-Z]{2}\d{2}(?:[\s]?\d{4}){4,6}(?:[\s]?\d{1,3})?\b',
    "CARTE":     r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b',
    "TELEPHONE": r'\b0[1-9](?:[\s\-\.]?\d{2}){4}\b',
    "EMAIL":     r'\b[\w.+-]+@[\w\-]+\.[a-z]{2,}\b',
}


@dataclass
class PIIAnonymizer:
    """
    Masque les PII d'un texte avant envoi au LLM.

    known_names : noms de clients connus (deny-list), ex. ["Marie Martin", "Jean Dupont"].
                  Les noms les plus longs sont remplacés en premier pour éviter
                  les collisions ("Martin" avant "M").
    """
    known_names: list[str] = field(default_factory=list)

    def anonymize(self, text: str) -> str:
        """Remplace les PII par des tokens [ENTITE_N]. Retourne le texte masqué."""
        counters: dict[str, int] = {}

        # 1. Patterns structurés en premier — protège les emails avant que les prénoms
        #    qu'ils contiennent ne soient remplacés individuellement
        for entity, pattern in _PATTERNS.items():
            def _replace(m, entity=entity, counters=counters):
                counters[entity] = counters.get(entity, 0) + 1
                return f"[{entity}_{counters[entity]}]"
            text = re.sub(pattern, _replace, text, flags=re.IGNORECASE)

        # 2. Noms connus — du plus long au plus court (évite les substitutions partielles)
        for name in sorted(self.known_names, key=len, reverse=True):
            if re.search(r'\b' + re.escape(name) + r'\b', text, re.IGNORECASE):
                counters["PERSONNE"] = counters.get("PERSONNE", 0) + 1
                token = f"[PERSONNE_{counters['PERSONNE']}]"
                text = re.sub(r'\b' + re.escape(name) + r'\b', token, text, flags=re.IGNORECASE)

        return text
