"""Service layer: business logic orchestrated above repositories.

Services are the only layer that may combine repositories; routes stay thin
and delegate here. Phase 2 will extend these services with AI analysis.
"""

from __future__ import annotations