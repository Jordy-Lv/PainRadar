"""Enumeraciones compartidas por el modelo de datos y el pipeline."""

from __future__ import annotations

from enum import StrEnum


class Track(StrEnum):
    """Los dos carriles del radar.

    SALES busca trabajo pagado; CONTRIB busca gente a la que ayudar en abierto.
    Comparten pipeline pero no criterio: en SALES gana el presupuesto, en
    CONTRIB gana la reputación.
    """

    SALES = "sales"
    CONTRIB = "contrib"


class DraftKind(StrEnum):
    PROPOSAL = "proposal"  # propuesta comercial (track sales)
    REPLY = "reply"  # respuesta técnica pública (track contrib)


class OutcomeStatus(StrEnum):
    NEW = "new"
    NOTIFIED = "notified"
    DISCARDED = "discarded"
    # track sales
    APPLIED = "applied"
    REPLIED = "replied"
    WON = "won"
    LOST = "lost"
    # track contrib
    ANSWERED = "answered"  # publiqué una respuesta / comentario
    ACCEPTED = "accepted"  # la respuesta fue aceptada / el PR se mergeó
    IGNORED = "ignored"  # publiqué y no pasó nada
