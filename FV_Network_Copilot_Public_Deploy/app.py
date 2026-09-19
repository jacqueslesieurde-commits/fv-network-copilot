
import json
import re
from pathlib import Path
import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

BASE_DIR = Path(__file__).parent

with open(BASE_DIR / "network_profiles.json", encoding="utf-8") as f:
    PROFILES = json.load(f)

with open(BASE_DIR / "startup_scenarios.json", encoding="utf-8") as f:
    SCENARIOS = json.load(f)

# ----------------------------
# Deterministic fallback layer
# ----------------------------
COUNTRY_KEYWORDS = {
    "germany": "Germany", "german": "Germany", "allemagne": "Germany", "allemand": "Germany",
    "france": "France", "french": "France",
    "uk": "United Kingdom", "united kingdom": "United Kingdom", "royaume-uni": "United Kingdom",
    "usa": "United States", "us": "United States", "united states": "United States", "états-unis": "United States",
    "italy": "Italy", "italie": "Italy",
    "spain": "Spain", "espagne": "Spain",
    "sweden": "Sweden", "suède": "Sweden",
    "norway": "Norway", "norvège": "Norway",
    "denmark": "Denmark", "danemark": "Denmark",
    "netherlands": "Netherlands", "pays-bas": "Netherlands",
    "belgium": "Belgium", "belgique": "Belgium",
    "israel": "Israel", "poland": "Poland", "pologne": "Poland",
}

INDUSTRY_KEYWORDS = {
    "industrial": "Industrial Technology", "industrie": "Industrial Technology",
    "manufacturing": "Manufacturing", "automotive": "Automotive", "automobile": "Automotive",
    "energy": "Energy", "énergie": "Energy", "climate": "Climate", "climat": "Climate",
    "ai": "AI", "ia": "AI", "software": "Enterprise Software", "saas": "Enterprise Software",
    "cyber": "Cybersecurity", "cybersecurity": "Cybersecurity",
    "robotics": "Robotics", "robotique": "Robotics",
    "health": "Health", "santé": "Health", "longevity": "Longevity", "longévité": "Longevity",
    "retail": "Retail", "logistics": "Logistics", "logistique": "Logistics",
    "defense": "Defense", "défense": "Defense",
}

NEED_RULES = {
    "Market entry": ["enter", "launch", "expand", "market entry", "entrer", "lancer", "développer", "expansion"],
    "Enterprise sales": ["enterprise", "large customer", "large customers", "industrial customers",
                         "grand compte", "grands comptes", "sign our first", "sign clients", "sales"],
    "Customer introductions": ["introduction", "introductions", "clients", "customers", "prospects", "contacts"],
    "GTM strategy": ["gtm", "go-to-market", "go to market", "market strategy", "market entry", "enter germany",
                     "enter france", "enter the", "expansion"],
    "Recruitment": ["hire", "hiring", "recruit", "recrut", "vp sales", "talent"],
    "Strategic partnerships": ["partner", "partnership", "partners", "partenaire", "partenariat"],
    "Fundraising": ["fundraising", "raise", "levée", "investor", "investisseur"],
    "Regulation": ["regulation", "regulatory", "réglement", "compliance"],
    "Industrial pilots": ["pilot", "pilots", "pilote", "proof of concept", "poc"],
    "Pricing": ["pricing", "price", "tarif", "prix"],
}

HELP_SYNONYMS = {
    "Market entry": ["market entry", "gtm", "expansion", "german gtm", "uk gtm", "us gtm"],
    "Enterprise sales": ["enterprise sales", "commercial strategy", "sales strategy", "sales playbook", "b2b sales",
                         "automotive sales", "public sector sales"],
    "Customer introductions": ["customer introductions", "introductions", "pilot customers", "oem introductions",
                               "hospital introductions", "industrial introductions", "buyer introductions"],
    "GTM strategy": ["gtm", "market entry", "launch strategy", "sales playbook", "growth strategy"],
    "Recruitment": ["hiring", "recruitment", "executive search", "vp hiring", "sales hiring"],
    "Strategic partnerships": ["partnership", "partner", "ecosystem", "commercial partnerships"],
    "Fundraising": ["fundraising", "investor introductions", "fundraising readiness"],
    "Regulation": ["regulation", "regulatory"],
    "Industrial pilots": ["pilot", "pilots", "pilot customers", "pilot design"],
    "Pricing": ["pricing"],
}

