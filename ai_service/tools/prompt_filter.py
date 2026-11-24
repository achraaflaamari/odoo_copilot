# -*- coding: utf-8 -*-
"""
Module de filtrage des injections de prompt.
Protège le microservice contre les tentatives de manipulation du LLM
via des instructions malveillantes dans les entrées utilisateur.
"""

import logging
import re

logger = logging.getLogger(__name__)

# ─────────────────────── Patterns d'injection connus ─────────────────────────

# Séquences typiques d'injection de prompt (insensible à la casse)
_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions?", re.I),
    re.compile(r"you\s+are\s+now\s+", re.I),
    re.compile(r"forget\s+(everything|all)\s+(you\s+)?(know|were told)", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a)\s+", re.I),
    re.compile(r"new\s+instructions?\s*:", re.I),
    re.compile(r"\[SYSTEM\]", re.I),
    re.compile(r"<\s*/?system\s*>", re.I),
    re.compile(r"###\s*instruction", re.I),
    re.compile(r"prompt\s*injection", re.I),
    re.compile(r"révèle\s+(ton|le)\s+(prompt|système|system)", re.I),
    re.compile(r"affiche\s+(tes|les)\s+instructions", re.I),
    re.compile(r"ignore\s+(toutes?\s+)?(les\s+)?(instructions?|règles?)\s+(précédentes?|ci-dessus)", re.I),
    re.compile(r"tu\s+es\s+maintenant\s+", re.I),
    re.compile(r"oublie\s+(tout|toutes?\s+les\s+(instructions?|règles?))", re.I),
    re.compile(r"(nouvelles?|new)\s+r[eè]gles?\s*:", re.I),
]

# Longueur maximale d'une question (protection contre les DoS et les injections longues)
MAX_QUESTION_LENGTH: int = 2000


def sanitize_question(question: str) -> tuple[str, bool]:
    """Nettoie et valide une question utilisateur avant envoi au LLM.

    La fonction :
    1. Tronque les questions trop longues.
    2. Supprime les balises HTML/XML basiques.
    3. Détecte les patterns d'injection de prompt connus.

    Args:
        question: Question brute saisie par l'utilisateur.

    Returns:
        Tuple (question_nettoyée, injection_détectée).
        - question_nettoyée : chaîne sûre à envoyer au LLM.
        - injection_détectée : True si un pattern d'injection a été trouvé.
    """
    if not question:
        return "", False

    # 1. Troncature
    if len(question) > MAX_QUESTION_LENGTH:
        logger.warning(
            "Question tronquée : longueur %d > %d", len(question), MAX_QUESTION_LENGTH
        )
        question = question[:MAX_QUESTION_LENGTH]

    # 2. Suppression des balises HTML/XML (ne pas interpréter comme instructions)
    question_clean = re.sub(r"<[^>]{0,200}>", "", question)

    # 3. Détection d'injection
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(question_clean):
            logger.warning(
                "Injection de prompt détectée — pattern : %s", pattern.pattern
            )
            return question_clean, True

    return question_clean, False


def is_safe_question(question: str) -> bool:
    """Retourne True si la question ne contient pas d'injection détectée.

    Args:
        question: Question à vérifier.

    Returns:
        True si sûre, False si injection suspectée.
    """
    _, injected = sanitize_question(question)
    return not injected
