
import json
import re
from pathlib import Path

import streamlit as st

try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ============================================================
# CONFIG & DATA
# ============================================================

BASE_DIR = Path(__file__).parent
MODEL_NAME = "gpt-5.6-luna"

with open(BASE_DIR / "network_profiles.json", encoding="utf-8") as f:
    PROFILES = json.load(f)

with open(BASE_DIR / "startup_scenarios.json", encoding="utf-8") as f:
    SCENARIOS = json.load(f)

try:
    API_KEY = st.secrets.get("OPENAI_API_KEY", "")
except Exception:
    API_KEY = ""

AI_ENABLED = bool(API_KEY and OpenAI is not None)


# ============================================================
# FALLBACK UNDERSTANDING
# ============================================================

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
    "israel": "Israel",
    "poland": "Poland", "pologne": "Poland",
    "switzerland": "Switzerland", "suisse": "Switzerland",
}

INDUSTRY_KEYWORDS = {
    "industrial": "Industrial Technology", "industrie": "Industrial Technology",
    "manufacturing": "Manufacturing", "factory": "Manufacturing",
    "automotive": "Automotive", "automobile": "Automotive",
    "energy": "Energy", "énergie": "Energy",
    "climate": "Climate", "climat": "Climate",
    "ai": "AI", "ia": "AI",
    "software": "Enterprise Software", "saas": "Enterprise Software",
    "cyber": "Cybersecurity", "cybersecurity": "Cybersecurity",
    "robotics": "Robotics", "robotique": "Robotics",
    "health": "Health", "santé": "Health",
    "longevity": "Longevity", "longévité": "Longevity",
    "retail": "Retail",
    "logistics": "Logistics", "logistique": "Logistics",
    "defense": "Defense", "défense": "Defense",
}

NEED_RULES = {
    "Market entry": [
        "enter", "launch", "expand", "market entry", "go into",
        "entrer", "lancer", "développer", "expansion"
    ],
    "Enterprise sales": [
        "enterprise", "large customer", "large customers", "industrial customers",
        "grand compte", "grands comptes", "sign our first", "sign clients",
        "sales", "sell to"
    ],
    "Customer introductions": [
        "introduction", "introductions", "clients", "customers",
        "prospects", "contacts", "buyers"
    ],
    "GTM strategy": [
        "gtm", "go-to-market", "go to market", "market strategy",
        "market entry", "enter germany", "enter france", "enter the", "expansion"
    ],
    "Recruitment": ["hire", "hiring", "recruit", "recrut", "vp sales", "talent"],
    "Strategic partnerships": ["partner", "partnership", "partners", "partenaire", "partenariat"],
    "Fundraising": ["fundraising", "raise", "levée", "investor", "investisseur"],
    "Regulation": ["regulation", "regulatory", "réglement", "compliance"],
    "Industrial pilots": ["pilot", "pilots", "pilote", "proof of concept", "poc"],
    "Pricing": ["pricing", "price", "tarif", "prix"],
}


# ============================================================
# MATCHING TAXONOMY
# ============================================================

INDUSTRY_FAMILIES = {
    "industrial": {
        "Industrial Technology", "Manufacturing", "Automotive", "Robotics",
        "Physical AI", "Chemicals", "Logistics"
    },
    "digital": {
        "AI", "Enterprise Software", "Cybersecurity", "Fintech",
        "Consumer Technology", "Technology"
    },
    "energy_climate": {
        "Energy", "Climate", "Infrastructure"
    },
    "health_longevity": {
        "Health", "Longevity", "Digital Health"
    },
    "consumer_retail": {
        "Consumer", "Retail", "Luxury"
    },
    "defense": {
        "Defense", "Cybersecurity"
    },
}

HELP_SYNONYMS = {
    "Market entry": ["market entry", "gtm", "expansion", "german gtm", "uk gtm", "us gtm"],
    "Enterprise sales": [
        "enterprise sales", "commercial strategy", "sales strategy",
        "sales playbook", "b2b sales", "automotive sales", "public sector sales"
    ],
    "Customer introductions": [
        "customer introductions", "introductions", "pilot customers",
        "oem introductions", "hospital introductions", "industrial introductions",
        "buyer introductions", "commercial introductions"
    ],
    "GTM strategy": ["gtm", "market entry", "launch strategy", "sales playbook", "growth strategy"],
    "Recruitment": ["hiring", "recruitment", "executive search", "vp hiring", "sales hiring"],
    "Strategic partnerships": ["partnership", "partner", "ecosystem", "commercial partnerships"],
    "Fundraising": ["fundraising", "investor introductions", "fundraising readiness"],
    "Regulation": ["regulation", "regulatory"],
    "Industrial pilots": ["pilot", "pilots", "pilot customers", "pilot design"],
    "Pricing": ["pricing"],
}


