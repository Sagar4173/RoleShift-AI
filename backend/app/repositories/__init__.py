"""Data access layer: one repository per document type.

Repositories encapsulate all MongoDB access so routes and services never
touch the database directly. Swapping storage later means replacing only
this layer.
"""

from __future__ import annotations