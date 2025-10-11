"""Activity domain package.

Struttura domain-driven per gestione Activity & Health Tracking:

Layers previsti:
  * model: Value Objects e Aggregate roots
  * ports: Interfacce astratte verso infrastruttura
  * application: Servizi di orchestrazione (Sync, Aggregation, Calculation)
  * integration: Bridge/feature flag con GraphQL layer esistente (ACTIVITY_DOMAIN_V2)

Fase corrente: bootstrap modelli + pianificazione architettura.
"""

from __future__ import annotations

ACTIVITY_DOMAIN_FEATURE_FLAG = "ACTIVITY_DOMAIN_V2"

__all__ = ["ACTIVITY_DOMAIN_FEATURE_FLAG"]