def normalise(text):
    return re.sub(r"\s+", " ", text.lower()).strip()

def fallback_extract(request):
    t = normalise(request)
    countries = []
    for kw, value in COUNTRY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", t) and value not in countries:
            countries.append(value)

    industries = []
    for kw, value in INDUSTRY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(kw)}\b", t) and value not in industries:
            industries.append(value)

    needs = []
    for need, keywords in NEED_RULES.items():
        if any(kw in t for kw in keywords):
            needs.append(need)

    if not needs:
        needs = ["Strategic support"]

    if "Market entry" in needs:
        objective = "International market expansion"
    elif "Recruitment" in needs:
        objective = "Team scaling"
    elif "Fundraising" in needs:
        objective = "Fundraising readiness"
    elif "Industrial pilots" in needs:
        objective = "Secure industrial pilots"
    else:
        objective = "Founder support"

    return {
        "objective": objective,
        "countries": countries,
        "industries": industries,
        "needs": needs,
        "support_plan": fallback_support_plan({
            "objective": objective,
            "countries": countries,
            "industries": industries,
            "needs": needs,
        }),
        "success_metric": "Define a measurable outcome with the founder.",
        "assumptions": ["Analysis based only on the founder request provided."]
    }

def fallback_support_plan(analysis):
    plan = []
    countries = analysis.get("countries", [])
    needs = analysis.get("needs", [])
    if "Market entry" in needs:
        market = countries[0] if countries else "target market"
        plan.append(f"Validate the go-to-market assumptions for {market}.")
    if "Enterprise sales" in needs:
        plan.append("Pressure-test the enterprise sales motion and target-account strategy.")
    if "Customer introductions" in needs:
        plan.append("Clarify the ideal customer profile, then identify high-value warm introductions.")
    if "Recruitment" in needs:
        plan.append("Define the role scorecard and identify operators who can benchmark or refer candidates.")
    if "Strategic partnerships" in needs:
        plan.append("Map the most relevant strategic partners and prioritise warm paths through the network.")
    if "Fundraising" in needs:
        plan.append("Review fundraising readiness, investor narrative and relevant investor introductions.")
    if "Regulation" in needs:
        plan.append("Validate the key regulatory questions with a relevant operator or domain expert.")
    if "Industrial pilots" in needs:
        plan.append("Select 3–5 potential pilot customers and define a clear pilot value proposition.")
    if "Pricing" in needs:
        plan.append("Benchmark pricing assumptions with an operator who knows the target market.")
    if len(plan) < 3:
        plan.append("Clarify the founder's highest-priority bottleneck and desired outcome.")
        plan.append("Match the need with the smallest set of relevant operators in the network.")
    return plan[:4]