# ============================================================
# HELPERS
# ============================================================

def normalise(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def fallback_support_plan(analysis):
    countries = analysis.get("countries", [])
    needs = analysis.get("needs", [])
    plan = []

    if "Market entry" in needs:
        market = countries[0] if countries else "the target market"
        plan.append(f"Validate the go-to-market assumptions and ICP for {market}.")
    if "Enterprise sales" in needs:
        plan.append("Pressure-test the enterprise sales motion, buyer journey and target-account list.")
    if "Customer introductions" in needs:
        plan.append("Identify the smallest set of high-value warm introductions after the ICP is validated.")
    if "Strategic partnerships" in needs:
        plan.append("Map priority strategic partners and identify warm paths through the network.")
    if "Recruitment" in needs:
        plan.append("Define the role scorecard and mobilise operators who can benchmark or refer candidates.")
    if "Fundraising" in needs:
        plan.append("Review fundraising readiness, narrative and relevant investor introductions.")
    if "Regulation" in needs:
        plan.append("Validate the key regulatory questions with a relevant operator or domain expert.")
    if "Industrial pilots" in needs:
        plan.append("Define the pilot value proposition and shortlist 3–5 potential industrial pilot customers.")
    if "Pricing" in needs:
        plan.append("Benchmark pricing assumptions with operators who know the target customer.")

    generic = [
        "Clarify the founder's highest-priority bottleneck and desired measurable outcome.",
        "Activate only the most relevant operators first, then expand the network if needed.",
    ]
    for item in generic:
        if len(plan) < 4:
            plan.append(item)

    return plan[:4]


def fallback_extract(request):
    t = normalise(request)

    countries = []
    for keyword, value in COUNTRY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", t) and value not in countries:
            countries.append(value)

    industries = []
    for keyword, value in INDUSTRY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(keyword)}\b", t) and value not in industries:
            industries.append(value)

    needs = []
    for need, keywords in NEED_RULES.items():
        if any(keyword in t for keyword in keywords):
            needs.append(need)

    if not needs:
        needs = ["Strategic support"]

    if "Market entry" in needs:
        objective = "International market expansion"
    elif "Recruitment" in needs:
        objective = "Scale the leadership team"
    elif "Fundraising" in needs:
        objective = "Prepare the next fundraising round"
    elif "Industrial pilots" in needs:
        objective = "Secure industrial pilot customers"
    else:
        objective = "Resolve the founder's priority bottleneck"

    if not industries and any(
        signal in t
        for signal in [
            "industrial customer", "industrial customers",
            "industrial client", "industrial clients",
            "factory", "factories", "manufacturer", "manufacturers"
        ]
    ):
        industries = ["Industrial Technology"]

    analysis = {
        "objective": objective,
        "countries": countries,
        "industries": industries,
        "needs": needs,
        "success_metric": "Agree one measurable business outcome with the founder.",
        "assumptions": ["Fallback analysis based only on the request text."],
    }
    analysis["support_plan"] = fallback_support_plan(analysis)
    return analysis


