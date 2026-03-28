"""
PawPal+ — logic layer
Class skeletons generated from UML. Logic to be implemented in later phases.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet-care activity with a duration and priority."""

    name: str
    category: str          # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    duration_minutes: int
    priority: int          # 1 (lowest) – 5 (highest)
    preferred_time: Optional[str] = None  # e.g. "morning", "evening", or None

    def is_schedulable(self, remaining_minutes: int) -> bool:
        """Return True if this task fits within the remaining time budget."""
        pass


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """A pet belonging to an owner, with its own list of care tasks."""

    name: str
    species: str           # e.g. "dog", "cat", "rabbit"
    age: int               # in years
    breed: str = ""
    _tasks: list[Task] = field(default_factory=list, repr=False)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        pass

    def remove_task(self, task_name: str) -> None:
        """Remove a task by name."""
        pass

    def get_tasks(self) -> list[Task]:
        """Return all tasks associated with this pet."""
        pass


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """The pet owner, tracking their available time and preferences."""

    name: str
    available_minutes: int          # total daily time budget for pet care
    preferences: list[str] = field(default_factory=list)  # e.g. ["no early walks"]
    _pets: list[Pet] = field(default_factory=list, repr=False)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        pass

    def set_available_time(self, minutes: int) -> None:
        """Update how many minutes per day the owner can dedicate to pet care."""
        pass

    def get_pets(self) -> list[Pet]:
        """Return all pets owned by this owner."""
        pass


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

@dataclass
class Scheduler:
    """
    Generates a prioritized daily care plan for a pet, respecting the
    owner's available time budget.
    """

    owner: Owner
    pet: Pet

    def filter_by_priority(self) -> list[Task]:
        """Return the pet's tasks sorted by priority (highest first)."""
        pass

    def generate_plan(self) -> list[Task]:
        """
        Build an ordered list of tasks that fit within owner.available_minutes.
        Higher-priority tasks are scheduled first; tasks that don't fit are
        omitted.
        """
        pass

    def explain_plan(self) -> str:
        """
        Return a plain-language explanation of why the generated plan
        includes or excludes each task.
        """
        pass
