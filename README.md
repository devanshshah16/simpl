# Simpl.

A Streamlit prototype for a source-linked, swipe-style global news briefing app.

## What is included

- Editorial interface inspired by the supplied Simpl references: white/soft-grey canvas, deep green accent, restrained blue-grey metadata, DM Sans UI typography and serif editorial headlines.
- Discover, Explore, Saved and Profile views.
- GDELT DOC 2.0 integration (no API key).
- RSS integrations: BBC World, BBC Business, NPR World and NASA.
- Optional NewsAPI and The Guardian Open Platform integrations.
- Optional OpenAI-powered source-grounded summary, interpretation and potential-impact fields.
- Source links, image attribution where available, category tagging, simple deduplication and user preferences.

## Important scope and limitations

There is no single API that provides every news publisher worldwide. This app uses multiple providers and is designed so more providers can be added. Provider availability, geographic coverage, rate limits, redistribution rights and commercial licensing vary.

The app does **not** bypass paywalls or scrape protected article text. Many providers return only headlines, descriptions or truncated excerpts. The AI is instructed to use only the text returned by the provider and to disclose when that is insufficient. For a production product, negotiate publisher/content and image licences, add a robust story-clustering pipeline, persistent database, background workers, moderation and editorial review.

The current app is a single-process MVP. Saved stories and preferences live in Streamlit session state and will not persist across devices or sessions. Add Supabase/Postgres and authentication before public multi-user launch.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Configure API keys

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and add your keys.

```toml
NEWSAPI_KEY = "..."
GUARDIAN_API_KEY = "..."
OPENAI_API_KEY = "..."
OPENAI_MODEL = "gpt-4o-mini"
```

GDELT and the listed RSS feeds work without keys. The app still runs if optional keys are absent.

- NewsAPI: https://newsapi.org/
- The Guardian Open Platform: https://open-platform.theguardian.com/
- OpenAI API: https://platform.openai.com/

Never commit `.streamlit/secrets.toml` or API keys to GitHub.

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository and upload `app.py`, `requirements.txt`, and this README.
2. In Streamlit Community Cloud, create an app and select `app.py` as the entry point.
3. Add API credentials under the app's **Settings → Secrets** (TOML format).
4. Deploy.

See Streamlit's official deployment and secrets documentation:
- https://docs.streamlit.io/deploy
- https://docs.streamlit.io/deploy/concepts/secrets

## Suggested production roadmap

1. Add Supabase Auth and Postgres for accounts, preferences, bookmarks and reading history.
2. Move ingestion and AI processing into background workers/queues; don't run large ingestion tasks in a user request.
3. Persist raw article metadata and story clusters, with provenance for every generated statement.
4. Add publisher/image licensing records and enforce usage permissions.
5. Add multi-source corroboration, duplicate/event clustering and editorial review for low-confidence stories.
6. Add caching, observability, API budget controls, abuse protection and automated tests.
7. Add a mobile-native interaction layer or custom Streamlit components if you need true touch-first swipe gestures.

## Data integrity design

The card separates:
- **Source reporting**: factual summary based on the supplied provider excerpt.
- **AI insight**: interpretation, explicitly labelled.
- **Possible impact**: conditional implications, not a claim of certainty.

The 60-word target is enforced in the AI instruction prompt, but provider excerpts may be too short to support useful analysis. Always check the original publisher article.
