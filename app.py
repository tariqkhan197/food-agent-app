"""
NutriAgent — AI Nutrition & Dietary Health Agent
=================================================
A production-grade Streamlit application powered by Groq Llama-3.3
that analyzes meals from text, enforces strict structured (JSON) output, 
cross-references results against a persistent user health profile, 
and renders a premium dark-slate coaching dashboard.

SETUP
-----
1. pip install streamlit groq pydantic plotly pillow
2. Provide your Groq API key via:
      .streamlit/secrets.toml  ->  GROQ_API_KEY = "gsk_..."
3. streamlit run app.py
"""

import io
import json
import os
from datetime import datetime
from typing import List, Any,Optional

import streamlit as st
from groq import Groq

try:
    import plotly.graph_objects as go
except ImportError:  # pragma: no cover
    go = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

try:
    from pydantic import BaseModel, Field, ValidationError
except ImportError:  # pragma: no cover
    st.error("Missing dependency `pydantic`. Run: pip install pydantic")
    st.stop()


# =============================================================================
# 1. STRUCTURED OUTPUT SCHEMA (The Agent's Contract)
# =============================================================================

class Macros(BaseModel):
    calories: int = Field(description="Total estimated calories (kcal) for the meal")
    protein_g: float = Field(description="Total protein in grams")
    carbs_g: float = Field(description="Total carbohydrates in grams")
    fats_g: float = Field(description="Total fats in grams")
    sodium_mg: float = Field(description="Total sodium in milligrams")
    sugar_g: float = Field(description="Total sugar in grams")


class MealAnalysis(BaseModel):
    is_food: bool = Field(description="True only if the input clearly depicts/describes food or drink")
    rejection_message: str = Field(
        default="",
        description="Polite explanation if is_food is False, otherwise empty string",
    )
    identified_items: List[Any] = Field(
        default_factory=list,
        description="Specific identified components of the meal, e.g. ['2 whole wheat rotis', 'chicken haleem', '1 glass whole milk']",
    )
    macros: Macros
    allergen_alerts: List[str] = Field(
        default_factory=list,
        description="Allergens/restricted ingredients detected in the meal that match the user's stated restrictions",
    )
    goal_alignment_score: int = Field(
        ge=0, le=100,
        description="1-100 score of how well this meal aligns with the user's stated fitness goal",
    )
    coach_reasoning: str = Field(
        description="3-4 sentence physiological explanation plus one concrete actionable swap/tweak"
    )


FITNESS_GOALS = ["Weight Loss", "Muscle Gain", "Lean Bulk", "Diabetic Friendly", "Keto Diet"]
RESTRICTION_OPTIONS = ["Nuts", "Gluten", "Dairy", "Seafood", "None"]


# =============================================================================
# 2. SESSION STATE / AGENT MEMORY
# =============================================================================

def init_state() -> None:
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "calorie_target": 2000,
            "goal": "Weight Loss",
            "restrictions": [],
        }
    if "meal_log" not in st.session_state:
        st.session_state.meal_log = []  # list[dict] of logged meal analyses
    if "consumed_calories" not in st.session_state:
        st.session_state.consumed_calories = 0
    if "consumed_macros" not in st.session_state:
        st.session_state.consumed_macros = {"protein": 0.0, "carbs": 0.0, "fats": 0.0}
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_error" not in st.session_state:
        st.session_state.last_error = None


# =============================================================================
# 3. API KEY RESOLUTION
# =============================================================================

def resolve_api_key():
    


# =============================================================================
# 4. THE UNIFIED DUAL-INPUT PROCESSING PIPELINE
# =============================================================================

