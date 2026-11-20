# Simpl.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Secrets
Create `.streamlit/secrets.toml` locally:
```toml
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_MODEL = "gpt-4o-mini"
```
Never commit `.streamlit/secrets.toml` to GitHub. The `.gitignore` excludes it.

For Streamlit Community Cloud, add the same TOML values in your app's Settings → Secrets.

## Current features
- Google News RSS discovery, with optional NewsAPI and Guardian sources.
- Best-effort extraction of publicly accessible article text using Trafilatura.
- OpenAI-generated 5–8 fact bullets when the available source supports them, plus separately labelled insight and potential impact.
- OpenAI connection test in the Profile page.
- Inter typography and Source Serif 4 editorial headlines.

Article extraction cannot bypass paywalls or publisher restrictions. If only a headline/excerpt is available, Simpl instructs the model to disclose that limitation rather than invent details.
