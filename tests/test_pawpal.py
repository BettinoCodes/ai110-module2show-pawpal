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


# ---------------------------------------------------------------------------
# Challenge 1: Weighted prioritization tests
# ---------------------------------------------------------------------------

def test_weighted_score_base_component():
    """weighted_score() base = priority * 10 with no bonuses."""
    task = Task("Walk", "walk", 20, priority=4)
    # No due_date (not overdue), once, no preferred_time
    assert task.weighted_score(current_hour=None) == pytest.approx(40.0)


def test_weighted_score_overdue_bonus():
    """weighted_score() adds 5 per day overdue."""
    from datetime import date, timedelta
    task = Task("Meds", "meds", 5, priority=3,
                due_date=date.today() - timedelta(days=2))
    score = task.weighted_score(current_hour=None)
    # base=30 + overdue=10 (2 days * 5)
    assert score == pytest.approx(40.0)


def test_weighted_score_daily_recurrence_bonus():
    """weighted_score() adds 8 for daily tasks."""
    task = Task("Feed", "feed", 10, priority=2, frequency="daily")
    score = task.weighted_score(current_hour=None)
    # base=20 + recur=8
    assert score == pytest.approx(28.0)


def test_weighted_score_weekly_recurrence_bonus():
    """weighted_score() adds 4 for weekly tasks."""
    task = Task("Bath", "grooming", 30, priority=2, frequency="weekly")
    score = task.weighted_score(current_hour=None)
    # base=20 + recur=4
    assert score == pytest.approx(24.0)


def test_weighted_score_time_alignment_bonus():
    """weighted_score() adds 6 when preferred_time matches current_hour."""
    task = Task("Walk", "walk", 20, priority=3, preferred_time="morning")
    # 08:00 is within "morning" (5–11)
    score_aligned = task.weighted_score(current_hour=8)
    score_not_aligned = task.weighted_score(current_hour=20)
    assert score_aligned == pytest.approx(36.0)   # base=30 + align=6
    assert score_not_aligned == pytest.approx(30.0)


def test_weighted_score_priority_still_dominates():
    """A priority-5 task should always outscore a priority-4 task at equal bonuses."""
    high = Task("Meds",  "meds", 5, priority=5)
    low  = Task("Play",  "enrichment", 10, priority=4, frequency="daily")
    # low has recur +8, so score=48; high has base=50
    assert high.weighted_score(current_hour=None) > low.weighted_score(current_hour=None)


def test_generate_weighted_plan_respects_budget():
    """generate_weighted_plan() must not exceed the time budget."""
    owner = Owner(name="Jo", available_minutes=30)
    pet = Pet(name="Rex", species="dog", age=2)
    pet.add_task(Task("Long Walk", "walk", 25, priority=5))
    pet.add_task(Task("Groom",    "grooming", 20, priority=3))
    owner.add_pet(pet)
    plan = Scheduler(owner=owner).generate_weighted_plan(current_hour=10)
    assert sum(t.duration_minutes for t in plan) <= 30


def test_generate_weighted_plan_skips_completed():
    """generate_weighted_plan() should never include completed tasks."""
    owner = Owner(name="Jo", available_minutes=60)
    pet = Pet(name="Rex", species="dog", age=2)
    done = Task("Done", "feed", 5, priority=5)
    done.mark_complete()
    pet.add_task(done)
    pet.add_task(Task("Pending", "walk", 20, priority=3))
    owner.add_pet(pet)
    plan = Scheduler(owner=owner).generate_weighted_plan(current_hour=10)
    assert done not in plan


def test_generate_weighted_plan_overdue_overtakes_equal_priority():
    """An overdue task should rank above a non-overdue task of equal priority."""
    from datetime import date, timedelta
    owner = Owner(name="Jo", available_minutes=120)
    pet = Pet(name="Rex", species="dog", age=2)
    overdue = Task("Old Meds", "meds", 5, priority=3,
                   due_date=date.today() - timedelta(days=3))
    fresh   = Task("New Task", "walk", 20, priority=3)
    pet.add_task(fresh)
    pet.add_task(overdue)
    owner.add_pet(pet)
    plan = Scheduler(owner=owner).generate_weighted_plan(current_hour=10)
    # overdue task should appear first
    assert plan[0].name == "Old Meds"


def test_explain_weighted_plan_contains_score():
    """explain_weighted_plan() output should contain 'score=' for each task."""
    owner = Owner(name="Jo", available_minutes=60)
    pet = Pet(name="Rex", species="dog", age=2)
    pet.add_task(Task("Walk", "walk", 20, priority=4))
    owner.add_pet(pet)
    explanation = Scheduler(owner=owner).explain_weighted_plan(current_hour=9)
    assert "score=" in explanation


# ---------------------------------------------------------------------------
# Challenge 2: JSON serialization tests
# ---------------------------------------------------------------------------

