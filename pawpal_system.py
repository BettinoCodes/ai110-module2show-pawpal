"""
PawPal+ — logic layer
Four core classes: Task, Pet, Owner, Scheduler.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet-care activity with a duration, priority, and completion state."""

    name: str
    category: str           # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    duration_minutes: int
    priority: int           # 1 (lowest) – 5 (highest)
    preferred_time: Optional[str] = None   # e.g. "morning", "evening", or None
    completed: bool = False

    def is_schedulable(self, remaining_minutes: int) -> bool:
        """Return True if this task fits within the remaining time budget."""
        return self.duration_minutes <= remaining_minutes

    def mark_complete(self) -> None:
        """Mark this task as done for today."""
        self.completed = True

    def __str__(self) -> str:
        """Return a human-readable one-line summary of the task."""
        status = "[x]" if self.completed else "[ ]"
        time_note = f" [{self.preferred_time}]" if self.preferred_time else ""
        return (
            f"  {status} {self.name:<22} "
            f"{self.category:<12} "
            f"{self.duration_minutes:>3} min   "
            f"priority {self.priority}"
            f"{time_note}"
        )


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    """A pet belonging to an owner, with its own list of care tasks."""

    name: str
    species: str            # e.g. "dog", "cat", "rabbit"
    age: int                # in years
    breed: str = ""
    _tasks: list[Task] = field(default_factory=list, repr=False)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        self._tasks.append(task)

    def remove_task(self, task_name: str) -> None:
        """Remove the first task whose name matches task_name (case-insensitive)."""
        self._tasks = [t for t in self._tasks if t.name.lower() != task_name.lower()]

    def get_tasks(self) -> list[Task]:
        """Return a copy of all tasks associated with this pet."""
        return list(self._tasks)

    def __str__(self) -> str:
        """Return a short description of the pet."""
        breed = f" ({self.breed})" if self.breed else ""
        return f"{self.name}{breed} - {self.age}-yr-old {self.species}"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """The pet owner, tracking their pets, available time, and preferences."""

    name: str
    available_minutes: int          # total daily time budget for pet care
    preferences: list[str] = field(default_factory=list)
    _pets: list[Pet] = field(default_factory=list, repr=False)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        self._pets.append(pet)

    def set_available_time(self, minutes: int) -> None:
        """Update how many minutes per day the owner can dedicate to pet care."""
        self.available_minutes = minutes

    def get_pets(self) -> list[Pet]:
        """Return a copy of all pets owned by this owner."""
        return list(self._pets)

    def get_all_tasks(self) -> list[Task]:
        """Collect and return every task across all of the owner's pets."""
        tasks: list[Task] = []
        for pet in self._pets:
            tasks.extend(pet.get_tasks())
        return tasks


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

@dataclass
class Scheduler:
    """
    The scheduling brain: retrieves tasks from all of the owner's pets,
    sorts by priority, and builds a daily plan that fits the time budget.
    """

    owner: Owner

    def filter_by_priority(self) -> list[Task]:
        """Return all tasks across all pets, sorted highest priority first."""
        return sorted(self.owner.get_all_tasks(), key=lambda t: t.priority, reverse=True)

    def generate_plan(self) -> list[Task]:
        """
        Build an ordered list of incomplete tasks that fit within
        owner.available_minutes. Higher-priority tasks are chosen first.
        """
        remaining = self.owner.available_minutes
        plan: list[Task] = []
        for task in self.filter_by_priority():
            if not task.completed and task.is_schedulable(remaining):
                plan.append(task)
                remaining -= task.duration_minutes
        return plan

    def explain_plan(self) -> str:
        """
        Return a plain-language explanation of every scheduling decision,
        showing which tasks are added, skipped, or already done.
        """
        remaining = self.owner.available_minutes
        lines = [
            f"Daily plan for {self.owner.name}  (budget: {self.owner.available_minutes} min)\n"
            + "-" * 60
        ]
        for task in self.filter_by_priority():
            if task.completed:
                lines.append(f"  SKIP  '{task.name}' - already completed today")
            elif task.is_schedulable(remaining):
                remaining -= task.duration_minutes
                lines.append(
                    f"  ADD   '{task.name}' - {task.duration_minutes} min, "
                    f"priority {task.priority}  ({remaining} min left)"
                )
            else:
                lines.append(
                    f"  SKIP  '{task.name}' - needs {task.duration_minutes} min "
                    f"but only {remaining} min remain"
                )
        lines.append("-" * 60)
        return "\n".join(lines)
