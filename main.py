"""
main.py -- PawPal+ demo script
Demonstrates: priority scheduling, sort_by_time, filter_tasks,
              recurring task auto-spawn, and conflict detection.
Run with: python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main() -> None:
    # -----------------------------------------------------------------------
    # Setup
    # -----------------------------------------------------------------------
    owner = Owner(name="Jordan", available_minutes=90)

    luna  = Pet(name="Luna",  species="dog", age=3, breed="Labrador")
    mochi = Pet(name="Mochi", species="cat", age=5, breed="Siamese")
    owner.add_pet(luna)
    owner.add_pet(mochi)

    # Tasks added OUT OF TIME ORDER intentionally to test sort_by_time.
    # start_time uses "HH:MM" format.
    luna.add_task(Task("Evening Walk",    "walk",       30, 3,
                       preferred_time="evening",   start_time="18:00", frequency="daily"))
    luna.add_task(Task("Morning Walk",    "walk",       30, 5,
                       preferred_time="morning",   start_time="07:00", frequency="daily"))
    luna.add_task(Task("Flea Medication", "meds",        5, 4,
                       start_time="08:00"))
    luna.add_task(Task("Teeth Brushing",  "grooming",   10, 2,
                       preferred_time="evening",   start_time="19:00"))
    luna.add_task(Task("Breakfast",       "feed",       10, 5,
                       preferred_time="morning",   start_time="07:30", frequency="daily"))

    mochi.add_task(Task("Mochi Breakfast","feed",        5, 5,
                        preferred_time="morning",  start_time="07:30", frequency="daily"))
    mochi.add_task(Task("Hairball Meds",  "meds",        5, 4,
                        start_time="09:00"))
    mochi.add_task(Task("Puzzle Feeder",  "enrichment", 15, 2,
                        preferred_time="afternoon",start_time="14:00"))

    scheduler = Scheduler(owner=owner)

    # -----------------------------------------------------------------------
    # 1. Priority-based schedule (existing behaviour)
    # -----------------------------------------------------------------------
    section("1. Today's Schedule  (sorted by priority)")
    plan = scheduler.generate_plan()
    if not plan:
        print("  No tasks fit within today's time budget.")
    else:
        total = sum(t.duration_minutes for t in plan)
        for task in plan:
            print(task)
        print("-" * 60)
        print(f"  {len(plan)} tasks  |  {total} min used  |  "
              f"{owner.available_minutes - total} min remaining")

    # -----------------------------------------------------------------------
    # 2. Sort by start time
    # -----------------------------------------------------------------------
    section("2. All Tasks  (sorted by start_time HH:MM)")
    for task in scheduler.sort_by_time():
        print(task)

    # -----------------------------------------------------------------------
    # 3. Filter -- pending tasks for Luna only
    # -----------------------------------------------------------------------
    section("3. Filter: Luna's pending tasks only")
    for task in scheduler.filter_tasks(pet_name="Luna", completed=False):
        print(task)

    # -----------------------------------------------------------------------
    # 4. Conflict detection
    #    Luna's Breakfast and Mochi's Breakfast both start at 07:30 -> conflict
    # -----------------------------------------------------------------------
    section("4. Conflict Detection")
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        for warning in conflicts:
            print(f"  WARNING: {warning}")
    else:
        print("  No conflicts detected.")

    # -----------------------------------------------------------------------
    # 5. Recurring tasks -- mark Luna's Morning Walk complete
    #    A new occurrence should appear automatically for the next day
    # -----------------------------------------------------------------------
    section("5. Recurring Task  (mark Morning Walk complete)")
    next_task = luna.complete_task("Morning Walk")
    if next_task:
        print(f"  'Morning Walk' marked complete.")
        print(f"  Next occurrence created: due {next_task.due_date}")
    else:
        print("  Task not found or non-recurring.")

    print()
    print("  Luna's tasks after completion:")
    for task in luna.get_tasks():
        due = f"  due {task.due_date}" if task.due_date else ""
        status = "[x]" if task.completed else "[ ]"
        print(f"    {status} {task.name}{due}")

    # -----------------------------------------------------------------------
    # 6. Scheduler explanation
    # -----------------------------------------------------------------------
    section("6. Scheduling Explanation")
    print(scheduler.explain_plan())


if __name__ == "__main__":
    main()
