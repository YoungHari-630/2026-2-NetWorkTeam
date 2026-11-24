"""Shared API request and topology models."""

from pydantic import BaseModel, Field


class Router(BaseModel):
    """A router identified by a stable, case-sensitive ID."""

    id: str = Field(min_length=1)


class Link(BaseModel):
    """An undirected network link between two routers."""

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    cost: int = Field(gt=0)
    active: bool


class Topology(BaseModel):
    """The complete network state exchanged by the API."""

    routers: list[Router]
    links: list[Link]


class LinkToggleRequest(BaseModel):
    link_id: str = Field(min_length=1)


class RouteRequest(BaseModel):
    source: str = Field(min_length=1)
    destination: str = Field(min_length=1)


class RouteResult(BaseModel):
    source: str
    destination: str
    path: list[str]
    total_cost: int | None
    reachable: bool


class SimulationEvent(BaseModel):
    event_id: str
    step: int
    event_type: str
    router_id: str | None = None
    source: str | None = None
    destination: str | None = None
    related_link: str | None = None
    previous_state: bool | None = None
    new_state: bool | None = None
    description: str


class SimulationEventList(BaseModel):
    events: list[SimulationEvent]