def clean_json_text(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def llm_extract(request, api_key):
    client = OpenAI(api_key=api_key)

    instructions = """
You are the intake intelligence layer of FV Network Copilot, a prototype designed for Family Ventures.

Family Ventures creates value by mobilising a network of entrepreneurial families, operators and sector experts
to support founders. Your role is to understand a founder request. You do NOT select network members:
a deterministic, explainable matching engine does that later.

Return ONLY valid JSON, no markdown.

Schema:
{
  "objective": "short, concrete business objective",
  "countries": ["Country"],
  "industries": ["Industry"],
  "needs": ["Need"],
  "support_plan": ["Action 1", "Action 2", "Action 3", "Action 4"],
  "success_metric": "one measurable outcome",
  "assumptions": ["missing information or direct assumption"]
}

Allowed needs:
Market entry
Enterprise sales
Customer introductions
GTM strategy
Recruitment
Strategic partnerships
Fundraising
Regulation
Industrial pilots
Pricing
Strategic support

Preferred industry labels:
Industrial Technology
Manufacturing
Automotive
Energy
Climate
AI
Enterprise Software
Cybersecurity
Robotics
Health
Longevity
Retail
Logistics
Defense

Industry interpretation rule:
- "industries" should capture the relevant operating or target-customer sector for network matching.
- If the founder explicitly says "industrial customers", "industrial clients", factories, manufacturers,
  industrial groups or similar wording, do NOT leave industries empty.
- In that case use "Industrial Technology" unless a more specific label such as Manufacturing,
  Automotive, Energy, Robotics or Logistics is directly supported by the request.

Rules:
- Use only information supported by the founder request.
- You may infer a direct business implication, but make uncertainty explicit in assumptions.
- Do not invent traction, customers, contacts, budgets, company facts or deadlines.
- Make the support plan practical for an investor/operator network.
- Prefer diagnosis and preparation before introductions when the ICP or target is unclear.
- The success metric must be concrete and tied to the request.
"""
    response = client.responses.create(
        model=MODEL_NAME,
        instructions=instructions,
        input=request,
    )

    data = json.loads(clean_json_text(response.output_text))
    data.setdefault("objective", "Founder support")
    data.setdefault("countries", [])
    data.setdefault("industries", [])
    data.setdefault("needs", ["Strategic support"])
    data.setdefault("support_plan", [])
    data.setdefault("success_metric", "Agree one measurable business outcome with the founder.")
    data.setdefault("assumptions", [])

    # Guardrail for network matching: capture an explicit industrial target sector
    # even if the model focuses on the founder's company rather than the buyer.
    request_lower = request.lower()
    industrial_signals = [
        "industrial customer", "industrial customers",
        "industrial client", "industrial clients",
        "manufacturing customer", "manufacturing customers",
        "factory", "factories", "manufacturer", "manufacturers"
    ]
    if not data["industries"] and any(signal in request_lower for signal in industrial_signals):
        data["industries"] = ["Industrial Technology"]

    return data


def same_industry_family(request_industry, profile_industry):
    if request_industry.lower() == profile_industry.lower():
        return True

    for family in INDUSTRY_FAMILIES.values():
        if request_industry in family and profile_industry in family:
            return True

    return False


def industry_score(requested, profile_values, max_points=25):
    """
    Exact industry matches receive full credit.
    Related industries from the same family receive partial credit.
    This keeps the ranking intuitive: adjacent expertise helps, but should not
    outrank a profile with a direct sector match.
    """
    if not requested:
        return 0, []

    total_credit = 0.0
    explanations = []

    for req in requested:
        best_credit = 0.0
        best_label = None

        for profile_industry in profile_values:
            if req.lower() == profile_industry.lower():
                best_credit = 1.0
                best_label = profile_industry
                break

            if same_industry_family(req, profile_industry) and best_credit < 0.55:
                best_credit = 0.55
                best_label = profile_industry

        total_credit += best_credit

        if best_label and best_label not in explanations:
            explanations.append(best_label)

    coverage = total_credit / len(requested)
    return round(max_points * coverage), explanations


def geography_score(requested, profile_values, max_points=30):
    if not requested:
        return 0, []

    req_lower = {x.lower(): x for x in requested}
    profile_lower = {x.lower(): x for x in profile_values}
    hits = [req_lower[k] for k in req_lower.keys() & profile_lower.keys()]

    if not hits:
        return 0, []

    coverage = len(hits) / len(requested)
    return round(max_points * coverage), hits


def help_hits(needs, profile):
    haystack = " | ".join(
        profile.get("expertise", []) + profile.get("can_help_with", [])
    ).lower()

    hits = []
    for need in needs:
        terms = HELP_SYNONYMS.get(need, [need.lower()])
        if any(term.lower() in haystack for term in terms):
            hits.append(need)

    return list(dict.fromkeys(hits))


def score_profile(analysis, profile):
    countries = analysis.get("countries", [])
    industries = analysis.get("industries", [])
    needs = analysis.get("needs", [])

    geo_pts, geo_hits = geography_score(countries, profile.get("countries", []), 30)
    industry_pts, industry_hits = industry_score(industries, profile.get("industries", []), 25)

    matched_needs = help_hits(needs, profile)
    coverage = (len(set(matched_needs)) / len(set(needs))) if needs else 0

    expertise_pts = round(25 * coverage)
    help_pts = round(15 * coverage)

    availability = profile.get("availability", "Low")
    availability_pts = {"High": 5, "Medium": 3, "Low": 0}.get(availability, 0)

    # Small role-fit adjustment: for commercial expansion requests, reward direct
    # enterprise-sales / market-entry capability and avoid over-rewarding adjacent
    # industrial profiles whose main strength is pilots or product feedback.
    role_adjustment = 0
    haystack = " | ".join(
        profile.get("expertise", []) + profile.get("can_help_with", [])
    ).lower()

    commercial_request = any(
        need in needs
        for need in ["Market entry", "Enterprise sales", "Customer introductions", "GTM strategy"]
    )

    if commercial_request:
        if any(term in haystack for term in ["enterprise sales", "market entry", "german gtm", "sales strategy"]):
            role_adjustment += 4
        if "procurement" in haystack or "buyer" in haystack:
            role_adjustment += 2
        if "pilot design" in haystack and "enterprise sales" not in haystack:
            role_adjustment -= 4

    score = min(
        100,
        max(
            0,
            geo_pts + industry_pts + expertise_pts + help_pts + availability_pts + role_adjustment
        )
    )

    reasons = []
    if geo_hits:
        reasons.append("Direct geography fit: " + ", ".join(geo_hits))
    if industry_hits:
        reasons.append("Relevant sector background: " + ", ".join(industry_hits[:2]))
    if matched_needs:
        reasons.append("Can help with: " + ", ".join(matched_needs[:3]))
    reasons.append(f"Availability: {availability}")

    breakdown = {
        "Geography": geo_pts,
        "Industry": industry_pts,
        "Expertise coverage": expertise_pts,
        "Help type": help_pts,
        "Availability": availability_pts,
        "Role fit adjustment": role_adjustment,
    }

    return score, reasons, breakdown, matched_needs


def rank_profiles(analysis):
    ranked = []
    for profile in PROFILES:
        score, reasons, breakdown, matched_needs = score_profile(analysis, profile)
        ranked.append({
            **profile,
            "match_score": score,
            "reasons": reasons,
            "breakdown": breakdown,
            "matched_needs": matched_needs,
        })

    availability_rank = {"High": 2, "Medium": 1, "Low": 0}
    ranked.sort(
        key=lambda p: (
            p["match_score"],
            len(p["matched_needs"]),
            availability_rank.get(p.get("availability", "Low"), 0),
        ),
        reverse=True,
    )
    return ranked[:3]


def recommended_action(analysis, ranked):
    top = ranked[0]

    if "Customer introductions" in analysis.get("needs", []):
        return (
            f"Start with a 30-minute working session with {top['name']} to validate the target "
            "customer and commercial approach. Only then activate introductions."
        )

    need_text = ", ".join(analysis.get("needs", [])[:2]).lower()
    return f"Start with a focused 30-minute working session with {top['name']} around {need_text}."


def deterministic_intro(company, request, profile):
    relevant = ", ".join(profile.get("expertise", [])[:2])
    first_name = profile["name"].split()[0]

    return f"""Subject: {company} × {profile['name']} — quick introduction

Hi {first_name},

I’m reaching out regarding {company}, a portfolio company we are supporting.

Their current priority is:
“{request}”

Given your experience in {relevant}, I thought your perspective could be particularly useful before we activate any further introductions.

Would you be open to a focused 30-minute conversation with the team?

Best,
Family Ventures"""


def llm_intro(company, request, profile, api_key):
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
- Do not invent anything not in the facts.
- Explain in one sentence why this person is relevant.
- Position the first interaction as a focused working session to challenge the founder's approach.
- Do not promise or request customer introductions in the first email unless the request explicitly depends on them.
- Ask for a focused 30-minute conversation.
- Keep it under 120 words.
- Output only the email.
"""
    response = client.responses.create(model=MODEL_NAME, input=prompt)
    return response.output_text.strip()


def safe_analyze(request):
    if AI_ENABLED:
        try:
            return llm_extract(request, API_KEY), "LLM"
        except Exception:
            analysis = fallback_extract(request)
            return analysis, "Local fallback"

    return fallback_extract(request), "Local fallback"


def safe_intro(company, request, profile):
    if AI_ENABLED:
        try:
            return llm_intro(company, request, profile, API_KEY), "LLM"
        except Exception:
            pass

    return deterministic_intro(company, request, profile), "Local template"


# ============================================================
# UI
# ============================================================

st.set_page_config(
    page_title="FV Network Copilot",
    page_icon="⚡",
    layout="wide",
)

st.markdown("""
<style>
.block-container {
    max-width: 1180px;
    padding-top: 2.2rem;
    padding-bottom: 5rem;
}
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.kicker {
    font-size: .76rem;
    font-weight: 700;
    letter-spacing: .13em;
    text-transform: uppercase;
    opacity: .65;
}
.hero-subtitle {
    font-size: 1.03rem;
    opacity: .72;
    margin-top: -.5rem;
    margin-bottom: 1.2rem;
}
.pill {
    display: inline-block;
    border: 1px solid rgba(128,128,128,.35);
    border-radius: 999px;
    padding: 5px 10px;
    margin: 0 5px 5px 0;
    font-size: .82rem;
}
.status-good {
    display: inline-block;
    border-radius: 999px;
    padding: 5px 10px;
    background: rgba(35, 134, 54, .12);
    font-size: .82rem;
}
.status-safe {
    display: inline-block;
    border-radius: 999px;
    padding: 5px 10px;
    background: rgba(128, 128, 128, .12);
    font-size: .82rem;
}
.member-card {
    border: 1px solid rgba(128,128,128,.22);
    border-radius: 16px;
    padding: 18px;
    min-height: 360px;
}
.score {
    font-size: 2rem;
    font-weight: 750;
    margin: .4rem 0 .2rem 0;
}
.muted {
    opacity: .67;
    font-size: .91rem;
}
.human-box {
    border: 1px solid rgba(128,128,128,.24);
    border-radius: 14px;
    padding: 13px 15px;
    margin-top: .5rem;
}
div[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.20);
    padding: 14px;
    border-radius: 14px;
}
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### FV Network Copilot")
    st.caption("Interview prototype · v3.2")

    if AI_ENABLED:
        st.success("AI layer connected")
    else:
        st.info("Local fallback active")

    st.caption("The app automatically falls back to local logic if the API is unavailable.")

    st.divider()
    st.markdown("### Demo scenarios")

    scenario_labels = [f"{s['company']} — {s['sector']}" for s in SCENARIOS]
    selected = st.selectbox("Load an example", ["Custom request"] + scenario_labels)

    st.divider()
    st.caption(
        "Prototype data only. All network members and demo companies are fictional / synthetic."
    )

