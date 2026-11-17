"""In-memory link state operations used by the API."""

from copy import deepcopy
from typing import Any


TopologyData = dict[str, Any]


def toggle_link(topology: TopologyData, link_id: str) -> TopologyData:
    """Return a copy of topology with the selected link's state inverted.

    Raises:
        KeyError: If ``link_id`` is not present in the topology.
    """

    updated = deepcopy(topology)
    for link in updated["links"]:
        if link["id"] == link_id:
            link["active"] = not link["active"]
            return updated
    raise KeyError(link_id)


def reset_topology(initial_topology: TopologyData) -> TopologyData:
    """Return a fresh copy of the initial topology."""

    return deepcopy(initial_topology)
