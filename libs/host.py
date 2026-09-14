"""Is a Houdini GUI hosting this process? The only place that answers it.

No other imports so both the pure domain layer and Qt code can depend on it.
"""

from __future__ import annotations

try:
    import hou

    IS_HOUDINI = bool(hou.isUIAvailable())
except Exception:  # hou missing (tests, hython without UI) or not initialised
    IS_HOUDINI = False