def test_task_to_dict_and_from_dict_roundtrip():
    """Task.to_dict() -> Task.from_dict() should reproduce an identical task."""
    from datetime import date
    original = Task(
        name="Walk", category="walk", duration_minutes=20, priority=4,
        preferred_time="morning", start_time="07:00",
        frequency="daily", due_date=date(2026, 4, 1), completed=True,
    )
    restored = Task.from_dict(original.to_dict())
    assert restored.name == original.name
    assert restored.category == original.category
    assert restored.duration_minutes == original.duration_minutes
    assert restored.priority == original.priority
    assert restored.preferred_time == original.preferred_time
    assert restored.start_time == original.start_time
    assert restored.frequency == original.frequency
    assert restored.due_date == original.due_date
    assert restored.completed == original.completed


def test_task_roundtrip_with_none_fields():
    """Task.from_dict() should handle missing optional fields gracefully."""
    minimal = Task(name="Feed", category="feed", duration_minutes=5, priority=3)
    restored = Task.from_dict(minimal.to_dict())
    assert restored.preferred_time is None
    assert restored.start_time is None
    assert restored.due_date is None
    assert restored.completed is False


def test_pet_to_dict_and_from_dict_roundtrip():
    """Pet.to_dict() -> Pet.from_dict() should include all nested tasks."""
    pet = Pet(name="Luna", species="dog", age=3, breed="Lab")
    pet.add_task(Task("Walk", "walk", 30, 5))
    pet.add_task(Task("Feed", "feed", 10, 5))
    restored = Pet.from_dict(pet.to_dict())
    assert restored.name == "Luna"
    assert restored.breed == "Lab"
    assert len(restored.get_tasks()) == 2
    assert restored.get_tasks()[0].name == "Walk"


def test_owner_to_dict_and_from_dict_roundtrip():
    """Owner.to_dict() -> Owner.from_dict() should reconstruct full hierarchy."""
    owner = Owner(name="Jordan", available_minutes=90, preferences=["no early walks"])
    dog = Pet(name="Rex", species="dog", age=3)
    dog.add_task(Task("Walk", "walk", 20, 5, frequency="daily"))
    owner.add_pet(dog)

    restored = Owner.from_dict(owner.to_dict())
    assert restored.name == "Jordan"
    assert restored.available_minutes == 90
    assert restored.preferences == ["no early walks"]
    assert len(restored.get_pets()) == 1
    assert restored.get_pets()[0].name == "Rex"
    assert len(restored.get_pets()[0].get_tasks()) == 1
    assert restored.get_pets()[0].get_tasks()[0].frequency == "daily"


def test_save_and_load_json_roundtrip(tmp_path):
    """save_to_json() -> load_from_json() should reconstruct an identical Owner."""
    path = tmp_path / "test_data.json"
    owner = Owner(name="Sam", available_minutes=60)
    cat = Pet(name="Mochi", species="cat", age=5)
    cat.add_task(Task("Feed", "feed", 5, priority=5, frequency="daily"))
    owner.add_pet(cat)

    owner.save_to_json(path)
    restored = Owner.load_from_json(path)

    assert restored is not None
    assert restored.name == "Sam"
    assert restored.available_minutes == 60
    assert len(restored.get_pets()) == 1
    assert restored.get_pets()[0].name == "Mochi"
    assert restored.get_pets()[0].get_tasks()[0].name == "Feed"


def test_load_from_json_missing_file_returns_none(tmp_path):
    """load_from_json() should return None when the file does not exist."""
    result = Owner.load_from_json(tmp_path / "nonexistent.json")
    assert result is None


# ---------------------------------------------------------------------------
# Phase 4: Edge cases
# ---------------------------------------------------------------------------

# --- Empty states -----------------------------------------------------------

def test_owner_with_no_pets_generates_empty_plan():
    """An owner with no pets should produce an empty schedule."""
    owner = Owner(name="Empty", available_minutes=60)
    assert Scheduler(owner=owner).generate_plan() == []


def test_owner_with_no_pets_has_no_tasks():
    """get_all_tasks() with no pets should return an empty list."""
    owner = Owner(name="Empty", available_minutes=60)
    assert owner.get_all_tasks() == []


def test_pet_with_no_tasks_returns_empty_list():
    """A freshly created pet should have zero tasks."""
    pet = Pet(name="Solo", species="cat", age=1)
    assert pet.get_tasks() == []


def test_scheduler_with_pet_but_no_tasks_generates_empty_plan():
    """A pet registered but with no tasks should yield an empty plan."""
    owner = Owner(name="Jo", available_minutes=60)
    owner.add_pet(Pet(name="Blank", species="rabbit", age=2))
    assert Scheduler(owner=owner).generate_plan() == []


# --- Zero / exhausted budget ------------------------------------------------

def test_is_schedulable_zero_remaining_returns_false(sample_task):
    """is_schedulable(0) should be False for any task with duration > 0."""
    assert sample_task.is_schedulable(0) is False