# Defaults
default_company = "ForgeAI"
default_request = (
    "We want to enter Germany and sign our first three large industrial customers within six months."
)

if selected != "Custom request":
    idx = scenario_labels.index(selected)
    scenario = SCENARIOS[idx]
    default_company = scenario["company"]
    default_request = scenario["request"]

# Hero
st.markdown('<div class="kicker">Family Ventures · AI Agent Challenge</div>', unsafe_allow_html=True)
st.title("FV Network Copilot")
st.markdown(
    '<div class="hero-subtitle">'
    'From a founder request to an actionable support plan and the right network activation.'
    '</div>',
    unsafe_allow_html=True
)

badge_col1, badge_col2, badge_col3 = st.columns([1.25, 1.15, 4])
with badge_col1:
    mode_label = "AI understanding" if AI_ENABLED else "Local understanding"
    st.markdown(f'<span class="status-good">● {mode_label}</span>', unsafe_allow_html=True)
with badge_col2:
    st.markdown('<span class="status-safe">Human approval required</span>', unsafe_allow_html=True)

# Input
st.markdown("### Founder request")
input_col1, input_col2 = st.columns([1, 2.2])

with input_col1:
    company = st.text_input("Company", value=default_company)

with input_col2:
    request = st.text_area(
        "How can Family Ventures help?",
        value=default_request,
        height=120,
        placeholder="Describe the founder's current priority, target market and desired outcome..."
    )

