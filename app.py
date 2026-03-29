import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("Your smart pet care planner — prioritized, conflict-aware, and recurring-task ready.")

# ---------------------------------------------------------------------------
# Session state vault — Owner object persists across Streamlit reruns
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=90)

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Section 1 — Owner info
# ---------------------------------------------------------------------------
st.subheader("Owner Info")
with st.form("owner_form"):
    col1, col2 = st.columns(2)
    with col1:
        owner_name = st.text_input("Your name", value=owner.name)
    with col2:
        available = st.number_input(
            "Daily time budget (minutes)",
            min_value=0, max_value=480,
            value=owner.available_minutes,
        )
    if st.form_submit_button("Save"):
        owner.name = owner_name.strip() or owner.name
        owner.set_available_time(int(available))
        st.success(f"Saved — {owner.name}, {owner.available_minutes} min/day")

# ---------------------------------------------------------------------------
# Section 2 — Pets
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Your Pets")

pets = owner.get_pets()
if pets:
    for pet in pets:
        breed_note = f" ({pet.breed})" if pet.breed else ""
        st.markdown(f"- **{pet.name}**{breed_note} — {pet.age}-yr-old {pet.species}")
else:
    st.info("No pets yet. Add one below.")

with st.expander("Add a pet"):
    with st.form("pet_form"):
        col1, col2 = st.columns(2)
        with col1:
            pet_name = st.text_input("Pet name")
            species = st.selectbox("Species", ["dog", "cat", "rabbit", "bird", "other"])
        with col2:
            age = st.number_input("Age (years)", min_value=0, max_value=30, value=1)
            breed = st.text_input("Breed (optional)")

        if st.form_submit_button("Add pet"):
            if pet_name.strip():
                owner.add_pet(Pet(
                    name=pet_name.strip(),
                    species=species,
                    age=int(age),
                    breed=breed.strip(),
                ))
                st.success(f"Added {pet_name.strip()}!")
                st.rerun()
            else:
                st.error("Pet name cannot be empty.")

# ---------------------------------------------------------------------------
# Section 3 — Tasks
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Tasks")

pets = owner.get_pets()
if not pets:
    st.info("Add a pet first before adding tasks.")
else:
    # --- Show tasks per pet with Done button and recurrence badge ----------
    for pet in pets:
        tasks = pet.get_tasks()
        if not tasks:
            continue
        st.markdown(f"**{pet.name}'s tasks:**")
        for task in tasks:
            col_info, col_btn = st.columns([6, 1])
            time_note = f" `{task.start_time}`" if task.start_time else (
                f" [{task.preferred_time}]" if task.preferred_time else ""
            )
            recur_badge = f" _{task.frequency}_" if task.frequency != "once" else ""
            done_note = "  ✅ done" if task.completed else ""
            col_info.markdown(
                f"- **{task.name}**{time_note} | {task.category} | "
                f"{task.duration_minutes} min | priority {task.priority}"
                f"{recur_badge}{done_note}"
            )
            if not task.completed:
                btn_key = f"done_{pet.name}_{task.name}_{id(task)}"
                if col_btn.button("Done", key=btn_key):
                    next_task = pet.complete_task(task.name)
                    if next_task:
                        st.toast(
                            f"'{task.name}' done! Next {task.frequency} occurrence: {next_task.due_date}",
                            icon="🔁",
                        )
                    st.rerun()

    # --- Add task form -----------------------------------------------------
    with st.expander("Add a task"):
        with st.form("task_form"):
            col1, col2 = st.columns(2)
            with col1:
                selected_pet_name = st.selectbox(
                    "For which pet?", [p.name for p in pets]
                )
                task_name = st.text_input("Task name", value="Morning Walk")
                category = st.selectbox(
                    "Category",
                    ["walk", "feed", "meds", "grooming", "enrichment", "play", "other"],
                )
                frequency = st.selectbox("Recurrence", ["once", "daily", "weekly"])
            with col2:
                duration = st.number_input(
                    "Duration (minutes)", min_value=1, max_value=240, value=20
                )
                priority = st.slider(
                    "Priority (1 = low, 5 = urgent)", min_value=1, max_value=5, value=3
                )
                preferred_time = st.selectbox(
                    "Preferred time", ["any", "morning", "afternoon", "evening"]
                )
                start_time_raw = st.text_input(
                    "Start time (HH:MM, optional)", value="",
                    placeholder="e.g. 07:30"
                )

            if st.form_submit_button("Add task"):
                if task_name.strip():
                    # Validate optional HH:MM
                    start_time: str | None = None
                    if start_time_raw.strip():
                        import re
                        if re.match(r"^\d{2}:\d{2}$", start_time_raw.strip()):
                            start_time = start_time_raw.strip()
                        else:
                            st.error("Start time must be in HH:MM format (e.g. 07:30).")
                            st.stop()

                    target_pet = next(
                        p for p in owner.get_pets() if p.name == selected_pet_name
                    )
                    target_pet.add_task(Task(
                        name=task_name.strip(),
                        category=category,
                        duration_minutes=int(duration),
                        priority=priority,
                        preferred_time=None if preferred_time == "any" else preferred_time,
                        start_time=start_time,
                        frequency=frequency,
                    ))
                    st.success(f"Added '{task_name.strip()}' for {target_pet.name}!")
                    st.rerun()
                else:
                    st.error("Task name cannot be empty.")

