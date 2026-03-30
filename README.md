# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Features

| Feature | Description |
|---|---|
| **Owner & pet profiles** | Enter your name, daily time budget, and details for one or more pets (species, age, breed) |
| **Task management** | Add care tasks (walk, feed, meds, grooming, enrichment…) with duration, priority (1–5), preferred time, and an optional precise start time |
| **Priority scheduling** | `Scheduler.generate_plan()` selects incomplete tasks in priority order, stopping when the time budget is exhausted; every inclusion and skip is explained in plain language |
| **Chronological view** | `Scheduler.sort_by_time()` sorts all tasks by `start_time` (HH:MM ascending); tasks without a start time appear last |
| **Flexible filtering** | `Scheduler.filter_tasks()` narrows the task list by pet name, completion status, or both simultaneously |
| **Recurring tasks** | Tasks carry a `frequency` field (`once` / `daily` / `weekly`); marking one complete automatically spawns the next occurrence with a `due_date` calculated via Python's `timedelta` |
| **Conflict detection** | `Scheduler.detect_conflicts()` flags any two tasks that share the same start time and surfaces a warning banner in the UI — no exceptions, no crashes |
| **Interactive UI** | Streamlit interface with conflict banners (`st.warning`/`st.error`), sortable task table, Done buttons with recurrence toast notifications, and a filter panel |
| **Weighted prioritization** | `Scheduler.generate_weighted_plan()` ranks tasks by a composite score: base priority + overdue urgency + recurrence bonus + time-of-day alignment; UI toggle compares Standard vs. Weighted plans side-by-side |
| **Data persistence** | `Owner.save_to_json()` / `load_from_json()` auto-saves to `data.json` after every change using a custom `to_dict`/`from_dict` contract on all classes; no extra dependencies |
| **Automated tests** | 56 pytest tests covering happy paths and edge cases (empty states, zero budget, combined filters, weighted score components, full JSON round-trip) |

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Run the app

```bash
streamlit run app.py
```

### Run the tests

```bash
python -m pytest
```

## Challenge 1 — Weighted Prioritization

`Scheduler.generate_weighted_plan()` is a third algorithmic capability that goes beyond the basic priority sort. It computes a **composite urgency score** for each task using four additive components:

| Component | Weight | Rationale |
|---|---|---|
| Base priority | `priority × 10` (0–50) | Dominates; ensures a P5 task always beats a P4 task at equal bonuses |
| Overdue urgency | `days_overdue × 5` | Catches up recurring meds that have been skipped; prevents them from being perpetually bumped |
| Recurrence bonus | `+8` daily / `+4` weekly | Recurring commitments are weighted slightly higher than one-off errands at the same priority |
| Time-of-day alignment | `+6` if `preferred_time` matches current hour | Soft preference: rewards scheduling a "morning" task in the morning without preventing it from being chosen later |

The UI exposes a **Standard vs. Weighted** radio toggle on the Generate Plan button. In Weighted mode the plan table shows each task's composite score; the explanation log breaks down every component.

**How Agent Mode was used:**
Agent Mode was prompted with the full `pawpal_system.py` and asked: *"Suggest a composite scoring algorithm for pet care tasks that combines priority, overdue days, recurrence frequency, and time-of-day preference — and explain how to weight the components so priority still dominates."*  The AI proposed equal weights for all components, which would have allowed a severely overdue low-priority enrichment task to jump ahead of urgent medication. The weights were redesigned so `priority × 10` always produces a higher gap between priority levels (10 points) than any single bonus can bridge — only a task that is simultaneously overdue, recurring, and time-aligned can overtake a task one priority level above it.

## Challenge 2 — Data Persistence

PawPal+ now remembers everything between runs using a `data.json` file.

**How it works:**

Each class implements a `to_dict()` / `from_dict()` pair rather than relying on a third-party serialization library like `marshmallow`. This approach keeps the project dependency-free and makes the serialization logic explicit and testable. `date` objects are converted to ISO-8601 strings (`YYYY-MM-DD`) for JSON compatibility and parsed back with `date.fromisoformat()`.

