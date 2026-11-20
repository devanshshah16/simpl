
from __future__ import annotations

import html
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import feedparser
import requests
import streamlit as st
from dateutil import parser as date_parser

# -------------------------------------------------------------------
# SIMPL — a source-linked global news briefing experience
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Simpl — A little clarity. Every day.",
    page_icon="🟢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Read secrets safely: Streamlit Cloud uses App settings > Secrets.
def secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default) or default)
    except Exception:
        return default

NEWSAPI_KEY = secret("NEWSAPI_KEY")
GUARDIAN_API_KEY = secret("GUARDIAN_API_KEY")
OPENAI_API_KEY = secret("OPENAI_API_KEY")
OPENAI_MODEL = secret("OPENAI_MODEL", "gpt-4o-mini")

COUNTRIES = {
    "United States": "US", "United Kingdom": "GB", "India": "IN",
    "Canada": "CA", "Australia": "AU", "Germany": "DE", "France": "FR",
    "Italy": "IT", "Spain": "ES", "Japan": "JP", "China": "CN",
    "Singapore": "SG", "United Arab Emirates": "AE", "Brazil": "BR",
    "South Africa": "ZA", "Mexico": "MX", "South Korea": "KR",
    "Netherlands": "NL", "Switzerland": "CH", "Ireland": "IE",
}
CATEGORIES = [
    "Technology", "Business", "Economy", "Geopolitics", "Science",
    "Climate", "Energy", "Politics", "Health", "Society", "Manufacturing",
]
CATEGORY_QUERIES = {
    "Technology": 'technology OR artificial intelligence OR software',
    "Business": 'business OR company OR corporate OR startup',
    "Economy": 'economy OR inflation OR interest rates OR trade',
    "Geopolitics": 'geopolitics OR diplomacy OR sanctions OR conflict',
    "Science": 'science OR research OR space OR discovery',
    "Climate": 'climate OR environment OR emissions',
    "Energy": 'energy OR oil OR gas OR renewables',
    "Politics": 'election OR government OR parliament OR policy',
    "Health": 'health OR medicine OR public health',
    "Society": 'society OR education OR labor OR culture',
    "Manufacturing": 'manufacturing OR industrial OR supply chain',
}
RSS_FEEDS = [
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
    ("NASA", "https://www.nasa.gov/news-release/feed/"),
]