def test_generate_plan_zero_budget_returns_empty():
    """A budget of 0 minutes means no tasks can be scheduled."""
    owner = Owner(name="Busy", available_minutes=0)
    pet = Pet(name="Rex", species="dog", age=2)
    pet.add_task(Task("Walk", "walk", 1, 5))   # even 1-min task won't fit
    owner.add_pet(pet)
    assert Scheduler(owner=owner).generate_plan() == []


def test_generate_plan_all_completed_returns_empty():
    """If every task is already completed, the plan should be empty."""
    owner = Owner(name="Done", available_minutes=120)
    pet = Pet(name="Rex", species="dog", age=2)
    for name in ("Walk", "Feed", "Meds"):
        t = Task(name, "walk", 10, 5)
        t.mark_complete()
        pet.add_task(t)
    owner.add_pet(pet)
    assert Scheduler(owner=owner).generate_plan() == []


# --- Combined filter --------------------------------------------------------

def test_filter_tasks_combined_pet_and_completed():
    """filter_tasks(pet_name, completed=False) should narrow by both axes."""
    owner = Owner(name="Jo", available_minutes=120)
    dog = Pet(name="Rex", species="dog", age=3)
    cat = Pet(name="Luna", species="cat", age=2)
    done = Task("Rex Done", "feed", 10, 5)
    done.mark_complete()
    dog.add_task(done)
    dog.add_task(Task("Rex Pending", "walk", 20, 4))
    cat.add_task(Task("Luna Pending", "walk", 20, 4))
    owner.add_pet(dog)
    owner.add_pet(cat)
    results = Scheduler(owner=owner).filter_tasks(pet_name="Rex", completed=False)
    assert len(results) == 1
    assert results[0].name == "Rex Pending"


# --- Recurring edge cases ---------------------------------------------------

def test_complete_task_unknown_name_returns_none():
    """complete_task() with a non-existent name should return None gracefully."""
    pet = Pet(name="Rex", species="dog", age=3)
    pet.add_task(Task("Walk", "walk", 20, 5, frequency="daily"))
    result = pet.complete_task("NonExistent")
    assert result is None


def test_next_occurrence_no_due_date_uses_today():
    """next_occurrence() with no due_date set should base the offset on today."""
    from datetime import date, timedelta
    task = Task("Walk", "walk", 20, 5, frequency="daily")  # due_date=None
    next_task = task.next_occurrence()
    assert next_task.due_date == date.today() + timedelta(days=1)


def test_next_occurrence_preserves_task_attributes():
    """next_occurrence() should copy all fields except due_date and completed."""
    from datetime import date
    task = Task("Feed", "feed", 10, 4, preferred_time="morning",
                start_time="07:30", frequency="daily", due_date=date.today())
    nxt = task.next_occurrence()
    assert nxt.name == task.name
    assert nxt.category == task.category
    assert nxt.duration_minutes == task.duration_minutes
    assert nxt.priority == task.priority
    assert nxt.preferred_time == task.preferred_time
    assert nxt.start_time == task.start_time
    assert nxt.frequency == task.frequency
    assert nxt.completed is False


# --- Multiple conflicts ------------------------------------------------------

def test_detect_conflicts_multiple_slots():
    """detect_conflicts() should report a warning for each conflicting time slot."""
    owner = Owner(name="Jo", available_minutes=120)
    dog = Pet(name="Rex", species="dog", age=3)
    cat = Pet(name="Luna", species="cat", age=2)
    # Two conflicts: 07:00 and 18:00
    dog.add_task(Task("Morning Walk", "walk", 20, 5, start_time="07:00"))
    cat.add_task(Task("Morning Feed", "feed", 10, 5, start_time="07:00"))
    dog.add_task(Task("Evening Walk", "walk", 20, 3, start_time="18:00"))
    cat.add_task(Task("Evening Play", "enrichment", 15, 2, start_time="18:00"))
    owner.add_pet(dog)
    owner.add_pet(cat)
    warnings = Scheduler(owner=owner).detect_conflicts()
    assert len(warnings) == 2
    assert any("07:00" in w for w in warnings)
    assert any("18:00" in w for w in warnings)


# --- explain_plan sanity check ----------------------------------------------

def test_explain_plan_contains_owner_name():
    """explain_plan() output should reference the owner's name."""
    owner = Owner(name="Jordan", available_minutes=30)
    pet = Pet(name="Rex", species="dog", age=2)
    pet.add_task(Task("Walk", "walk", 20, 5))
    owner.add_pet(pet)
    explanation = Scheduler(owner=owner).explain_plan()
    assert "Jordan" in explanation


def test_explain_plan_mentions_skipped_task():
    """explain_plan() should mention tasks that are skipped due to budget."""
    owner = Owner(name="Jo", available_minutes=10)
    pet = Pet(name="Rex", species="dog", age=2)
    pet.add_task(Task("Short",  "feed", 5,  priority=5))
    pet.add_task(Task("TooLong", "walk", 20, priority=3))
    owner.add_pet(pet)
    explanation = Scheduler(owner=owner).explain_plan()
    assert "TooLong" in explanation
    assert "SKIP" in explanation