```
Owner.save_to_json("data.json")   # writes full hierarchy
Owner.load_from_json("data.json") # returns None if file missing (safe first-run)
```

`app.py` calls `Owner.load_from_json()` at startup (inside the `if "owner" not in st.session_state` guard so it only runs once per browser session), and calls `save(owner)` after every mutation — adding a pet, adding a task, marking a task done, and updating owner info. A **Reset all data** button in the sidebar deletes `data.json` and clears the session.

## Smarter Scheduling

Phase 3 added four algorithmic features to `pawpal_system.py`:

| Feature | Method | How it works |
|---|---|---|
| **Sort by time** | `Scheduler.sort_by_time()` | Sorts tasks by `start_time` ("HH:MM") using a lambda key; tasks without a time sort to the end via a `"99:99"` sentinel so the comparison stays a plain string sort |
| **Filter tasks** | `Scheduler.filter_tasks(pet_name, completed)` | Accepts optional keyword arguments to narrow results by pet name (case-insensitive) and/or completion status; both filters can be combined |
| **Recurring tasks** | `Task.next_occurrence()` / `Pet.complete_task()` | Tasks carry a `frequency` field (`"once"`, `"daily"`, `"weekly"`); calling `pet.complete_task(name)` marks the task done and, if recurring, appends a fresh copy with the next `due_date` computed via `timedelta` |
| **Conflict detection** | `Scheduler.detect_conflicts()` | Buckets tasks by `start_time`; any bucket with more than one entry produces a human-readable warning string — no exceptions raised |

## Testing PawPal+

### Run the tests

```bash
python -m pytest
```

All tests live in `tests/test_pawpal.py`. The suite currently contains **40 tests** covering:

| Category | What is verified |
|---|---|
| **Task basics** | `mark_complete()` flips status; idempotent; `is_schedulable()` boundary conditions including zero remaining minutes |
| **Pet management** | `add_task` / `remove_task` / `get_tasks` copy-safety; pet with no tasks returns empty list |
| **Owner aggregation** | `get_all_tasks()` collects across multiple pets; owner with no pets returns empty |
| **Scheduler — plan generation** | Respects time budget; skips completed tasks; zero-budget returns empty; all-completed returns empty |
| **Scheduler — sorting** | `sort_by_time()` returns HH:MM ascending; tasks without `start_time` sort last |
| **Scheduler — filtering** | `filter_tasks()` by pet name, by completion status, and both combined |
| **Scheduler — conflict detection** | Exact `start_time` matches flagged; distinct non-overlapping times clean; multiple conflict slots reported separately; no `start_time` → never a conflict |
| **Recurring tasks** | Daily task spawns next occurrence +1 day; weekly +7 days; `once` tasks do not spawn; unknown task name returns `None` gracefully; `next_occurrence()` preserves all fields and uses today when `due_date` is `None` |
| **explain_plan output** | Contains owner name; mentions skipped tasks with "SKIP" label |

### Confidence level: ★★★★☆ (4/5)

The core scheduling contract (priority ordering, time budget, completed-task skipping) and all algorithmic additions (sorting, filtering, recurrence, conflict detection) are thoroughly covered. The main gap is integration-level testing of the Streamlit UI — clicking buttons in `app.py` is not tested automatically — and true duration-overlap detection is not implemented (only exact `start_time` equality is checked). Those are the areas to tackle next.

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.

### Demo
<img width="1078" height="631" alt="image" src="https://github.com/user-attachments/assets/504cc564-0226-4c1a-bcd8-43d70fb042f7" />
<img width="1050" height="733" alt="image" src="https://github.com/user-attachments/assets/e532e4fb-33c1-4b6b-a634-c1032750fd7b" />
<img width="1037" height="771" alt="image" src="https://github.com/user-attachments/assets/7b58eef2-7349-489e-afa0-f9e4e704b508" />