# ----------------------------
# LLM layer
# ----------------------------
def clean_json_text(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()

def llm_extract(request, api_key):
    if OpenAI is None:
        raise RuntimeError("The OpenAI Python package is not installed.")

    client = OpenAI(api_key=api_key)

    system_prompt = """
You are the intake intelligence layer of FV Network Copilot, a prototype for Family Ventures.

Your job is NOT to choose network members. A deterministic matching engine will do that later.
Your job is to understand a founder's request and convert it into structured, useful information.

Return ONLY valid JSON. No markdown and no extra text.

Use this exact schema:
{
  "objective": "short business objective",
  "countries": ["Country"],
  "industries": ["Industry"],
  "needs": ["Need"],
  "support_plan": ["Action 1", "Action 2", "Action 3", "Action 4"],
  "success_metric": "one measurable outcome",
  "assumptions": ["assumption or missing information"]
}

Allowed needs:
- Market entry
- Enterprise sales
- Customer introductions
- GTM strategy
- Recruitment
- Strategic partnerships
- Fundraising
- Regulation
- Industrial pilots
- Pricing
- Strategic support

Industry labels should preferably use:
Industrial Technology, Manufacturing, Automotive, Energy, Climate, AI,
Enterprise Software, Cybersecurity, Robotics, Health, Longevity, Retail,
Logistics, Defense.

Rules:
- Extract only what is supported by the founder request.
- You may infer a useful need when it is a direct business implication, but list uncertainty under assumptions.
- Do not invent company facts, contacts, traction, geography, or deadlines.
- Keep the support plan practical for an investor / operator network.
- Customer introductions should not be the first action if the commercial target or ICP is still unclear.
"""
    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=system_prompt,
        input=request
    )
    data = json.loads(clean_json_text(response.output_text))

    # Ensure keys always exist
    data.setdefault("objective", "Founder support")
    data.setdefault("countries", [])
    data.setdefault("industries", [])
    data.setdefault("needs", ["Strategic support"])
    data.setdefault("support_plan", [])
    data.setdefault("success_metric", "Define a measurable outcome with the founder.")
    data.setdefault("assumptions", [])
    return data

# ----------------------------
# Explainable ranking engine
# ----------------------------
def list_overlap_score(requested, profile_values, max_points):
    if not requested:
        return 0, []
    requested_lower = {x.lower() for x in requested}
    profile_lower = {x.lower() for x in profile_values}
    hits = requested_lower.intersection(profile_lower)
    if not hits:
        return 0, []
    ratio = len(hits) / len(requested_lower)
    return round(max_points * ratio), sorted(hits)

def semantic_help_hits(needs, profile):
    haystack = " | ".join(profile.get("expertise", []) + profile.get("can_help_with", [])).lower()
    hits = []
    for need in needs:
        terms = HELP_SYNONYMS.get(need, [need.lower()])
        if any(term.lower() in haystack for term in terms):
            hits.append(need)
    return hits

def score_profile(analysis, p):
    country_pts, country_hits = list_overlap_score(analysis.get("countries", []), p.get("countries", []), 30)
    industry_pts, industry_hits = list_overlap_score(analysis.get("industries", []), p.get("industries", []), 25)

    need_hits = semantic_help_hits(analysis.get("needs", []), p)
    needs = analysis.get("needs", [])
    coverage = (len(set(need_hits)) / len(set(needs))) if needs else 0
    expertise_pts = round(25 * coverage)
    help_pts = round(15 * coverage)

    availability = p.get("availability", "Low")
    availability_pts = {"High": 5, "Medium": 3, "Low": 0}.get(availability, 0)

    score = min(100, country_pts + industry_pts + expertise_pts + help_pts + availability_pts)

    reasons = []
    if country_hits:
        reasons.append("Geography: " + ", ".join(x.title() for x in country_hits))
    if industry_hits:
        reasons.append("Industry fit: " + ", ".join(x.title() for x in industry_hits))
    if need_hits:
        reasons.append("Relevant help: " + ", ".join(need_hits[:3]))
    reasons.append(f"Availability: {availability}")

    breakdown = {
        "Geography": country_pts,
        "Industry": industry_pts,
        "Expertise": expertise_pts,
        "Help type": help_pts,
        "Availability": availability_pts,
    }
    return score, reasons, breakdown

def rank_profiles(analysis):
    ranked = []
    for p in PROFILES:
        score, reasons, breakdown = score_profile(analysis, p)
        ranked.append({**p, "match_score": score, "reasons": reasons, "breakdown": breakdown})
    ranked.sort(key=lambda x: (x["match_score"], x["availability"] == "High"), reverse=True)
    return ranked[:3]

