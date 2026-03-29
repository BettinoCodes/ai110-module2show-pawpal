"""
PawPal+ — logic layer
Four core classes: Task, Pet, Owner, Scheduler.

Phase 3 additions:
  - Task: start_time (HH:MM), frequency ("once"/"daily"/"weekly"), due_date,
          next_occurrence()
  - Pet:  complete_task() handles recurring task spawning
  - Scheduler: sort_by_time(), filter_tasks(), detect_conflicts()
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, timedelta
from collections import defaultdict
from typing import Optional


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet-care activity with duration, priority, scheduling metadata,
    and optional recurrence."""

    name: str
    category: str           # e.g. "walk", "feed", "meds", "grooming", "enrichment"
    duration_minutes: int
    priority: int           # 1 (lowest) – 5 (highest)
    preferred_time: Optional[str] = None   # "morning", "afternoon", "evening", or None
    start_time: Optional[str] = None       # "HH:MM" for precise scheduling / conflict detection
    frequency: str = "once"                # "once", "daily", "weekly"
    due_date: Optional[date] = None        # concrete due date; None means today
    completed: bool = False

    def is_schedulable(self, remaining_minutes: int) -> bool:
        """Return True if this task fits within the remaining time budget."""
        return self.duration_minutes <= remaining_minutes

    def mark_complete(self) -> None:
        """Mark this task as done for the current occurrence."""
        self.completed = True

    def next_occurrence(self) -> Task:
        """Return a fresh, incomplete copy of this task for the next recurrence.

        Uses timedelta to calculate the next due date:
          - daily  -> today + 1 day
          - weekly -> today + 7 days
        """
        base = self.due_date if self.due_date else date.today()
        delta = timedelta(days=1) if self.frequency == "daily" else timedelta(weeks=1)
        return Task(
            name=self.name,
            category=self.category,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            preferred_time=self.preferred_time,
            start_time=self.start_time,
            frequency=self.frequency,
            due_date=base + delta,
        )

    def __str__(self) -> str:
        """Return a human-readable one-line summary of the task."""
        status = "[x]" if self.completed else "[ ]"
        time_note = f" [{self.start_time}]" if self.start_time else (
            f" [{self.preferred_time}]" if self.preferred_time else ""
        )
        recur = f" ({self.frequency})" if self.frequency != "once" else ""
        return (
            f"  {status} {self.name:<24}"
            f"{self.category:<12}"
            f"{self.duration_minutes:>3} min   "
            f"priority {self.priority}"
            f"{time_note}{recur}"
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

    def complete_task(self, task_name: str) -> Optional[Task]:
        """Mark a task complete by name.

        If the task is recurring (daily or weekly), automatically appends the
        next occurrence to this pet's task list and returns it.
        Returns None if the task is non-recurring or not found.
        """
        for task in self._tasks:
            if task.name.lower() == task_name.lower():
                task.mark_complete()
                if task.frequency != "once":
                    next_task = task.next_occurrence()
                    self._tasks.append(next_task)
                    return next_task
                return None
        return None

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
    """The scheduling brain: retrieves tasks from all of the owner's pets,
    sorts/filters them, detects conflicts, and builds a daily plan."""

    owner: Owner

    # --- Sorting -----------------------------------------------------------

    def filter_by_priority(self) -> list[Task]:
        """Return all tasks across all pets, sorted highest priority first."""
        return sorted(self.owner.get_all_tasks(), key=lambda t: t.priority, reverse=True)

    def sort_by_time(self) -> list[Task]:
        """Return all tasks sorted by start_time (HH:MM, ascending).

        Tasks without a start_time sort to the end ("99:99" sentinel).
        Because HH:MM strings compare lexicographically in the same order as
        chronologically, a plain string sort is both simple and correct.
        """
        return sorted(
            self.owner.get_all_tasks(),
            key=lambda t: t.start_time if t.start_time else "99:99",
        )

    # --- Filtering ---------------------------------------------------------

    def filter_tasks(
        self,
        *,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
    ) -> list[Task]:
        """Filter tasks by pet name and/or completion status.

        Args:
            pet_name:  If given, only include tasks for that pet (case-insensitive).
            completed: If True, only completed tasks; if False, only pending.
                       If None, no completion filter is applied.
        Returns:
            Flat list of matching Task objects.
        """
        results: list[Task] = []
        for pet in self.owner.get_pets():
            if pet_name and pet.name.lower() != pet_name.lower():
                continue
            for task in pet.get_tasks():
                if completed is not None and task.completed != completed:
                    continue
                results.append(task)
        return results

    # --- Conflict detection ------------------------------------------------

    def detect_conflicts(self) -> list[str]:
        """Detect tasks that share the same start_time slot.

        Strategy: bucket all tasks by start_time; any bucket with more than
        one entry is a conflict.  Returns a list of human-readable warning
        strings — never raises, so the app stays running.

        Tradeoff: only exact start_time equality is checked, not overlapping
        durations.  This is lightweight and easy to reason about; detecting
        true overlaps would require computing end times and interval
        intersection, which adds complexity for limited benefit in a daily
        planner used by a single owner.
        """
        buckets: dict[str, list[tuple[str, Task]]] = defaultdict(list)
        for pet in self.owner.get_pets():
            for task in pet.get_tasks():
                if task.start_time:
                    buckets[task.start_time].append((pet.name, task))

        warnings: list[str] = []
        for time_slot, entries in sorted(buckets.items()):
            if len(entries) > 1:
                desc = ", ".join(
                    f"'{pet_name}: {task.name}'" for pet_name, task in entries
                )
                warnings.append(f"CONFLICT at {time_slot} -> {desc}")
        return warnings

    # --- Plan generation ---------------------------------------------------

    def generate_plan(self) -> list[Task]:
        """Build an ordered list of incomplete tasks that fit within
        owner.available_minutes. Higher-priority tasks are chosen first."""
        remaining = self.owner.available_minutes
        plan: list[Task] = []
        for task in self.filter_by_priority():
            if not task.completed and task.is_schedulable(remaining):
                plan.append(task)
                remaining -= task.duration_minutes
        return plan

    def explain_plan(self) -> str:
        """Return a plain-language explanation of every scheduling decision."""
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
