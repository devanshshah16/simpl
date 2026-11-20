# Simpl.

A Streamlit news briefing app using Google News RSS as its primary discovery connection, with optional NewsAPI and The Guardian integrations and OpenAI-generated source-grounded analysis.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
streamlit run app.py
```

## Configure API credentials

Create `.streamlit/secrets.toml` locally:

```toml
OPENAI_API_KEY = "your-openai-api-key"
OPENAI_MODEL = "gpt-4o-mini"
# Optional:
NEWSAPI_KEY = ""
GUARDIAN_API_KEY = ""
```

**Never commit `.streamlit/secrets.toml` or API keys to GitHub.** The `.gitignore` file excludes the real secrets file.

## Deploy on Streamlit Community Cloud

1. Push `app.py`, `requirements.txt`, `.gitignore`, and optionally this README to GitHub.
2. Create an app in Streamlit Community Cloud and select `app.py`.
3. In the deployed app's Settings → Secrets, add the TOML credentials shown above.
4. Deploy or reboot the app.

## Notes

- Google News RSS is the primary news discovery source and requires no API key.
- OpenAI API access is billed separately from a ChatGPT subscription.
- News feeds may provide only titles and short excerpts; the AI is instructed not to invent facts or numbers and to disclose when source text is insufficient.
- Provider content, images, rate limits and redistribution rights vary. This app links readers to publishers and does not bypass paywalls.
- User preferences and saved stories are currently held in Streamlit session state; persistent multi-user storage requires a database and authentication.
