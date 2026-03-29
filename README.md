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
| **Automated tests** | 40 pytest tests covering happy paths and edge cases (empty states, zero budget, combined filters, multiple conflict slots) |

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
