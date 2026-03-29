"""
tests/test_pawpal.py — unit tests for PawPal+ core logic
Run with: python -m pytest
"""

import pytest
from pawpal_system import Owner, Pet, Task, Scheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_task():
    return Task(name="Morning Walk", category="walk", duration_minutes=30, priority=5)


@pytest.fixture
def sample_pet():
    return Pet(name="Luna", species="dog", age=3)


@pytest.fixture
def sample_owner():
    return Owner(name="Jordan", available_minutes=60)


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

def test_mark_complete_changes_status(sample_task):
    """mark_complete() should flip completed from False to True."""
    assert sample_task.completed is False
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_mark_complete_is_idempotent(sample_task):
    """Calling mark_complete() twice should keep completed as True."""
    sample_task.mark_complete()
    sample_task.mark_complete()
    assert sample_task.completed is True


def test_is_schedulable_fits(sample_task):
    """Task with duration 30 should be schedulable when 30 min remain."""
    assert sample_task.is_schedulable(30) is True


def test_is_schedulable_too_long(sample_task):
    """Task with duration 30 should not be schedulable when only 29 min remain."""
    assert sample_task.is_schedulable(29) is False


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

def test_add_task_increases_count(sample_pet, sample_task):
    """Adding a task to a pet should increase its task count by 1."""
    before = len(sample_pet.get_tasks())
    sample_pet.add_task(sample_task)
    assert len(sample_pet.get_tasks()) == before + 1


def test_add_multiple_tasks(sample_pet):
    """Adding three tasks should result in exactly three tasks on the pet."""
    for i in range(3):
        sample_pet.add_task(Task(f"Task {i}", "walk", duration_minutes=10, priority=i + 1))
    assert len(sample_pet.get_tasks()) == 3


def test_remove_task_decreases_count(sample_pet, sample_task):
    """Removing a task by name should reduce the task count."""
    sample_pet.add_task(sample_task)
    sample_pet.remove_task("Morning Walk")
    assert len(sample_pet.get_tasks()) == 0


def test_remove_nonexistent_task_is_safe(sample_pet):
    """Removing a task that doesn't exist should not raise an error."""
    sample_pet.remove_task("Ghost Task")   # should not raise


def test_get_tasks_returns_copy(sample_pet, sample_task):
    """get_tasks() should return a separate list, not the internal one."""
    sample_pet.add_task(sample_task)
    tasks = sample_pet.get_tasks()
    tasks.clear()
    assert len(sample_pet.get_tasks()) == 1   # internal list unchanged


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

def test_add_pet_increases_count(sample_owner, sample_pet):
    """Adding a pet should increase the owner's pet count by 1."""
    before = len(sample_owner.get_pets())
    sample_owner.add_pet(sample_pet)
    assert len(sample_owner.get_pets()) == before + 1


def test_set_available_time(sample_owner):
    """set_available_time() should update available_minutes."""
    sample_owner.set_available_time(120)
    assert sample_owner.available_minutes == 120


def test_get_all_tasks_aggregates_across_pets(sample_owner):
    """get_all_tasks() should return tasks from all pets combined."""
    dog = Pet(name="Rex", species="dog", age=2)
    cat = Pet(name="Mochi", species="cat", age=4)
    dog.add_task(Task("Walk", "walk", 20, 5))
    cat.add_task(Task("Feed", "feed", 10, 5))
    cat.add_task(Task("Play", "enrichment", 15, 3))
    sample_owner.add_pet(dog)
    sample_owner.add_pet(cat)
    assert len(sample_owner.get_all_tasks()) == 3


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

def test_generate_plan_respects_time_budget():
    """Scheduler should not schedule tasks that exceed the time budget."""
    owner = Owner(name="Alex", available_minutes=30)
    pet = Pet(name="Buddy", species="dog", age=2)
    pet.add_task(Task("Long Walk",    "walk", duration_minutes=25, priority=5))
    pet.add_task(Task("Grooming",     "grooming", duration_minutes=20, priority=3))
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)
    plan = scheduler.generate_plan()
    total_time = sum(t.duration_minutes for t in plan)
    assert total_time <= 30