# ---------------------------------------------------------------------------
# Section 4 — Schedule & Smart Features
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Today's Schedule")

all_tasks = owner.get_all_tasks()
if not all_tasks:
    st.info("Add at least one pet and one task to generate a schedule.")
else:
    scheduler = Scheduler(owner=owner)

    # --- Conflict warnings (always visible when tasks exist) --------------
    conflicts = scheduler.detect_conflicts()
    if conflicts:
        st.warning(
            "**Scheduling conflicts detected** — two or more tasks share the same start time. "
            "Edit their start times to resolve before finalising your day."
        )
        for warning in conflicts:
            st.error(f"⚠️  {warning}")

    # --- View toggle -------------------------------------------------------
    view = st.radio(
        "View tasks by:",
        ["Priority (high → low)", "Time of day (chronological)"],
        horizontal=True,
    )

    if view.startswith("Time"):
        sorted_tasks = scheduler.sort_by_time()
        rows = []
        for t in sorted_tasks:
            rows.append({
                "Time": t.start_time or t.preferred_time or "—",
                "Task": t.name,
                "Pet": next(
                    (p.name for p in owner.get_pets() if t in p.get_tasks()), "?"
                ),
                "Category": t.category,
                "Duration": f"{t.duration_minutes} min",
                "Priority": t.priority,
                "Recurrence": t.frequency,
                "Done": "✅" if t.completed else "",
            })
        st.table(rows)
    else:
        sorted_tasks = scheduler.filter_by_priority()
        rows = []
        for t in sorted_tasks:
            rows.append({
                "Priority": t.priority,
                "Task": t.name,
                "Pet": next(
                    (p.name for p in owner.get_pets() if t in p.get_tasks()), "?"
                ),
                "Category": t.category,
                "Duration": f"{t.duration_minutes} min",
                "Recurrence": t.frequency,
                "Done": "✅" if t.completed else "",
            })
        st.table(rows)

    # --- Generate plan button ----------------------------------------------
    if st.button("Generate today's plan", type="primary"):
        plan = scheduler.generate_plan()

        if not plan:
            st.warning(
                "No tasks fit within today's time budget. "
                "Try increasing your available minutes or reducing task durations."
            )
        else:
            total_min = sum(t.duration_minutes for t in plan)
            remaining = owner.available_minutes - total_min
            st.success(
                f"**{len(plan)} tasks scheduled** — "
                f"{total_min} min used, {remaining} min remaining out of {owner.available_minutes} min"
            )
            plan_rows = []
            for t in plan:
                plan_rows.append({
                    "Task": t.name,
                    "Category": t.category,
                    "Duration": f"{t.duration_minutes} min",
                    "Priority": t.priority,
                    "Time": t.start_time or t.preferred_time or "—",
                    "Recurrence": t.frequency,
                })
            st.table(plan_rows)

        with st.expander("Scheduling explanation"):
            st.code(scheduler.explain_plan(), language=None)

    # --- Filter panel ------------------------------------------------------
    with st.expander("Filter tasks"):
        f_pet = st.selectbox(
            "Filter by pet", ["All"] + [p.name for p in owner.get_pets()],
            key="filter_pet"
        )
        f_status = st.selectbox(
            "Filter by status", ["All", "Pending", "Completed"],
            key="filter_status"
        )
        pet_arg = None if f_pet == "All" else f_pet
        completed_arg = None if f_status == "All" else (f_status == "Completed")
        filtered = scheduler.filter_tasks(pet_name=pet_arg, completed=completed_arg)
        if filtered:
            filter_rows = [
                {
                    "Task": t.name,
                    "Category": t.category,
                    "Duration": f"{t.duration_minutes} min",
                    "Priority": t.priority,
                    "Status": "Done" if t.completed else "Pending",
                }
                for t in filtered
            ]
            st.table(filter_rows)
        else:
            st.info("No tasks match this filter.")