# ---------------------------- Styling -----------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');
:root {
  --ink:#171d1a; --muted:#6d7470; --green:#087747; --pale:#e0f2e8;
  --line:#dfe4e0; --blue:#617895; --paper:#f7f8f7; --white:#ffffff;
}
html, body, [class*="css"] { font-family:'DM Sans',Arial,sans-serif; color:var(--ink); }
.stApp { background:var(--paper); }
header[data-testid="stHeader"] { background:rgba(247,248,247,.94); }
.block-container { padding-top:1.35rem; padding-bottom:3rem; max-width:1500px; }
[data-testid="stSidebar"] { background:#f7f8f7; border-right:1px solid var(--line); }
[data-testid="stSidebar"] .block-container { padding-top:1.1rem; }
.logo { font-size:2.65rem; letter-spacing:-2px; font-weight:700; line-height:1; margin:.2rem 0 2.2rem; }
.logo span { color:var(--green); }
.eyebrow { color:#707772; font-size:.77rem; letter-spacing:2px; font-weight:700; text-transform:uppercase; }
.hero-title { font-size:2.65rem; line-height:1.13; font-weight:700; letter-spacing:-1.3px; margin:0; }
.hero-sub { color:var(--muted); font-size:1.15rem; margin-top:.45rem; }
.story-card { background:white; border:1px solid #d9dfdb; border-radius:14px; overflow:hidden; box-shadow:0 10px 35px rgba(26,43,34,.055); margin:1rem 0 1.5rem; }
.story-meta { display:flex; align-items:center; gap:12px; padding:18px 26px; color:#202723; font-size:.92rem; }
.pill { display:inline-block; background:var(--pale); color:var(--green); padding:7px 13px; border-radius:7px; font-size:.82rem; font-weight:600; }
.story-image { width:100%; height:360px; object-fit:cover; display:block; background:#e9eeeb; }
.image-placeholder { height:240px; display:flex; align-items:center; justify-content:center; background:linear-gradient(130deg,#e7eee9,#dce7e1); color:#728078; font-size:1rem; }
.story-body { padding:25px 30px 20px; }
.publisher { color:var(--blue); font-size:.9rem; margin-bottom:12px; }
.story-title { font-family:'Playfair Display',Georgia,serif; font-weight:700; font-size:2.2rem; line-height:1.1; letter-spacing:-.4px; margin:0 0 15px; }
.story-summary { color:#737a75; font-size:1.12rem; line-height:1.65; }
.section-label { color:var(--green); font-size:.78rem; letter-spacing:1.8px; font-weight:700; text-transform:uppercase; margin:18px 0 7px; }
.insight-text { color:#202723; font-size:1.02rem; line-height:1.55; }
.story-footer { border-top:1px solid var(--line); padding:16px 28px; display:flex; justify-content:space-between; color:#6d7470; font-size:.9rem; }
.story-row { border-bottom:1px solid var(--line); padding:18px 0; display:flex; gap:18px; align-items:center; }
.story-thumb { width:140px; height:88px; object-fit:cover; border-radius:8px; background:#e5ebe7; }
.small-muted { color:var(--blue); font-size:.85rem; }
div.stButton > button { border-radius:9px; border:1px solid #d9e0dc; font-weight:600; }
div.stButton > button[kind="primary"] { background:var(--green); border-color:var(--green); }
div[data-testid="stSelectbox"] label, div[data-testid="stMultiSelect"] label { color:#59635d; font-size:.85rem; }
hr { border-color:var(--line); }
a { color:var(--green)!important; }
@media(max-width:800px) {
 .hero-title{font-size:2rem}.story-title{font-size:1.65rem}
 .story-image{height:230px}.story-body{padding:20px}
 .block-container{padding-left:1rem;padding-right:1rem}
}
</style>
""", unsafe_allow_html=True)

# -------------------------- Data helpers --------------------------
def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()

def parse_date(value: Any) -> datetime:
    try:
        dt = date_parser.parse(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def normalise_article(title="", description="", url="", image="", source="", published="", category="Global", country="Global"):
    return {
        "title": clean_text(title) or "Untitled story",
        "description": clean_text(description),
        "url": url or "",
        "image": image or "",
        "source": clean_text(source) or "News source",
        "published": parse_date(published),
        "category": category,
        "country": country,
    }

def request_json(url: str, params: dict, headers: dict | None = None, timeout: int = 18):
    response = requests.get(url, params=params, headers=headers or {}, timeout=timeout)
    response.raise_for_status()
    return response.json()

def fetch_gdelt(query: str, max_records: int = 35) -> list[dict]:
    """GDELT DOC 2.0: broad international news discovery; no API key."""
    data = request_json(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        {"query": query, "mode": "ArtList", "format": "json",
         "maxrecords": min(max_records, 250), "sort": "DateDesc", "timespan": "7d"},
        timeout=25,
    )
    out = []
    for item in data.get("articles", []):
        out.append(normalise_article(
            item.get("title"), item.get("title"), item.get("url"),
            item.get("socialimage"), item.get("domain") or urlparse(item.get("url","")).netloc,
            item.get("seendate"), "Global", "Global"
        ))
    return out

def fetch_newsapi(query: str, country_code: str | None = None, max_records: int = 30) -> list[dict]:
    if not NEWSAPI_KEY:
        return []
    params = {"q": query, "pageSize": min(max_records, 100), "sortBy": "publishedAt",
              "language": "en", "apiKey": NEWSAPI_KEY}
    data = request_json("https://newsapi.org/v2/everything", params, timeout=20)
    out = []
    for item in data.get("articles", []):
        out.append(normalise_article(
            item.get("title"), item.get("description") or item.get("content"),
            item.get("url"), item.get("urlToImage"),
            (item.get("source") or {}).get("name"), item.get("publishedAt")
        ))
    return out

def fetch_guardian(query: str, max_records: int = 25) -> list[dict]:
    if not GUARDIAN_API_KEY:
        return []
    data = request_json(
        "https://content.guardianapis.com/search",
        {"q": query, "api-key": GUARDIAN_API_KEY, "show-fields": "thumbnail,trailText",
         "page-size": min(max_records, 50), "order-by": "newest"},
        timeout=20,
    )
    out = []
    for item in data.get("response", {}).get("results", []):
        fields = item.get("fields", {})
        out.append(normalise_article(
            item.get("webTitle"), fields.get("trailText"), item.get("webUrl"),
            fields.get("thumbnail"), "The Guardian", item.get("webPublicationDate")
        ))
    return out

def fetch_rss(max_per_feed: int = 12) -> list[dict]:
    out = []
    for publisher, feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_per_feed]:
                out.append(normalise_article(
                    entry.get("title"), entry.get("summary"), entry.get("link"),
                    "", publisher, entry.get("published") or entry.get("updated")
                ))
        except Exception:
            continue
    return out

def deduplicate(articles: list[dict]) -> list[dict]:
    seen, result = set(), []
    for article in sorted(articles, key=lambda x: x["published"], reverse=True):
        key = re.sub(r"[^a-z0-9]", "", article["title"].lower())[:95]
        if key and key not in seen:
            seen.add(key)
            result.append(article)
    return result

def infer_category(article: dict) -> str:
    text = (article["title"] + " " + article["description"]).lower()
    for category, terms in {
        "Technology":["ai","artificial intelligence","software","chip","tech","robot"],
        "Business":["company","business","corporate","startup","earnings","merger"],
        "Economy":["inflation","interest rate","gdp","economy","central bank","trade"],
        "Geopolitics":["war","sanction","diplomacy","military","border","iran","china"],
        "Science":["research","scientist","nasa","space","study","discovery"],
        "Climate":["climate","warming","emissions","environment","carbon"],
        "Energy":["oil","gas","energy","solar","wind power","electricity"],
        "Politics":["election","president","minister","government","parliament"],
        "Health":["health","hospital","disease","drug","medical"],
        "Manufacturing":["factory","manufacturing","industrial","supply chain"],
    }.items():
        if any(term in text for term in terms):
            return category
    return "Society"

def country_matches(article: dict, selected_country: str) -> bool:
    if selected_country == "Global":
        return True
    # GDELT can constrain by sourcecountry; for other providers, use best-effort text matching.
    return selected_country.lower() in (article["title"] + " " + article["description"] + " " + article["source"]).lower()

def search_news(category: str, country: str, custom_query: str = "") -> tuple[list[dict], list[str]]:
    errors = []
    if custom_query.strip():
        query = custom_query.strip()
    elif category == "All":
        query = "world news"
    else:
        query = CATEGORY_QUERIES.get(category, category)
    if country != "Global" and not custom_query.strip():
        query = f'({query}) sourcecountry:{COUNTRIES.get(country, "US").lower()}'
    articles = []
    # GDELT is the no-key global baseline.
    try:
        articles.extend(fetch_gdelt(query))
    except Exception as exc:
        errors.append(f"GDELT: {str(exc)[:180]}")
    # Optional licensed/provider APIs.
    try:
        articles.extend(fetch_newsapi(custom_query or query))
    except Exception as exc:
        errors.append(f"NewsAPI: {str(exc)[:180]}")
    try:
        articles.extend(fetch_guardian(custom_query or query))
    except Exception as exc:
        errors.append(f"Guardian: {str(exc)[:180]}")
    if category == "All" and country == "Global" and not custom_query:
        try:
            articles.extend(fetch_rss())
        except Exception as exc:
            errors.append(f"RSS: {str(exc)[:180]}")
    articles = deduplicate(articles)
    for article in articles:
        article["category"] = infer_category(article)
    if category != "All":
        articles = [a for a in articles if a["category"] == category or category.lower() in (a["title"]+" "+a["description"]).lower()]
    if country != "Global":
        # Retain GDELT's source-country results; apply soft matching only to avoid discarding all provider results.
        matched = [a for a in articles if country_matches(a, country)]
        if matched:
            articles = matched
    return articles[:60], errors

def ai_interpret(article: dict) -> dict:
    """Only generate AI interpretation from text supplied by retrieved source metadata."""
    if not OPENAI_API_KEY:
        return {
            "summary": article["description"] or "Open the original reporting for the full article. The available feed metadata does not include enough text for a reliable factual summary.",
            "insight": "AI interpretation is not enabled. Add OPENAI_API_KEY in Streamlit secrets to generate a source-grounded perspective.",
            "impact": "Potential effects are not generated until the source text can be assessed.",
            "status": "AI disabled",
        }
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    prompt = f"""
You are the editorial analyst for Simpl, a concise global news intelligence product.
Use ONLY the article metadata/text below. Do not add outside facts or pretend to have read the full article.
If the provided text is insufficient, say so. Separate reported facts from interpretation.
Return valid JSON with keys:
summary (factual, max 32 words),
insight (interpretation, max 18 words; label it as analysis, not fact),
impact (possible consequence, max 15 words; conditional language),
confidence ("High", "Medium", or "Low"),
basis (one sentence explaining what supplied text supports this analysis).
The three display fields summary + insight + impact combined must be fewer than 60 words.
ARTICLE TITLE: {article['title']}
PUBLISHER: {article['source']}
DESCRIPTION / AVAILABLE EXCERPT: {article['description']}
URL: {article['url']}
"""
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL, temperature=0.2,
            response_format={"type": "json_object"},
            messages=[{"role":"system","content":"Be precise, neutral, and evidence-bound."},
                      {"role":"user","content":prompt}],
        )
        data = json.loads(response.choices[0].message.content)
        for key in ("summary","insight","impact"):
            data[key] = clean_text(data.get(key, ""))
        return data
    except Exception as exc:
        return {
            "summary": article["description"] or "The feed does not provide enough article text for a factual summary.",
            "insight": "AI analysis could not be generated for this story.",
            "impact": "Read the source before drawing conclusions.",
            "status": f"AI error: {str(exc)[:100]}",
        }

def time_ago(dt: datetime) -> str:
    seconds = max(0, int((datetime.now(timezone.utc) - dt).total_seconds()))
    if seconds < 3600: return f"about {max(1, seconds//60)} min ago"
    if seconds < 86400: return f"about {seconds//3600} hours ago"
    return f"about {seconds//86400} days ago"

# -------------------------- Session state -------------------------
defaults = {
    "articles": [], "errors": [], "last_fetch": None, "saved": set(),
    "active_tab": "Discover", "card_index": 0, "ai_cache": {},
    "interests": ["Technology", "Business", "Economy", "Geopolitics", "Science"],
    "country": "Global", "category": "All", "search_query": "",
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ------------------------------ Sidebar ---------------------------
with st.sidebar:
    st.markdown('<div class="logo">Simpl<span>.</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">YOUR WORLD, UNDERSTOOD</div>', unsafe_allow_html=True)
    nav = st.radio("Navigation", ["Discover", "Explore", "Saved", "Profile"], label_visibility="collapsed")
    st.session_state.active_tab = nav
    st.markdown("---")
    st.markdown('<div class="eyebrow">YOUR INTERESTS</div>', unsafe_allow_html=True)
    for interest in st.session_state.interests:
        st.markdown(f'<div style="padding:9px 0;font-weight:600">● &nbsp;{html.escape(interest)}</div>', unsafe_allow_html=True)
    with st.expander("＋ Add interests"):
        new_interests = st.multiselect("Choose topics", CATEGORIES, default=st.session_state.interests)
        if st.button("Save interests", use_container_width=True):
            st.session_state.interests = new_interests
            st.rerun()
    st.markdown("---")
    st.markdown('<div class="eyebrow">PERSPECTIVE, NOT NOISE</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#617895;line-height:2.1">Credible reporting.<br>Clearly labelled interpretation.</div>', unsafe_allow_html=True)
    st.caption("A little clarity. Every day.")

# ------------------------------ Header ----------------------------
col1, col2 = st.columns([8, 1])
with col1:
    if st.session_state.active_tab == "Discover":
        st.markdown('<div class="hero-title">A world of perspective.</div><div class="hero-sub">The stories that matter. The context you need.</div>', unsafe_allow_html=True)
    elif st.session_state.active_tab == "Explore":
        st.markdown('<div class="hero-title">Follow your curiosity.</div><div class="hero-sub">Different places. New perspectives.</div>', unsafe_allow_html=True)
    elif st.session_state.active_tab == "Saved":
        st.markdown('<div class="hero-title">Worth keeping.</div><div class="hero-sub">Your saved stories, all in one place.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="hero-title">Your perspective.</div><div class="hero-sub">Shape the world you want to understand.</div>', unsafe_allow_html=True)
with col2:
    st.write("")
    st.write("")
    if st.button("↻ Refresh", help="Fetch the latest available stories"):
        st.session_state.articles = []
        st.session_state.ai_cache = {}
        st.rerun()

# ------------------------------- Fetch ----------------------------
if not st.session_state.articles:
    with st.spinner("Finding stories from around the world…"):
        articles, errors = search_news(st.session_state.category, st.session_state.country)
        st.session_state.articles = articles
        st.session_state.errors = errors
        st.session_state.last_fetch = datetime.now(timezone.utc)

articles = st.session_state.articles

# ------------------------------ Discover --------------------------
if nav == "Discover":
    tab1, tab2, tab3, tab4 = st.tabs(["For you", "Global", "Following", "Trending"])
    with tab1:
        a, b, c = st.columns([1.1, 1.1, 2.8])
        with a:
            selected_country = st.selectbox("Geography", ["Global"] + list(COUNTRIES.keys()), key="discover_country")
        with b:
            selected_category = st.selectbox("Topic", ["All"] + CATEGORIES, key="discover_category")
        with c:
            query = st.text_input("Search stories", placeholder="Search countries, companies, topics…", label_visibility="collapsed")
        if st.button("Apply filters", type="primary"):
            st.session_state.country = selected_country
            st.session_state.category = selected_category
            st.session_state.search_query = query
            with st.spinner("Refreshing your feed…"):
                found, errs = search_news(selected_category, selected_country, query)
                st.session_state.articles, st.session_state.errors = found, errs
                st.session_state.ai_cache = {}
                st.session_state.card_index = 0
            st.rerun()
        feed = articles
    with tab2:
        st.markdown("Stories discovered across international reporting.")
        feed = articles
    with tab3:
        st.markdown("Your selected interests: " + " · ".join(st.session_state.interests))
        feed = [a for a in articles if a["category"] in st.session_state.interests] or articles
    with tab4:
        st.markdown("A latest-first view of stories found by connected sources.")
        feed = articles

    if st.session_state.errors:
        with st.expander("Source connection notes"):
            for err in st.session_state.errors:
                st.warning(err)
    if not feed:
        st.info("No stories were returned for these filters. Try another topic or geography.")
    else:
        if "card_index" not in st.session_state:
            st.session_state.card_index = 0
        st.caption(f"{min(st.session_state.card_index+1, len(feed))} of {len(feed)} stories  ·  Source-linked perspective")
        idx = st.session_state.card_index % len(feed)
        article = feed[idx]
        cache_key = article["url"] or article["title"]
        if cache_key not in st.session_state.ai_cache:
            with st.spinner("Preparing a source-grounded perspective…"):
                st.session_state.ai_cache[cache_key] = ai_interpret(article)
        insight = st.session_state.ai_cache[cache_key]
        image_html = (f'<img class="story-image" src="{html.escape(article["image"], quote=True)}" alt="News image" onerror="this.style.display=\'none\'" />'
                      if article["image"] else '<div class="image-placeholder">SIMPL · THE BIGGER PICTURE</div>')
        title = html.escape(article["title"])
        summary = html.escape(insight.get("summary") or article["description"])
        ai_insight = html.escape(insight.get("insight", ""))
        impact = html.escape(insight.get("impact", ""))
        publisher = html.escape(article["source"])
        cat = html.escape(article["category"])
        country = html.escape(article["country"])
        st.markdown(f"""
        <div class="story-card">
          <div class="story-meta"><span>◎ &nbsp;{country}</span><span class="pill">{cat}</span><span style="margin-left:auto;color:#617895">{time_ago(article['published'])}</span></div>
          {image_html}
          <div class="story-body">
            <div class="publisher">◉ &nbsp;{publisher} &nbsp;·&nbsp; Source reporting</div>
            <div class="story-title">{title}</div>
            <div class="story-summary">{summary}</div>
            <hr>
            <div class="section-label">✧ &nbsp; AI insight · interpretation</div>
            <div class="insight-text">{ai_insight}</div>
            <div class="section-label">Why it matters · possible impact</div>
            <div class="insight-text">{impact}</div>
            <div style="margin-top:16px;color:#617895;font-size:.9rem">Confidence: {html.escape(insight.get('confidence','Not assessed'))}</div>
          </div>
          <div class="story-footer"><span>Read original · {publisher}</span><span>Source-linked perspective</span></div>
        </div>
        """, unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1, 1, 1, 5])
        with c1:
            if st.button("↑ Previous", disabled=len(feed) < 2):
                st.session_state.card_index = (idx - 1) % len(feed); st.rerun()
        with c2:
            if st.button("↓ Next", disabled=len(feed) < 2):
                st.session_state.card_index = (idx + 1) % len(feed); st.rerun()
        with c3:
            if st.button("＋ Save"):
                st.session_state.saved.add(cache_key); st.toast("Story saved")
        with c4:
            if article["url"]:
                st.link_button("Read original article ↗", article["url"])
        with st.expander("Behind the story · source and AI basis"):
            st.write(f"**Publisher:** {article['source']}")
            st.write(f"**Published:** {article['published'].strftime('%d %b %Y, %H:%M UTC')}")
            st.write(f"**Article URL:** {article['url']}")
            st.write(f"**AI basis:** {insight.get('basis', 'Only the metadata and excerpt supplied by the news provider were available.')}")
            st.caption("Simpl labels source reporting separately from AI interpretation. The AI analysis is not a substitute for reading the original reporting.")

# -------------------------------- Explore -------------------------
elif nav == "Explore":
    query = st.text_input("⌕  Search countries, companies, topics…", placeholder="Try: India, artificial intelligence, energy")
    x1, x2 = st.columns([1, 1])
    with x1:
        category = st.selectbox("Explore by topic", ["All"] + CATEGORIES)
    with x2:
        country = st.selectbox("Explore by geography", ["Global"] + list(COUNTRIES.keys()))
    if st.button("Explore stories", type="primary"):
        with st.spinner("Searching connected sources…"):
            found, errs = search_news(category, country, query)
            st.session_state.articles, st.session_state.errors = found, errs
            st.session_state.ai_cache = {}
        st.rerun()
    st.markdown("### The bigger picture")
    st.caption(f"{len(articles)} stories currently available")
    for i, article in enumerate(articles):
        image = article["image"]
        left, right = st.columns([1, 5])
        with left:
            if image: st.image(image, use_container_width=True)
            else: st.markdown("▧")
        with right:
            st.markdown(f"**{html.escape(article['title'])}**")
            st.markdown(f"<span class='small-muted'>{html.escape(article['category'])} · {html.escape(article['source'])} · {time_ago(article['published'])}</span>", unsafe_allow_html=True)
            if article["url"]: st.markdown(f"[Read reporting ↗]({article['url']})")
        st.divider()

# -------------------------------- Saved ---------------------------
elif nav == "Saved":
    saved_articles = [a for a in articles if (a["url"] or a["title"]) in st.session_state.saved]
    if not saved_articles:
        st.info("Your saved stories will appear here. Select ＋ Save on any story.")
    for article in saved_articles:
        st.markdown(f"**{article['title']}**")
        st.caption(f"{article['source']} · {article['category']}")
        if article["url"]: st.markdown(f"[Read original ↗]({article['url']})")
        if st.button("Remove saved story", key="remove_"+str(hash(article["title"]))):
            st.session_state.saved.discard(article["url"] or article["title"]); st.rerun()
        st.divider()

# -------------------------------- Profile -------------------------
elif nav == "Profile":
    st.markdown("### Personalise your feed")
    st.write("Choose the topics and geographies you want Simpl to prioritise.")
    interests = st.multiselect("Your interests", CATEGORIES, default=st.session_state.interests)
    country = st.selectbox("Preferred geography", ["Global"] + list(COUNTRIES.keys()), index=(["Global"] + list(COUNTRIES.keys())).index(st.session_state.country) if st.session_state.country in (["Global"] + list(COUNTRIES.keys())) else 0)
    if st.button("Save preferences", type="primary"):
        st.session_state.interests = interests
        st.session_state.country = country
        st.toast("Preferences saved")
    st.markdown("---")
    st.markdown("### Connected intelligence sources")
    st.write("GDELT DOC 2.0 · public global news discovery")
    st.write("RSS · BBC World, BBC Business, NPR World and NASA")
    st.write("NewsAPI · " + ("Connected" if NEWSAPI_KEY else "API key not configured"))
    st.write("The Guardian Open Platform · " + ("Connected" if GUARDIAN_API_KEY else "API key not configured"))
    st.write("OpenAI · " + ("Connected" if OPENAI_API_KEY else "API key not configured"))
    st.caption("Provider coverage, commercial rights and API limits vary. This prototype uses public metadata/excerpts where available and links readers to publishers.")

st.markdown("<div style='text-align:center;color:#8a928d;font-size:.8rem;margin-top:3rem'>Simpl. &nbsp; A little clarity. Every day.</div>", unsafe_allow_html=True)
