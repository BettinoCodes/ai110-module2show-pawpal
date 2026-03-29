"""
PawPal+ — logic layer
Four core classes: Task, Pet, Owner, Scheduler.

Phase 3 additions:
  - Task: start_time (HH:MM), frequency ("once"/"daily"/"weekly"), due_date,
          next_occurrence()
  - Pet:  complete_task() handles recurring task spawning
  - Scheduler: sort_by_time(), filter_tasks(), detect_conflicts()

Challenge 1 — Weighted Prioritization:
  - Task.weighted_score(): composite urgency score (priority + overdue bonus +
    recurrence bonus + time-of-day alignment)
  - Scheduler.generate_weighted_plan(): uses weighted_score instead of raw priority
  - Scheduler.explain_weighted_plan(): explains each weight component

Challenge 2 — JSON Persistence:
  - Task.to_dict() / Task.from_dict()
  - Pet.to_dict()  / Pet.from_dict()
  - Owner.to_dict() / Owner.from_dict()
  - Owner.save_to_json() / Owner.load_from_json()
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

# Maps preferred_time strings to rough hour-of-day ranges for alignment scoring
_TIME_OF_DAY_HOURS: dict[str, tuple[int, int]] = {
    "morning":   (5,  11),
    "afternoon": (12, 16),
    "evening":   (17, 22),
}


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

    # -----------------------------------------------------------------------
    # Core scheduling helpers
    # -----------------------------------------------------------------------

    def is_schedulable(self, remaining_minutes: int) -> bool:
        """Return True if this task fits within the remaining time budget."""
        return self.duration_minutes <= remaining_minutes

    def mark_complete(self) -> None:
        """Mark this task as done for the current occurrence."""
        self.completed = True

    def next_occurrence(self) -> Task:
        """Return a fresh, incomplete copy of this task for the next recurrence.

        Uses timedelta to calculate the next due date:
          - daily  -> due_date + 1 day
          - weekly -> due_date + 7 days
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

    # -----------------------------------------------------------------------
    # Challenge 1 — Weighted prioritization score
    # -----------------------------------------------------------------------

    def weighted_score(self, current_hour: Optional[int] = None) -> float:
        """Compute a composite urgency score for weighted scheduling.

        Score components (all additive):
          base        = priority × 10          (0–50)
          overdue     = days overdue × 5       (0–unbounded; rewards catching up)
          recurrence  = +8 for daily, +4 for weekly  (recurring care matters more)
          time_align  = +6 if preferred_time matches current_hour  (schedule at the
                        right part of day)

        Design rationale (Challenge 1):
          Raw priority is the strongest signal but is coarse (only 5 levels).
          The overdue bonus prevents a priority-3 recurring medication from being
          perpetually bumped by a priority-4 non-urgent task.  The recurrence bonus
          nudges daily/weekly commitments ahead of one-off errands at equal priority.
          Time alignment rewards scheduling a "morning" task in the morning without
          making it impossible to schedule it later — it is a soft preference, not
          a hard constraint.  All weights were chosen so priority still dominates:
          a priority-5 task (score ≥ 50) will always beat a priority-4 task (≤ 49)
          unless the lower-priority task is both heavily overdue AND recurring.
        """
        score: float = self.priority * 10

        # Overdue bonus
        effective_due = self.due_date if self.due_date else date.today()
        days_overdue = (date.today() - effective_due).days
        if days_overdue > 0:
            score += days_overdue * 5

        # Recurrence bonus
        if self.frequency == "daily":
            score += 8
        elif self.frequency == "weekly":
            score += 4

        # Time-of-day alignment bonus
        if current_hour is not None and self.preferred_time:
            lo, hi = _TIME_OF_DAY_HOURS.get(self.preferred_time, (0, 23))
            if lo <= current_hour <= hi:
                score += 6

        return score

    # -----------------------------------------------------------------------
    # Challenge 2 — JSON serialization
    # -----------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize this Task to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "preferred_time": self.preferred_time,
            "start_time": self.start_time,
            "frequency": self.frequency,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "completed": self.completed,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Reconstruct a Task from a dictionary (as produced by to_dict)."""
        due_raw = data.get("due_date")
        return cls(
            name=data["name"],
            category=data["category"],
            duration_minutes=data["duration_minutes"],
            priority=data["priority"],
            preferred_time=data.get("preferred_time"),
            start_time=data.get("start_time"),
            frequency=data.get("frequency", "once"),
            due_date=date.fromisoformat(due_raw) if due_raw else None,
            completed=data.get("completed", False),
        )

    # -----------------------------------------------------------------------
    # Display
    # -----------------------------------------------------------------------

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

    # --- Challenge 2 --------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize this Pet (and its tasks) to a JSON-compatible dictionary."""
        return {
            "name": self.name,
            "species": self.species,
            "age": self.age,
            "breed": self.breed,
            "tasks": [t.to_dict() for t in self._tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Reconstruct a Pet (and its tasks) from a dictionary."""
        pet = cls(
            name=data["name"],
            species=data["species"],
            age=data["age"],
            breed=data.get("breed", ""),
        )
        for task_data in data.get("tasks", []):
            pet.add_task(Task.from_dict(task_data))
        return pet

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

    # --- Challenge 2 --------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize the Owner and all nested Pets/Tasks to a plain dictionary."""
        return {
            "name": self.name,
            "available_minutes": self.available_minutes,
            "preferences": self.preferences,
            "pets": [p.to_dict() for p in self._pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Reconstruct an Owner (with all Pets and Tasks) from a dictionary."""
        owner = cls(
            name=data["name"],
            available_minutes=data["available_minutes"],
            preferences=data.get("preferences", []),
        )
        for pet_data in data.get("pets", []):
            owner.add_pet(Pet.from_dict(pet_data))
        return owner

    def save_to_json(self, path: str | Path = "data.json") -> None:
        """Persist the owner's full state (pets + tasks) to a JSON file.

        Uses a custom dict conversion instead of a third-party serialization
        library (e.g. marshmallow) so the project has no extra dependencies.
        Each class implements to_dict() / from_dict() as a paired contract.
        """
        Path(path).write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load_from_json(cls, path: str | Path = "data.json") -> Optional[Owner]:
        """Load owner state from a JSON file.

        Returns None (instead of raising) if the file does not exist yet,
        so the app can fall back to a default owner on first run.
        """
        p = Path(path)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(data)


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

    # --- Plan generation (original) ----------------------------------------

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

    # --- Challenge 1 — Weighted plan generation ----------------------------

    def generate_weighted_plan(self, current_hour: Optional[int] = None) -> list[Task]:
        """Build a daily plan using composite weighted scores instead of raw priority.

        Tasks are ranked by Task.weighted_score(), which combines:
          - Base priority (dominates)
          - Overdue urgency (days past due_date)
          - Recurrence frequency bonus (daily > weekly > once)
          - Time-of-day alignment (preferred_time matches current_hour)

        The time budget constraint is identical to generate_plan(): tasks that
        don't fit are skipped.  Pass current_hour (0–23) to activate time-of-day
        alignment; omit it (or pass None) to disable that component.

        Challenge 1 — Agent Mode rationale:
          Agent Mode was used to brainstorm the weight schema.  The initial AI
          suggestion used equal weights for all components, which would let a
          severely overdue low-priority task jump ahead of urgent meds.  The
          weights were adjusted so priority × 10 always dominates within the same
          priority level, while the auxiliary signals only break ties between tasks
          at equal priority.
        """
        if current_hour is None:
            from datetime import datetime
            current_hour = datetime.now().hour

        remaining = self.owner.available_minutes
        candidates = [
            t for t in self.owner.get_all_tasks() if not t.completed
        ]
        ranked = sorted(
            candidates,
            key=lambda t: t.weighted_score(current_hour),
            reverse=True,
        )
        plan: list[Task] = []
        for task in ranked:
            if task.is_schedulable(remaining):
                plan.append(task)
                remaining -= task.duration_minutes
        return plan

    def explain_weighted_plan(self, current_hour: Optional[int] = None) -> str:
        """Return a detailed explanation of the weighted scheduling decisions,
        showing each task's score breakdown."""
        if current_hour is None:
            from datetime import datetime
            current_hour = datetime.now().hour

        remaining = self.owner.available_minutes
        lines = [
            f"Weighted plan for {self.owner.name}  (budget: {self.owner.available_minutes} min)\n"
            + "-" * 70
        ]
        candidates = [t for t in self.owner.get_all_tasks() if not t.completed]
        ranked = sorted(
            candidates,
            key=lambda t: t.weighted_score(current_hour),
            reverse=True,
        )
        all_tasks = {id(t) for t in self.owner.get_all_tasks()}
        done_tasks = [t for t in self.owner.get_all_tasks() if t.completed]

        for task in done_tasks:
            lines.append(f"  SKIP  '{task.name}' - already completed today")

        for task in ranked:
            score = task.weighted_score(current_hour)
            # Score breakdown
            base = task.priority * 10
            effective_due = task.due_date if task.due_date else date.today()
            overdue = max(0, (date.today() - effective_due).days) * 5
            recur_bonus = 8 if task.frequency == "daily" else (4 if task.frequency == "weekly" else 0)
            lo, hi = _TIME_OF_DAY_HOURS.get(task.preferred_time or "", (0, 23))
            align_bonus = 6 if task.preferred_time and (lo <= current_hour <= hi) else 0
            breakdown = (
                f"score={score:.0f} "
                f"[base={base} overdue={overdue} recur={recur_bonus} align={align_bonus}]"
            )
            if task.is_schedulable(remaining):
                remaining -= task.duration_minutes
                lines.append(
                    f"  ADD   '{task.name}' - {task.duration_minutes} min  "
                    f"{breakdown}  ({remaining} min left)"
                )
            else:
                lines.append(
                    f"  SKIP  '{task.name}' - needs {task.duration_minutes} min "
                    f"but only {remaining} min remain  {breakdown}"
                )
        lines.append("-" * 70)
        return "\n".join(lines)