def recommended_action(analysis, top):
    p = top[0]
    if "Customer introductions" in analysis.get("needs", []):
        return (
            f"Start with a 30-minute working session with {p['name']} to validate the commercial approach "
            "before requesting introductions."
        )
    return (
        f"Start with a focused 30-minute session with {p['name']} around "
        f"{', '.join(analysis.get('needs', [])[:2]).lower()}."
    )

def deterministic_intro(company, request, top_profile):
    expertise = ", ".join(top_profile["expertise"][:2])
    return f"""Subject: Introduction — {company} × {top_profile['name']}

Hi {top_profile['name'].split()[0]},

I’m reaching out regarding {company}, a portfolio company we are supporting.

Their current priority is:
“{request}”

Given your experience in {expertise}, I thought your perspective could be particularly valuable.

Would you be open to a short 30-minute conversation with the team?

Best,
Family Ventures
"""

def llm_intro(company, request, profile, api_key):
    if OpenAI is None:
        return deterministic_intro(company, request, profile)

    client = OpenAI(api_key=api_key)
    facts = {
        "name": profile["name"],
        "role": profile["role"],
        "countries": profile["countries"],
        "industries": profile["industries"],
        "expertise": profile["expertise"],
        "can_help_with": profile["can_help_with"],
    }
    prompt = f"""
Draft a concise, warm professional introduction email from Family Ventures.

Portfolio company: {company}
Founder request: {request}
Network member facts: {json.dumps(facts, ensure_ascii=False)}

Constraints:
- Do not invent any fact not present above.
- Explain in one sentence why this person is relevant.
- Ask for a 30-minute conversation.
- Keep it under 130 words.
- Output only the email.
"""
    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )
    return response.output_text.strip()

# ----------------------------
# UI
# ----------------------------
st.set_page_config(page_title="FV Network Copilot", page_icon="⚡", layout="wide")

st.markdown("""
<style>
.block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem;}
.kicker {font-size: .78rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase;}
.ai-badge {display:inline-block; padding:6px 10px; border:1px solid rgba(128,128,128,.35);
border-radius:999px; font-size:.82rem; margin-bottom:8px;}
div[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.22); padding: 14px; border-radius: 14px;}
</style>
""", unsafe_allow_html=True)

# API key is loaded from Streamlit Secrets in production.
# Never store the secret in GitHub.
try:
    api_key = st.secrets.get("OPENAI_API_KEY", "")
except Exception:
    api_key = ""

ai_enabled = bool(api_key)

with st.sidebar:
    st.header("AI mode")
    if ai_enabled:
        st.success("LLM enabled")
        st.caption("API key loaded securely from Streamlit Secrets.")
    else:
        st.info("Fallback mode: local rules")
        st.caption("Add OPENAI_API_KEY in Streamlit Secrets to enable the LLM.")

    st.divider()
    st.header("Demo scenarios")
    scenario_labels = [f"{s['company']} — {s['sector']}" for s in SCENARIOS]
    selected = st.selectbox("Load an example", ["Custom request"] + scenario_labels)
    st.divider()
    st.caption("All network profiles in this prototype are fictional and synthetic.")

default_company = "ForgeAI"
default_request = "We want to enter Germany and sign our first three large industrial customers within six months."

if selected != "Custom request":
    idx = scenario_labels.index(selected)
    scenario = SCENARIOS[idx]
    default_company = scenario["company"]
    default_request = scenario["request"]

st.markdown('<div class="kicker">Family Ventures — AI Agent Challenge</div>', unsafe_allow_html=True)
st.title("FV Network Copilot")
st.caption("Turn founder needs into concrete support and the right network activation.")

if ai_enabled:
    st.markdown('<span class="ai-badge">● AI understanding enabled · GPT-5.6 Luna</span>', unsafe_allow_html=True)
else:
    st.markdown('<span class="ai-badge">○ Local fallback · no external AI call</span>', unsafe_allow_html=True)

col_a, col_b = st.columns([1, 2])
with col_a:
    company = st.text_input("Company", value=default_company)
