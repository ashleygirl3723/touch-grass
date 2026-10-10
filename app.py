"""
Touch Grass — an honest AI that prescribes the outdoors,
then tells you to put the phone down.

Built for the Hacktoberfest 2026 DEV Challenge, Week 1 ("Touch Grass").
Open-weight model via OpenRouter's free tier. No API paywall.

How it works:
  1. You say how much time and energy you have, and what's around you.
  2. The AI gives you a straight outdoor prescription — no guilt trips.
  3. The last line is always "Phone down. Go." The screen is the
     shortest part of the experience.

Run it:
  pip install -r requirements.txt
  streamlit run app.py
"""

import os

import streamlit as st
from openai import OpenAI

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
MODEL = "openrouter/free"  # OpenRouter auto-router: picks a working free open-weight model each call

SYSTEM_PROMPT = """You are Touch Grass, a thought partner whose only loyalty is getting the user off their phone and outside. Your job: hear their time, energy, surroundings, and conditions, then prescribe an honest outdoor outing.

Rules:
1. Be honest about what fits. If they claim beast-mode energy but it's midnight and raining, say so and downscale. Never prescribe something they won't actually do.
2. No guilt trips, no toxic positivity. Don't shame them for being inside. Don't oversell nature as a miracle cure.
3. Concrete over vague. Name the actual activity, where to do it, and how long. "Walk to the park and back, 20 minutes" beats "go enjoy nature."
4. Give them one thing to notice while they're out there — a sound, a smell, something to look at. One thing, not a list.
5. Keep it short. The screen is the shortest part of this experience. Under 150 words for the prescription.
6. End every first response with a prescription block and the exact words "Phone down. Go." on their own line.

Response format for the first prescription — use these headers:
- **The prescription** — what to do, where, how long
- **One thing to notice** — a single sensory detail to look for
- **Phone down. Go.**

Follow-ups: the user can ask for adjustments ("what if it starts raining?", "somewhere closer?", "I only have 10 minutes"). Stay in character — honest, brief. If they keep stalling, call it out kindly and shrink the prescription until it's undeniable. Never extend screen time; every answer should end with them closer to the door, not deeper in chat."""


def ask(client, messages):
    """Send the whole conversation (plus the system prompt) to the AI."""
    reply = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + messages,
    )
    return reply.choices[0].message.content


# ---------------------------------------------------------------------------
# Page setup + conversation state
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Touch Grass", page_icon="🌿", layout="centered")
st.title("🌿 Touch Grass")
st.caption("Tell it your time and energy. Get an honest outdoor prescription. Then put the phone down.")

# Conversation state survives reruns while the tab is open.
for key, default in [("active", False), ("messages", [])]:
    if key not in st.session_state:
        st.session_state[key] = default

# API key: sidebar field first, then Streamlit secrets, then environment.
# (On Streamlit Cloud you paste the key once under Settings → Secrets.)
api_key = st.sidebar.text_input("OpenRouter API key", type="password",
                                help="Pasted here it lives only in this session. On Streamlit Cloud, use Settings → Secrets instead.")
api_key = api_key or st.secrets.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")


# ---------------------------------------------------------------------------
# Intake form — shown until the first prescription comes back
# ---------------------------------------------------------------------------
if not st.session_state.active:
    time_available = st.selectbox(
        "How much time do you actually have?",
        ["15 minutes", "30 minutes", "1 hour", "Half a day", "The whole day"],
    )

    energy = st.select_slider(
        "Energy level — be honest",
        options=["Couch mode", "Gentle stroll", "Ready to move", "Beast mode"],
        value="Gentle stroll",
    )

    surroundings = st.text_area(
        "What's around you?",
        height=100,
        placeholder="Neighborhood sidewalks, a park ten minutes away, the Oregon coast, a trailhead, just my backyard…",
    )

    weather = st.text_input(
        "Weather / anything else? (optional)",
        placeholder="Drizzling, 85 and sunny, pitch dark out, knee's acting up…",
    )

    if st.button("Prescribe my grass", type="primary", use_container_width=True):
        if not api_key:
            st.error("Add your OpenRouter API key in the sidebar first — the app can't think without one. (Free at openrouter.ai/keys, no credit card.)")
        else:
            first_message = (
                f"TIME AVAILABLE: {time_available}\n\n"
                f"ENERGY LEVEL: {energy}\n\n"
                f"WHAT'S AROUND ME:\n{surroundings.strip() or '(not specified)'}\n\n"
                f"WEATHER / OTHER:\n{weather.strip() or '(not specified)'}"
            )
            st.session_state.messages = [{"role": "user", "content": first_message}]
            try:
                with st.spinner("Reading the sky…"):
                    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
                    answer = ask(client, st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                st.session_state.active = True
                st.rerun()
            except Exception as e:  # show the real error so you can learn from it
                st.error(f"Something went wrong talking to the AI: {e}")

# ---------------------------------------------------------------------------
# Conversation view — the prescription plus a follow-up box for adjustments
# ---------------------------------------------------------------------------
else:
    if st.button("↩ Start over"):
        st.session_state.active = False
        st.session_state.messages = []
        st.rerun()

    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    followup = st.chat_input("Need an adjustment? Closer, shorter, raining…")
    if followup:
        st.session_state.messages.append({"role": "user", "content": followup})
        try:
            with st.spinner("Rethinking…"):
                client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
                answer = ask(client, st.session_state.messages)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()
        except Exception as e:
            st.error(f"Something went wrong talking to the AI: {e}")
            st.session_state.messages.pop()  # drop the failed question so retry is clean