def build_system_instruction(user_profile: dict) -> str:
    restrictions = ", ".join(user_profile["restrictions"]) if user_profile["restrictions"] else "None declared"
    return f"""You are NutriAgent, an elite clinical nutrition and dietary coaching AI. You analyze a user's meal description and return a rigorous nutritional breakdown personalized to their health profile.

USER PROFILE:
- Daily Calorie Target: {user_profile['calorie_target']} kcal
- Primary Fitness Goal: {user_profile['goal']}
- Declared Allergies/Restrictions: {restrictions}

INSTRUCTIONS:
1. First determine if the input actually describes food or a beverage. If it clearly does not, set is_food=false, write a short polite rejection_message, and fill macros with zeros and identified_items/allergen_alerts as empty lists.
2. Identify each distinct food/drink component separately in identified_items with realistic portion sizes.
3. Estimate macros (calories, protein_g, carbs_g, fats_g, sodium_mg, sugar_g) as realistically as possible using standard nutritional databases as a mental reference. Never leave macros at zero for real food.
4. allergen_alerts must ONLY include items that are BOTH present in the meal AND relevant to the user's declared restrictions above.
5. goal_alignment_score (1-100): critically evaluate how well this specific meal serves the user's stated Primary Fitness Goal.
6. coach_reasoning: Write 3-4 dense sentences of physiological reasoning explaining why this meal helps or hurts their specific goal, and end with ONE concrete, actionable swap/tweak.

Respond ONLY with a single valid JSON object matching the required schema structure. No markdown fences, no formatting text, no explanations outside JSON.
"""


def process_agent_input(text_query: Optional[str] = None, image_file=None, user_profile: Optional[dict] = None):
    if not text_query and image_file is None:
        return None, "No input provided. Please enter a description or upload an image."

    api_key = resolve_api_key()
    if not api_key:
        return None, "No Groq API key found. Set GROQ_API_KEY in `.streamlit/secrets.toml`."

    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        return None, f"Failed to initialize the Groq client: {e}"

    contents = ""
    if text_query:
        contents += f"User Text Description: {text_query.strip()}\n"
    
    if image_file is not None:
        contents += "[An image was uploaded by the user. Please analyze the nutritional value primarily based on the text description provided and context.]"

    system_instruction = build_system_instruction(user_profile or {
        "calorie_target": 200, "goal": "Weight Loss", "restrictions": []
    })

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": contents}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=2048,
        )
    except Exception as e:
        msg = str(e)
        if "timeout" in msg.lower() or "deadline" in msg.lower():
            return None, "The AI agent timed out while analyzing your meal. Please try again."
        return None, f"Agent API error: {msg}"

    raw_text = response.choices[0].message.content
    if not raw_text:
        return None, "The agent returned an empty response. Please try again."

    # --- Robust parsing ---
    try:
        data = json.loads(raw_text)
        return MealAnalysis(**data), None
    except (json.JSONDecodeError, ValidationError):
        pass

    try:
        start = raw_text.find("{")
        end = raw_text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object found in response")
        data = json.loads(raw_text[start:end + 1])
        return MealAnalysis(**data), None
    except Exception as e:
        return None, f"Could not parse the agent's response into a valid nutrition record ({e})."


# =============================================================================
# 5. UI — THEME
# =============================================================================