def test_generate_plan_skips_completed_tasks():
    """Scheduler should not include already-completed tasks in the plan."""
    owner = Owner(name="Sam", available_minutes=60)
    pet = Pet(name="Pip", species="cat", age=1)
    done_task = Task("Feed", "feed", duration_minutes=5, priority=5)
    done_task.mark_complete()
    pet.add_task(done_task)
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)
    plan = scheduler.generate_plan()
    assert done_task not in plan


def test_filter_by_priority_orders_correctly():
    """filter_by_priority() should return tasks highest-priority first."""
    owner = Owner(name="Pat", available_minutes=90)
    pet = Pet(name="Dot", species="rabbit", age=2)
    pet.add_task(Task("Low",  "enrichment", 10, priority=1))
    pet.add_task(Task("High", "meds",       5,  priority=5))
    pet.add_task(Task("Mid",  "feed",       10, priority=3))
    owner.add_pet(pet)
    scheduler = Scheduler(owner=owner)
    ordered = scheduler.filter_by_priority()
    priorities = [t.priority for t in ordered]
    assert priorities == sorted(priorities, reverse=True)


# ---------------------------------------------------------------------------
# Phase 3: Sorting tests
# ---------------------------------------------------------------------------

def test_sort_by_time_ascending():
    """sort_by_time() should return tasks in HH:MM ascending order."""
    owner = Owner(name="Jo", available_minutes=120)
    pet = Pet(name="Boo", species="dog", age=2)
    pet.add_task(Task("Evening", "walk",  20, 3, start_time="18:00"))
    pet.add_task(Task("Morning", "walk",  20, 5, start_time="07:00"))
    pet.add_task(Task("Midday",  "feed",  10, 4, start_time="12:00"))
    owner.add_pet(pet)
    times = [t.start_time for t in Scheduler(owner=owner).sort_by_time()]
    assert times == ["07:00", "12:00", "18:00"]


def test_sort_by_time_no_start_time_goes_last():
    """Tasks without start_time should appear after all timed tasks."""
    owner = Owner(name="Jo", available_minutes=120)
    pet = Pet(name="Boo", species="dog", age=2)
    pet.add_task(Task("No Time",  "grooming", 10, 2))
    pet.add_task(Task("Morning",  "walk",     20, 5, start_time="07:00"))
    owner.add_pet(pet)
    sorted_tasks = Scheduler(owner=owner).sort_by_time()
    assert sorted_tasks[0].name == "Morning"
    assert sorted_tasks[-1].name == "No Time"


# ---------------------------------------------------------------------------
# Phase 3: Filtering tests
# ---------------------------------------------------------------------------

def test_filter_tasks_by_pet_name():
    """filter_tasks(pet_name=...) should return only that pet's tasks."""
    owner = Owner(name="Jo", available_minutes=120)
    dog = Pet(name="Rex", species="dog", age=3)
    cat = Pet(name="Luna", species="cat", age=2)
    dog.add_task(Task("Walk", "walk", 20, 5))
    cat.add_task(Task("Feed", "feed", 10, 5))
    owner.add_pet(dog)
    owner.add_pet(cat)
    results = Scheduler(owner=owner).filter_tasks(pet_name="Rex")
    assert len(results) == 1
    assert results[0].name == "Walk"


def test_filter_tasks_by_completed_false():
    """filter_tasks(completed=False) should exclude finished tasks."""
    owner = Owner(name="Jo", available_minutes=120)
    pet = Pet(name="Rex", species="dog", age=3)
    done = Task("Done Task", "feed", 10, 5)
    done.mark_complete()
    pending = Task("Pending", "walk", 20, 4)
    pet.add_task(done)
    pet.add_task(pending)
    owner.add_pet(pet)
    results = Scheduler(owner=owner).filter_tasks(completed=False)
    assert all(not t.completed for t in results)
    assert any(t.name == "Pending" for t in results)


