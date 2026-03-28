"""
main.py — PawPal+ demo script
Run with: python main.py
"""

from pawpal_system import Owner, Pet, Task, Scheduler


def main() -> None:
    # --- Owner -----------------------------------------------------------
    owner = Owner(name="Jordan", available_minutes=90)

    # --- Pets ------------------------------------------------------------
    luna = Pet(name="Luna", species="dog", age=3, breed="Labrador")
    mochi = Pet(name="Mochi", species="cat", age=5, breed="Siamese")

    owner.add_pet(luna)
    owner.add_pet(mochi)

    # --- Tasks for Luna --------------------------------------------------
    luna.add_task(Task("Morning Walk",   "walk",       duration_minutes=30, priority=5, preferred_time="morning"))
    luna.add_task(Task("Breakfast",      "feed",       duration_minutes=10, priority=5, preferred_time="morning"))
    luna.add_task(Task("Flea Medication","meds",       duration_minutes=5,  priority=4))
    luna.add_task(Task("Evening Walk",   "walk",       duration_minutes=30, priority=3, preferred_time="evening"))
    luna.add_task(Task("Teeth Brushing", "grooming",   duration_minutes=10, priority=2))

    # --- Tasks for Mochi -------------------------------------------------
    mochi.add_task(Task("Mochi Breakfast", "feed",       duration_minutes=5,  priority=5, preferred_time="morning"))
    mochi.add_task(Task("Hairball Meds",   "meds",       duration_minutes=5,  priority=4))
    mochi.add_task(Task("Puzzle Feeder",   "enrichment", duration_minutes=15, priority=2, preferred_time="afternoon"))

    # --- Mark one task already done (demonstrates skip logic) ------------
    luna.get_tasks()[1].mark_complete()   # Breakfast already done

    # --- Scheduler -------------------------------------------------------
    scheduler = Scheduler(owner=owner)

    print("=" * 60)
    print("           PawPal+  Today's Schedule")
    print("=" * 60)

    plan = scheduler.generate_plan()

    if not plan:
        print("  No tasks fit within today's time budget.")
    else:
        total = sum(t.duration_minutes for t in plan)
        for task in plan:
            print(task)
        print("-" * 60)
        print(f"  {len(plan)} tasks scheduled  |  {total} min used  |  "
              f"{owner.available_minutes - total} min remaining")

    print()
    print(scheduler.explain_plan())


if __name__ == "__main__":
    main()
