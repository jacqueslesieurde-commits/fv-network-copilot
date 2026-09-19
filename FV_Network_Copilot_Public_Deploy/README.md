# FV Network Copilot — Public Deployment

Prototype for the Family Ventures AI Agent Challenge.

## Files to upload to GitHub
Upload:
- app.py
- requirements.txt
- network_profiles.json
- startup_scenarios.json
- matching_rules.json
- .gitignore
- README.md

Do NOT upload:
- any API key
- .streamlit/secrets.toml
- .env files

## Streamlit Cloud secret
After deploying the repository, open the app settings / secrets and add:

OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"

The app reads the key from Streamlit Secrets. Visitors never need to enter it.

## Architecture
Founder request
→ LLM structured analysis
→ deterministic / explainable matching
→ Top 3 profiles
→ recommended action
→ AI-generated draft introduction
→ human validation

All network profiles and startup examples are fictional / synthetic.