def test_filter_tasks_by_completed_true():
    """filter_tasks(completed=True) should return only completed tasks."""
    owner = Owner(name="Jo", available_minutes=120)
    pet = Pet(name="Rex", species="dog", age=3)
    done = Task("Done Task", "feed", 10, 5)
    done.mark_complete()
    pet.add_task(done)
    pet.add_task(Task("Pending", "walk", 20, 4))
    owner.add_pet(pet)
    results = Scheduler(owner=owner).filter_tasks(completed=True)
    assert len(results) == 1
    assert results[0].name == "Done Task"


# ---------------------------------------------------------------------------
# Phase 3: Recurring task tests
# ---------------------------------------------------------------------------

def test_complete_task_daily_spawns_next_occurrence():
    """Completing a daily task should add a new occurrence to the pet."""
    from datetime import date, timedelta
    pet = Pet(name="Rex", species="dog", age=3)
    pet.add_task(Task("Walk", "walk", 20, 5, frequency="daily",
                      due_date=date.today()))
    before = len(pet.get_tasks())
    next_task = pet.complete_task("Walk")
    assert len(pet.get_tasks()) == before + 1
    assert next_task is not None
    assert next_task.due_date == date.today() + timedelta(days=1)
    assert next_task.completed is False


def test_complete_task_weekly_spawns_seven_days_later():
    """Completing a weekly task should schedule the next occurrence 7 days out."""
    from datetime import date, timedelta
    pet = Pet(name="Rex", species="dog", age=3)
    pet.add_task(Task("Bath", "grooming", 30, 3, frequency="weekly",
                      due_date=date.today()))
    next_task = pet.complete_task("Bath")
    assert next_task is not None
    assert next_task.due_date == date.today() + timedelta(weeks=1)


def test_complete_task_once_does_not_spawn():
    """Completing a one-time task should not add a new occurrence."""
    pet = Pet(name="Rex", species="dog", age=3)
    pet.add_task(Task("Vet Visit", "meds", 60, 5, frequency="once"))
    before = len(pet.get_tasks())
    result = pet.complete_task("Vet Visit")
    assert result is None
    assert len(pet.get_tasks()) == before


# ---------------------------------------------------------------------------
# Phase 3: Conflict detection tests
# ---------------------------------------------------------------------------

def test_detect_conflicts_finds_same_start_time():
    """detect_conflicts() should flag tasks sharing the same start_time."""
    owner = Owner(name="Jo", available_minutes=120)
    dog = Pet(name="Rex", species="dog", age=3)
    cat = Pet(name="Luna", species="cat", age=2)
    dog.add_task(Task("Walk",  "walk", 20, 5, start_time="08:00"))
    cat.add_task(Task("Feed",  "feed", 10, 5, start_time="08:00"))
    owner.add_pet(dog)
    owner.add_pet(cat)
    warnings = Scheduler(owner=owner).detect_conflicts()
    assert len(warnings) == 1
    assert "08:00" in warnings[0]


def test_detect_conflicts_no_overlap_returns_empty():
    """detect_conflicts() should return an empty list when no times clash."""
    owner = Owner(name="Jo", available_minutes=120)
    pet = Pet(name="Rex", species="dog", age=3)
    pet.add_task(Task("Morning", "walk", 20, 5, start_time="07:00"))
    pet.add_task(Task("Evening", "walk", 20, 3, start_time="18:00"))
    owner.add_pet(pet)
    assert Scheduler(owner=owner).detect_conflicts() == []


def test_detect_conflicts_no_start_times_returns_empty():
    """Tasks with no start_time should never produce a conflict warning."""
    owner = Owner(name="Jo", available_minutes=120)
    pet = Pet(name="Rex", species="dog", age=3)
    pet.add_task(Task("Walk", "walk",  20, 5))
    pet.add_task(Task("Feed", "feed",  10, 5))
    owner.add_pet(pet)
    assert Scheduler(owner=owner).detect_conflicts() == []
