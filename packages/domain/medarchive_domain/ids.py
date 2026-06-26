from __future__ import annotations

from uuid import UUID, uuid4


def new_id() -> UUID:
    """Create a domain UUID.

    Kept as a tiny helper so tests can inject deterministic IDs later without
    leaking infrastructure concerns into entities.
    """

    return uuid4()