if st.button("Analyze & activate network", type="primary", use_container_width=True):
    with st.spinner("Understanding the need and mapping the network..."):
        analysis, mode = safe_analyze(request)
        ranked = rank_profiles(analysis)

        st.session_state["analysis"] = analysis
        st.session_state["ranked"] = ranked
        st.session_state["request"] = request
        st.session_state["company"] = company
        st.session_state["analysis_mode"] = mode
        st.session_state.pop("intro", None)
        st.session_state.pop("intro_mode", None)

# Results
if "analysis" in st.session_state:
    analysis = st.session_state["analysis"]
    ranked = st.session_state["ranked"]
    mode = st.session_state.get("analysis_mode", "Local fallback")

    st.divider()

    if mode == "LLM":
        st.caption("Understanding layer: LLM · Matching layer: deterministic scoring")
    else:
        st.warning(
            "AI API unavailable or disabled — the prototype continued automatically using its local fallback."
        )

    # 1 Need analysis
    st.markdown("## 1. Need analysis")

    objective = analysis.get("objective", "—")
    geography = ", ".join(analysis.get("countries", [])) or "Not specified"
    industry = ", ".join(analysis.get("industries", [])) or "Not specified"

    m1, m2, m3 = st.columns(3)

    for col, label, value in [
        (m1, "Objective", objective),
        (m2, "Geography", geography),
        (m3, "Industry", industry),
    ]:
        with col:
            st.markdown(
                f"""
                <div style="
                    border:1px solid rgba(128,128,128,.20);
                    padding:14px 16px;
                    border-radius:14px;
                    min-height:112px;">
                    <div style="font-size:.82rem; opacity:.68; margin-bottom:8px;">{label}</div>
                    <div style="font-size:1.35rem; font-weight:650; line-height:1.18;">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("**Needs detected**")
    needs_html = "".join(
        f'<span class="pill">{need}</span>' for need in analysis.get("needs", [])
    )
    st.markdown(needs_html or '<span class="muted">No explicit need detected</span>', unsafe_allow_html=True)

    if analysis.get("assumptions"):
        with st.expander("Assumptions / missing information"):
            for item in analysis["assumptions"]:
                st.write("•", item)

    # 2 Support plan
    st.markdown("## 2. Recommended support plan")

    for i, item in enumerate(analysis.get("support_plan", []), start=1):
        st.markdown(f"**{i}.** {item}")

    if analysis.get("success_metric"):
        st.info("**Suggested success metric:** " + analysis["success_metric"])

    # 3 Matches
    st.markdown("## 3. Best network matches")
    st.caption("The LLM does not select the contacts. The ranking below is deterministic and explainable.")

    cols = st.columns(3)

    for col, profile in zip(cols, ranked):
        with col:
            st.markdown(f"### {profile['name']}")
            st.caption(profile["role"])
            st.markdown(f'<div class="score">{profile["match_score"]} / 100</div>', unsafe_allow_html=True)

            st.progress(profile["match_score"] / 100)

            for reason in profile["reasons"]:
                st.write("✓", reason)

            st.markdown("**Relevant capabilities**")
            capabilities = profile.get("can_help_with", [])[:3]
            if capabilities:
                for capability in capabilities:
                    st.caption("• " + capability)

            with st.expander("Why this score?"):
                for label, points in profile["breakdown"].items():
                    st.write(f"{label}: **{points} pts**")
                st.caption(
                    "Score = geography (30) + industry (25) + expertise coverage (25) "
                    "+ help type (15) + availability (5), with a small transparent role-fit adjustment."
                )

    # 4 Action
    st.markdown("## 4. Recommended next action")
    st.success(recommended_action(analysis, ranked))

    st.markdown(
        '<div class="human-box"><strong>Human-in-the-loop</strong><br>'
        'The agent recommends who to involve and drafts the message. '
        'A Family Ventures team member decides whether an introduction should actually be made.</div>',
        unsafe_allow_html=True
    )

    # 5 Intro
    st.markdown("## 5. Draft introduction")

    top_profile = ranked[0]
    st.caption(f"Drafting an introduction to {top_profile['name']} — final human validation required.")

    if st.button("Generate introduction draft"):
        with st.spinner("Drafting the introduction..."):
            intro, intro_mode = safe_intro(
                st.session_state["company"],
                st.session_state["request"],
                top_profile,
            )
            st.session_state["intro"] = intro
            st.session_state["intro_mode"] = intro_mode

    if "intro" in st.session_state:
        st.text_area(
            "Draft",
            st.session_state["intro"],
            height=230,
        )
        st.caption(f"Draft generation: {st.session_state.get('intro_mode', 'Local template')}")

    # Method
    with st.expander("How the prototype works"):
        st.markdown("""
**1 — Understanding layer**  
A language model converts an unstructured founder request into objective, geography, industry, needs,
a support plan and a measurable success metric.

**2 — Explainable matching layer**  
Network members are ranked with deterministic scoring based only on stored profile facts:
geography, industry, expertise, type of help and availability.

**3 — Generation layer**  
The model can draft an introduction using only the selected profile's stored facts.

**4 — Human validation**  
No message is sent automatically. A Family Ventures team member remains accountable for activating the network.

**Resilience**  
If the API is unavailable, the prototype automatically continues using a local rule-based fallback.
""")
