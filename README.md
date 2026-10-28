# 🥗 NutriAgent — AI Nutrition & Dietary Health Agent

An agentic AI application that analyzes your meals, enforces **strict structured JSON output**, cross-checks every result against your personal health profile, and gives you goal-based coaching on a clean dark-themed dashboard.

Built with **Streamlit**, **Groq (Llama 3.3 70B)** and **Pydantic**.




## ✨ Features

- 🍽️ **Meal analysis from text:** describe what you ate (e.g. *"2 rotis with chicken haleem and a glass of milk"*) and get calories, protein, carbs, fats, sodium and sugar.
- 🧾 **Structured output contract:** the agent must reply in a strict JSON schema, validated with Pydantic models (`MealAnalysis`, `Macros`).
- 👤 **Persistent health profile:** daily calorie target, fitness goal (Weight Loss, Muscle Gain, Lean Bulk, Diabetic Friendly, Keto Diet) and allergies/restrictions (Nuts, Gluten, Dairy, Seafood).
- ⚠️ **Allergen Interceptor:** a high-priority warning banner when a meal contains something matching your declared restrictions.
- 🎯 **Goal Alignment Score (0–100):** how well each meal fits your fitness goal, with a short physiological explanation and one actionable swap.
- 🤔 **Smart follow-up questions:** if a description is too vague, the agent asks one clarifying question before estimating.
- 🌐 **Optional live web search:** uses Groq's `compound-mini` agentic model to look up real nutrition facts for branded or restaurant food.
- 📊 **Daily tracker:** calorie progress bar, remaining calories, macro totals and a meal log.
- 🧠 **Weekly AI Insights:** the agent reviews your logged meals and proactively points out patterns (e.g. low protein, high sodium).
- 🍩 **Interactive macro chart:** Plotly donut chart for protein / carbs / fats.

## 🛠️ Tech Stack

| Layer            | Technology                                      |
| ---------------- | ----------------------------------------------- |
| UI               | [Streamlit](https://streamlit.io/)              |
| LLM provider     | [Groq](https://groq.com/)                       |
| Reasoning model  | `llama-3.3-70b-versatile`                       |
| Research model   | `groq/compound-mini` (built-in web search)      |
| Data validation  | [Pydantic](https://docs.pydantic.dev/)          |
| Charts           | [Plotly](https://plotly.com/python/)            |
| Language         | Python                                          |

## 🧠 How It Works

1. You enter your profile (calorie target, goal, restrictions) in the sidebar.
2. You describe a meal. Optionally, enable live web search for better accuracy.
3. The app builds a system prompt containing your profile (and web research, if enabled).
4. Llama 3.3 returns a JSON object, which is parsed and validated against the `MealAnalysis` Pydantic schema.
5. If the agent needs more detail, it asks **one** follow-up question, then finalizes its estimate.
6. The result is shown with macros, allergen alerts, goal score and coaching, and added to your daily log.

## 📁 Project Structure

```
food-agent-app/
├── app.py             # Main Streamlit application
├── requirements.txt   # Python dependencies
├── runtime.txt        # Python version for deployment
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or newer
- A free [Groq API key](https://console.groq.com/keys)

### Installation

```bash
# Clone the repository
git clone https://github.com/tariqkhan197/food-agent-app.git
cd food-agent-app

# (Recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure your API key

Provide your Groq API key in **one** of these ways:

**Option 1: Streamlit secrets** (recommended)

Create `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "gsk_your_key_here"
```

**Option 2: Environment variable**

```bash
export GROQ_API_KEY="gsk_your_key_here"      # Windows (PowerShell): $env:GROQ_API_KEY="gsk_..."
```

> ⚠️ Never commit your API key to GitHub. Make sure `.streamlit/secrets.toml` and `.venv` are in your `.gitignore`.

### Run the app

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501).

## ☁️ Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io) and create a new app from your repo (main file: `app.py`).
3. Open **App settings → Secrets** and add:
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   ```
4. Deploy 🚀

## 📸 Example

**Input:**

> I had 3 rotis and a plate of mutton curry

**Output (structured JSON, simplified):**

```json
{
  "is_food": true,
  "identified_items": ["3 rotis (~30g each)", "1 plate of mutton curry (~275g, estimated)"],
  "macros": { "calories": 650, "protein_g": 35.0, "carbs_g": 60.0, "fats_g": 22.0, "sodium_mg": 780.0, "sugar_g": 9.0 },
  "allergen_alerts": [],
  "goal_alignment_score": 62,
  "coach_reasoning": "..."
}
```

## ⚠️ Disclaimer

NutriAgent provides **estimates** generated by an AI model for general informational purposes only. It is not a substitute for professional medical or dietary advice. Always consult a qualified healthcare professional for medical conditions, allergies or specific dietary needs.

## 🗺️ Roadmap

- [ ] Real image-based meal recognition (vision model)
- [ ] Persistent storage for meal history across sessions
- [ ] Weekly/monthly progress charts
- [ ] Export meal log as CSV

## 📬 Contact

**Tariq Khan**

- GitHub: [@tariqkhan197](https://github.com/tariqkhan197)



---

⭐ If you found this project useful, consider giving it a star!
