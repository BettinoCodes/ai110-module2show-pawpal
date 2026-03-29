import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Session state — persists across Streamlit reruns
# Think of this as a vault: the Owner object lives here so it is not
# recreated from scratch every time the page refreshes.
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
            min_value=10, max_value=480,
            value=owner.available_minutes,
        )
    if st.form_submit_button("Save"):
        owner.name = owner_name.strip() or owner.name
        owner.set_available_time(int(available))
        st.success(f"Saved: {owner.name}, {owner.available_minutes} min/day")

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
                new_pet = Pet(
                    name=pet_name.strip(),
                    species=species,
                    age=int(age),
                    breed=breed.strip(),
                )
                owner.add_pet(new_pet)
                st.success(f"Added {new_pet.name}!")
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
    # Show existing tasks for each pet with a "Mark done" button
    for pet in pets:
        tasks = pet.get_tasks()
        if tasks:
            st.markdown(f"**{pet.name}'s tasks:**")
            for task in tasks:
                col_label, col_btn = st.columns([5, 1])
                pref = f" [{task.preferred_time}]" if task.preferred_time else ""
                status = " ✓ done" if task.completed else ""
                col_label.markdown(
                    f"- {task.name}{pref} | {task.category} | "
                    f"{task.duration_minutes} min | priority {task.priority}{status}"
                )
                if not task.completed:
                    btn_key = f"done_{pet.name}_{task.name}"
                    if col_btn.button("Done", key=btn_key):
                        task.mark_complete()
                        st.rerun()

    # Form to add a new task
    st.markdown("**Add a task:**")
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
        with col2:
            duration = st.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20
            )
            priority = st.slider("Priority (1 = low, 5 = urgent)", min_value=1, max_value=5, value=3)
            preferred_time = st.selectbox(
                "Preferred time", ["any", "morning", "afternoon", "evening"]
            )

        if st.form_submit_button("Add task"):
            if task_name.strip():
                # Find the target pet by name (first match)
                target_pet = next(
                    p for p in owner.get_pets() if p.name == selected_pet_name
                )
                new_task = Task(
                    name=task_name.strip(),
                    category=category,
                    duration_minutes=int(duration),
                    priority=priority,
                    preferred_time=None if preferred_time == "any" else preferred_time,
                )
                target_pet.add_task(new_task)
                st.success(f"Added '{new_task.name}' for {target_pet.name}!")
                st.rerun()
            else:
                st.error("Task name cannot be empty.")

# ---------------------------------------------------------------------------
# Section 4 — Generate schedule
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Today's Schedule")

all_tasks = owner.get_all_tasks()
if not all_tasks:
    st.info("Add at least one pet and one task to generate a schedule.")
else:
    if st.button("Generate schedule", type="primary"):
        scheduler = Scheduler(owner=owner)
        plan = scheduler.generate_plan()

        if not plan:
            st.warning(
                "No tasks fit within today's time budget. "
                "Try increasing your available time or reducing task durations."
            )
        else:
            total_min = sum(t.duration_minutes for t in plan)
            remaining = owner.available_minutes - total_min
            st.success(
                f"{len(plan)} tasks scheduled — "
                f"{total_min} min used, {remaining} min remaining"
            )
            for task in plan:
                pref = f" [{task.preferred_time}]" if task.preferred_time else ""
                st.markdown(
                    f"- **{task.name}**{pref} | {task.category} | "
                    f"{task.duration_minutes} min | priority {task.priority}"
                )

        st.divider()
        st.markdown("**Scheduling explanation:**")
        st.code(scheduler.explain_plan(), language=None)