def inject_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: linear-gradient(180deg, #0b0f17 0%, #10151f 100%);
            color: #e6e9ef;
        }
        section[data-testid="stSidebar"] {
            background: #0d1119;
            border-right: 1px solid #1f2733;
        }
        h1, h2, h3, h4 {
            color: #f2f4f8 !important;
            font-weight: 700 !important;
        }
        .stButton>button {
            background: linear-gradient(135deg, #2e7d5b, #1f5f47);
            color: #f2f4f8;
            border: 1px solid #3a9c73;
            border-radius: 10px;
            font-weight: 600;
            padding: 0.55em 1em;
        }
        .stButton>button:hover {
            border: 1px solid #5fd9a4;
            color: #ffffff;
        }
        div[data-testid="stMetric"] {
            background: #141a24;
            border: 1px solid #232c3a;
            border-radius: 12px;
            padding: 10px 14px;
        }
        div[data-testid="stExpander"] {
            background: #10151f;
            border: 1px solid #232c3a;
            border-radius: 10px;
        }
        textarea, input {
            background-color: #141a24 !important;
            color: #e6e9ef !important;
        }
        hr { border-color: #232c3a; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =============================================================================
# 6. UI — SIDEBAR (Profile + Live Tracker)
# =============================================================================

def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 🧬 Your Health Profile")

        st.session_state.profile["calorie_target"] = st.number_input(
            "Daily Calorie Target (kcal)",
            min_value=1000, max_value=6000,
            value=int(st.session_state.profile["calorie_target"]),
            step=50,
        )

        current_goal = st.session_state.profile.get("goal", "Weight Loss")
        goal_index = FITNESS_GOALS.index(current_goal) if current_goal in FITNESS_GOALS else 0
        st.session_state.profile["goal"] = st.selectbox(
            "Primary Fitness Goal", FITNESS_GOALS, index=goal_index
        )

        st.markdown("#### 🚫 Dietary Restrictions / Allergies")
        current_restrictions = set(st.session_state.profile.get("restrictions", []))
        selected: List[str] = []
        cols = st.columns(2)
        for i, opt in enumerate(RESTRICTION_OPTIONS):
            with cols[i % 2]:
                checked = st.checkbox(opt, value=opt in current_restrictions, key=f"restriction_{opt}")
                if checked:
                    selected.append(opt)
        if "None" in selected:
            selected = []
        st.session_state.profile["restrictions"] = selected

        st.divider()
        st.markdown("### 🔥 Today's Progress")

        target = max(st.session_state.profile["calorie_target"], 1)
        consumed = st.session_state.consumed_calories
        pct = min(consumed / target, 1.0)
        remaining = target - consumed

        st.progress(pct, text=f"{consumed} / {target} kcal consumed")
        m1, m2 = st.columns(2)
        m1.metric("Remaining", f"{max(remaining, 0)} kcal")
        m2.metric("Meals Logged", f"{len(st.session_state.meal_log)}")

        if remaining < 0:
            st.warning(f"You are {abs(remaining)} kcal over your daily target.")

        cm = st.session_state.consumed_macros
        st.caption(
            f"Protein: {cm['protein']:.0f}g · Carbs: {cm['carbs']:.0f}g · Fats: {cm['fats']:.0f}g"
        )

        st.divider()
        if st.button("🔄 Reset Today's Log", use_container_width=True):
            st.session_state.meal_log = []
            st.session_state.consumed_calories = 0
            st.session_state.consumed_macros = {"protein": 0.0, "carbs": 0.0, "fats": 0.0}
            st.session_state.last_result = None
            st.rerun()

        with st.expander("⚙️ Agent Configuration"):
            key_status = "✅ Detected" if resolve_api_key() else "❌ Missing"
            st.caption(f"GROQ_API_KEY: {key_status}")
            st.caption("Model: `llama-3.3-70b-versatile`")


# =============================================================================
# 7. UI — RESULT RENDERING (Allergen Interceptor, Macros, Coaching)
# =============================================================================

def macro_pie_chart(macros: Macros):
    if go is None:
        st.info("Install `plotly` for macro visualizations: pip install plotly")
        return
    values = [macros.protein_g, macros.carbs_g, macros.fats_g]
    if sum(values) <= 0:
        st.info("No macro data to visualize.")
        return
    fig = go.Figure(
        data=[
            go.Pie(
                labels=["Protein", "Carbs", "Fats"],
                values=values,
                hole=0.55,
                marker=dict(colors=["#4dd0e1", "#ffb74d", "#ba68c8"]),
                textinfo="label+percent",
                textfont=dict(color="#e6e9ef"),
            )
        ]
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6e9ef"),
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", y=-0.1),
        height=300,
        showlegend=True,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_allergen_alert(result: MealAnalysis) -> None:
    profile_restrictions = [r.lower() for r in st.session_state.profile["restrictions"]]
    if not profile_restrictions or not result.allergen_alerts:
        return
    matched = [
        a for a in result.allergen_alerts
        if any(r in a.lower() or a.lower() in r for r in profile_restrictions)
    ]
    if not matched:
        return
    st.markdown(
        f"""
        <div style="background:#3b0d0d;border:2px solid #ff4d4d;border-radius:12px;
                    padding:16px 18px;margin-bottom:18px;">
            <h4 style="color:#ff6b6b;margin:0 0 6px 0;">⚠️ ALLERGEN INTERCEPTOR — HIGH PRIORITY</h4>
            <p style="color:#ffd6d6;margin:0;">
                This meal appears to contain <b>{', '.join(matched)}</b>, which matches your declared
                restrictions. Proceed with caution.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_result(result: MealAnalysis) -> None:
    if not result.is_food:
        st.info(
            f"🤖 {result.rejection_message or 'This does not look like food. Please describe or upload a meal.'}"
        )
        return

    render_allergen_alert(result)

    st.markdown("### 🍽️ Identified Items")
    if result.identified_items:
        for item_data in result.identified_items:
            if isinstance(item_data, dict):
                name = item_data.get('item', '')
                portion = item_data.get('portion_size', '')
                st.write(f"• **{name}** ({portion})")
            else:
                st.write(f"• {item_data}")
    else:
        st.write("-")

    m = result.macros
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Calories", f"{m.calories} kcal")
    c2.metric("Protein", f"{m.protein_g:.1f} g")
    c3.metric("Carbs", f"{m.carbs_g:.1f} g")
    c4.metric("Fats", f"{m.fats_g:.1f} g")

    c5, c6 = st.columns(2)
    c5.metric("Sodium", f"{m.sodium_mg:.0f} mg")
    c6.metric("Sugar", f"{m.sugar_g:.1f} g")

    st.markdown("#### Macro Breakdown")
    macro_pie_chart(m)

    score = result.goal_alignment_score
    color = "#4caf50" if score >= 70 else "#ffb300" if score >= 40 else "#ef5350"
    st.markdown(
        f"""
        <div style="background:#141a24;border-radius:12px;padding:14px 18px;margin:12px 0 6px 0;
                    border-left:5px solid {color};">
            <b style="color:{color};font-size:1.05em;">
                Goal Alignment Score ({st.session_state.profile['goal']}): {score}/100
            b>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.progress(score / 100)

    st.markdown("### 🧠 Coach's Analysis")
    st.markdown(
        f"""<div style="background:#10151f;border:1px solid #232c3a;padding:16px;
                       border-radius:12px;line-height:1.65;color:#d7dce4;">
                {result.coach_reasoning}
            </div>""",
        unsafe_allow_html=True,
    )


def render_history() -> None:
    st.markdown("### 📜 Today's Meal Log")
    for i, entry in enumerate(reversed(st.session_state.meal_log)):
        raw_items = entry.get("identified_items", [])
        formatted_items = []
        for item_data in raw_items:
            if isinstance(item_data, dict):
                formatted_items.append(item_data.get('item', 'Meal'))
            else:
                formatted_items.append(str(item_data))

        items = ", ".join(formatted_items) or "Meal"
        cal = entry.get("macros", {}).get("calories", 0)
        with st.expander(f"{items} — {cal} kcal"):
            st.json(entry)


# =============================================================================
# 8. UI — MAIN INPUT PANEL
# =============================================================================

def render_main() -> None:
    st.title("🥗 NutriAgent")
    st.caption(
        "Your AI Dietary Health Agent — log meals by text, photo, or both, and get "
        "physiologically-grounded coaching tailored to your goals and restrictions."
    )

    col1, col2 = st.columns([3, 2])
    with col1:
        text_query = st.text_area(
            "Describe your meal",
            placeholder="e.g. I had 2 rotis with chicken haleem and a glass of milk",
            height=120,
        )
    with col2:
        image_file = st.file_uploader("Or upload a photo", type=["png", "jpg", "jpeg", "webp"])
        if image_file is not None:
            st.image(image_file, use_column_width=True)

    analyze_clicked = st.button("🔍 Analyze Meal", type="primary", use_container_width=True)

    if analyze_clicked:
        if not text_query and image_file is None:
            st.warning("Please enter a meal description or upload a photo before analyzing.")
        else:
            with st.spinner("NutriAgent is cross-referencing your meal against your health profile..."):
                result, error = process_agent_input(
                    text_query=text_query or None,
                    image_file=image_file,
                    user_profile=st.session_state.profile,
                )
            st.session_state.last_error = error
            st.session_state.last_result = result

            if result and result.is_food:
                st.session_state.meal_log.append(result.model_dump())
                st.session_state.consumed_calories += result.macros.calories
                st.session_state.consumed_macros["protein"] += result.macros.protein_g
                st.session_state.consumed_macros["carbs"] += result.macros.carbs_g
                st.session_state.consumed_macros["fats"] += result.macros.fats_g

            st.rerun()

    if st.session_state.last_error:
        st.error(st.session_state.last_error)
        st.session_state.last_error = None
    elif st.session_state.last_result is not None:
        render_result(st.session_state.last_result)

    if st.session_state.meal_log:
        st.divider()
        render_history()


# =============================================================================
# 9. ENTRYPOINT
# =============================================================================

def main() -> None:
    st.set_page_config(
        page_title="NutriAgent — AI Nutrition Coach",
        page_icon="🥗",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_theme()
    init_state()
    render_sidebar()
    render_main()


if __name__ == "__main__":
    main()