with col_b:
    request = st.text_area("How can Family Ventures help?", value=default_request, height=120)

analyze = st.button("Analyze request", type="primary", use_container_width=True)

if analyze:
    try:
        with st.spinner("Understanding the founder need..."):
            if ai_enabled:
                analysis = llm_extract(request, api_key)
                mode = "LLM"
            else:
                analysis = fallback_extract(request)
                mode = "Fallback"

            ranked = rank_profiles(analysis)

            st.session_state["analysis"] = analysis
            st.session_state["ranked"] = ranked
            st.session_state["request"] = request
            st.session_state["company"] = company
            st.session_state["analysis_mode"] = mode
            st.session_state.pop("intro", None)
    except Exception as e:
        st.error("AI analysis failed. Check the API key / API access, or remove the key to use fallback mode.")
        st.caption(str(e))

if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]
    ranked = st.session_state["ranked"]

    st.divider()
    st.caption(f"Analysis mode: {st.session_state.get('analysis_mode', 'Unknown')}")

    st.subheader("1. Need analysis")
    c1, c2, c3 = st.columns(3)
    c1.metric("Objective", analysis.get("objective", "—"))
    c2.metric("Geography", ", ".join(analysis.get("countries", [])) or "Not specified")
    c3.metric("Industry", ", ".join(analysis.get("industries", [])) or "Not specified")

    st.markdown("**Needs detected**")
    st.write(" · ".join(analysis.get("needs", [])))

    if analysis.get("assumptions"):
        with st.expander("Assumptions / missing information"):
            for item in analysis["assumptions"]:
                st.write("•", item)

    st.subheader("2. Recommended support plan")
    for i, item in enumerate(analysis.get("support_plan", []), start=1):
        st.write(f"**{i}.** {item}")

    if analysis.get("success_metric"):
        st.markdown("**Suggested success metric**")
        st.write(analysis["success_metric"])

    st.subheader("3. Best network matches")
    cols = st.columns(3)
    for col, p in zip(cols, ranked):
        with col:
            st.markdown(f"### {p['name']}")
            st.caption(p["role"])
            st.metric("Match", f"{p['match_score']} / 100")
            for reason in p["reasons"]:
                st.write("✓", reason)
            with st.expander("Why this score?"):
                for label, pts in p["breakdown"].items():
                    st.write(f"{label}: **{pts} pts**")
                st.caption("Ranking is deterministic — the LLM does not choose the winner.")

    st.subheader("4. Recommended next action")
    st.info(recommended_action(analysis, ranked))

    st.subheader("5. Draft introduction")
    if st.button("Generate introduction"):
        try:
            with st.spinner("Drafting the introduction..."):
                if ai_enabled:
                    intro = llm_intro(
                        st.session_state["company"],
                        st.session_state["request"],
                        ranked[0],
                        api_key
                    )
                else:
                    intro = deterministic_intro(
                        st.session_state["company"],
                        st.session_state["request"],
                        ranked[0]
                    )
                st.session_state["intro"] = intro
        except Exception as e:
            st.error("Could not generate the AI draft. Falling back to the local template.")
            st.session_state["intro"] = deterministic_intro(
                st.session_state["company"],
                st.session_state["request"],
                ranked[0]
            )

    if "intro" in st.session_state:
        st.text_area("Draft — human validation required", st.session_state["intro"], height=240)
        st.caption("The agent recommends and drafts. A Family Ventures team member validates before any outreach.")

    with st.expander("How the prototype works"):
        st.markdown("""
**LLM layer**
- Understands free-form founder requests
- Converts them into structured needs
- Suggests a support plan
- Drafts the introduction

**Deterministic layer**
- Scores network members using stored profile facts
- Geography: 30 points
- Industry: 25 points
- Expertise: 25 points
- Help type: 15 points
- Availability: 5 points

**Safeguard**
- The LLM does not choose who gets contacted
- The system does not send anything automatically
- A human validates the final introduction
""")
