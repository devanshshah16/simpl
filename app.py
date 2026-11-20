from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import requests
import streamlit as st
from dateutil import parser as date_parser

st.set_page_config(page_title="Simpl. — A little clarity. Every day.", page_icon="🟢",
                   layout="wide", initial_sidebar_state="expanded")

def secret(key, default=""):
    try:
        return str(st.secrets.get(key, default) or default)
    except Exception:
        return default

NEWSAPI_KEY = secret("NEWSAPI_KEY")
GUARDIAN_API_KEY = secret("GUARDIAN_API_KEY")
OPENAI_API_KEY = secret("OPENAI_API_KEY")
OPENAI_MODEL = secret("OPENAI_MODEL", "gpt-4o-mini")

COUNTRIES = {
    "United States":"US", "United Kingdom":"GB", "India":"IN", "Canada":"CA",
    "Australia":"AU", "Germany":"DE", "France":"FR", "Italy":"IT", "Spain":"ES",
    "Japan":"JP", "China":"CN", "Singapore":"SG", "United Arab Emirates":"AE",
    "Brazil":"BR", "South Africa":"ZA", "Mexico":"MX", "South Korea":"KR",
    "Netherlands":"NL", "Switzerland":"CH", "Ireland":"IE",
}
CATEGORIES = ["Technology","Business","Economy","Geopolitics","Science","Climate",
              "Energy","Politics","Health","Society","Manufacturing"]
CATEGORY_QUERIES = {
    "Technology":"technology OR artificial intelligence OR software",
    "Business":"business OR company OR corporate OR startup",
    "Economy":"economy OR inflation OR interest rates OR trade",
    "Geopolitics":"geopolitics OR diplomacy OR sanctions OR conflict",
    "Science":"science OR research OR space OR discovery",
    "Climate":"climate OR environment OR emissions",
    "Energy":"energy OR oil OR gas OR renewables",
    "Politics":"election OR government OR parliament OR policy",
    "Health":"health OR medicine OR public health",
    "Society":"society OR education OR labor OR culture",
    "Manufacturing":"manufacturing OR industrial OR supply chain",
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Source+Serif+4:wght@600;700&display=swap');
:root{--ink:#171d1a;--muted:#6d7470;--green:#087747;--pale:#e0f2e8;--line:#dfe4e0;--blue:#617895;--paper:#f7f8f7}
html,body,[class*="css"]{font-family:'Inter',Arial,sans-serif;color:var(--ink)}
.stApp{background:var(--paper)} header[data-testid="stHeader"]{background:rgba(247,248,247,.94)}
.block-container{padding-top:1.35rem;padding-bottom:3rem;max-width:1500px}
[data-testid="stSidebar"]{background:#f7f8f7;border-right:1px solid var(--line)}
.logo{font-size:2.65rem;letter-spacing:-2px;font-weight:700;line-height:1;margin:.2rem 0 2.2rem}
.logo span{color:var(--green)} .eyebrow{color:#707772;font-size:.77rem;letter-spacing:2px;font-weight:700;text-transform:uppercase}
.hero-title{font-size:2.65rem;line-height:1.13;font-weight:700;letter-spacing:-1.3px;margin:0}
.hero-sub{color:var(--muted);font-size:1.12rem;margin-top:.45rem;letter-spacing:-.15px}
.story-card{background:white;border:1px solid #e1e7e3;border-radius:18px;overflow:hidden;box-shadow:0 14px 42px rgba(26,43,34,.065);margin:1rem 0 1.5rem}
.story-meta{display:flex;align-items:center;gap:12px;padding:18px 26px;color:#202723;font-size:.9rem;background:linear-gradient(180deg,#fff,#fcfdfc)}
.pill{display:inline-block;background:var(--pale);color:var(--green);padding:7px 13px;border-radius:7px;font-size:.82rem;font-weight:600}
.story-image{width:100%;height:360px;object-fit:cover;display:block;background:#e9eeeb}
.image-placeholder{height:240px;display:flex;align-items:center;justify-content:center;background:linear-gradient(130deg,#e7eee9,#dce7e1);color:#728078}
.story-body{padding:25px 30px 20px}.publisher{color:var(--blue);font-size:.9rem;margin-bottom:12px}
.story-title{font-family:'Source Serif 4',Georgia,serif;font-weight:700;font-size:2.05rem;line-height:1.16;margin:0 0 15px;letter-spacing:-.3px}
.story-summary{color:#303833;font-size:1rem;line-height:1.72;padding-left:1.35rem;margin:.55rem 0 1.15rem}.story-summary li{padding:.28rem 0 .28rem .18rem}.story-summary li::marker{color:#087747;font-weight:700}
.section-label{color:var(--green);font-size:.78rem;letter-spacing:1.8px;font-weight:700;text-transform:uppercase;margin:18px 0 7px}
.insight-text{color:#202723;font-size:1.02rem;line-height:1.55}
.story-footer{border-top:1px solid var(--line);padding:16px 28px;display:flex;justify-content:space-between;color:#6d7470;font-size:.9rem}
.small-muted{color:var(--blue);font-size:.85rem}
div.stButton>button{border-radius:9px;border:1px solid #d9e0dc;font-weight:600}
div.stButton>button[kind="primary"]{background:var(--green);border-color:var(--green)}
hr{border-color:var(--line)} a{color:var(--green)!important}
@media(max-width:800px){.hero-title{font-size:2rem}.story-title{font-size:1.65rem}.story-image{height:230px}.story-body{padding:20px}.block-container{padding-left:1rem;padding-right:1rem}}
</style>
""", unsafe_allow_html=True)

def clean(value):
    if value is None: return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(value)))).strip()

def parsed_date(value):
    try:
        dt = date_parser.parse(str(value))
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)

def article_obj(title="", description="", url="", image="", source="", published=""):
    return {"title":clean(title) or "Untitled story","description":clean(description),
            "url":url or "","image":image or "","source":clean(source) or "News publisher",
            "published":parsed_date(published),"category":"Global","country":"Global"}

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_article_text(url):
    """Best-effort extraction from publicly accessible article pages; never bypasses paywalls."""
    if not url:
        return ""
    try:
        import trafilatura
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SimplNews/1.0)"},
            timeout=12,
        )
        response.raise_for_status()
        extracted = trafilatura.extract(
            response.text,
            include_comments=False,
            include_tables=True,
            favor_precision=True,
        )
        return clean(extracted)[:12000] if extracted else ""
    except Exception:
        return ""


def rss_image(entry):
    for field in ("media_content","media_thumbnail","enclosures"):
        items = entry.get(field) or []
        for item in items:
            link = item.get("url") or item.get("href","")
            if link and (field != "enclosures" or item.get("type","").startswith("image/") or
                         re.search(r"\.(jpg|jpeg|png|webp)(\?|$)",link,re.I)):
                return link
    return ""

# Primary discovery: Google News RSS. Results cached for 15 minutes to avoid
# repeatedly hitting the RSS endpoint during Streamlit reruns.
@st.cache_data(ttl=900, show_spinner=False)
def fetch_google_news(query, country_code="US", max_records=50):
    cc = (country_code or "US").upper()
    url = ("https://news.google.com/rss/search?"
           f"q={quote_plus(query)}&hl=en-{cc}&gl={cc}&ceid={cc}:en")
    response = requests.get(url, headers={"User-Agent":"Mozilla/5.0 SimplNews/1.0"}, timeout=20)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    if getattr(feed,"bozo",False) and not feed.entries:
        raise RuntimeError("Google News returned an unreadable RSS feed.")
    rows = []
    for entry in feed.entries[:max_records]:
        src = entry.get("source")
        publisher = src.get("title") if src else "Google News"
        rows.append(article_obj(entry.get("title"),entry.get("summary"),entry.get("link"),
                                rss_image(entry),publisher,
                                entry.get("published") or entry.get("updated")))
    return rows

# Optional supplemental APIs. Neither is required for the app to run.
def fetch_newsapi(query, limit=25):
    if not NEWSAPI_KEY: return []
    r = requests.get("https://newsapi.org/v2/everything",
        params={"q":query,"pageSize":min(limit,100),"sortBy":"publishedAt",
                "language":"en","apiKey":NEWSAPI_KEY},timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "ok": raise RuntimeError(data.get("message","NewsAPI error"))
    return [article_obj(x.get("title"),x.get("description") or x.get("content"),
            x.get("url"),x.get("urlToImage"),(x.get("source") or {}).get("name"),
            x.get("publishedAt")) for x in data.get("articles",[])]

def fetch_guardian(query, limit=20):
    if not GUARDIAN_API_KEY: return []
    r = requests.get("https://content.guardianapis.com/search",
        params={"q":query,"api-key":GUARDIAN_API_KEY,"show-fields":"thumbnail,trailText",
                "page-size":min(limit,50),"order-by":"newest"},timeout=20)
    r.raise_for_status()
    data = r.json()
    if data.get("response",{}).get("status") != "ok": raise RuntimeError("Guardian API error")
    rows=[]
    for x in data.get("response",{}).get("results",[]):
        f=x.get("fields",{})
        rows.append(article_obj(x.get("webTitle"),f.get("trailText"),x.get("webUrl"),
                                f.get("thumbnail"),"The Guardian",x.get("webPublicationDate")))
    return rows

def category_for(a):
    text=(a["title"]+" "+a["description"]).lower()
    terms={
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
    }
    for cat, words in terms.items():
        if any(w in text for w in words): return cat
    return "Society"

def deduplicate(rows):
    seen=set(); result=[]
    for a in sorted(rows,key=lambda x:x["published"],reverse=True):
        key=re.sub(r"[^a-z0-9]","",a["title"].lower())[:110]
        if key and key not in seen:
            seen.add(key); result.append(a)
    return result

@st.cache_data(ttl=900, show_spinner=False)
def search_news(category, country, custom_query=""):
    query=custom_query.strip() or (CATEGORY_QUERIES.get(category,"world news") if category!="All" else "world news")
    cc=COUNTRIES.get(country,"US")
    rows=[]; errors=[]
    try:
        rows.extend(fetch_google_news(query,cc,50))
    except requests.HTTPError as e:
        status=e.response.status_code if e.response is not None else "HTTP"
        errors.append(f"Google News RSS returned HTTP {status}. Try again in a few minutes.")
    except requests.RequestException as e:
        errors.append(f"Google News RSS connection issue: {str(e)[:140]}")
    except Exception as e:
        errors.append(f"Google News RSS: {str(e)[:140]}")
    if NEWSAPI_KEY:
        try: rows.extend(fetch_newsapi(custom_query or query))
        except Exception as e: errors.append(f"NewsAPI: {str(e)[:140]}")
    if GUARDIAN_API_KEY:
        try: rows.extend(fetch_guardian(custom_query or query))
        except Exception as e: errors.append(f"Guardian: {str(e)[:140]}")
    rows=deduplicate(rows)
    for a in rows:
        a["category"]=category_for(a)
        a["country"]=country
    if category!="All":
        rows=[a for a in rows if a["category"]==category or
              category.lower() in (a["title"]+" "+a["description"]).lower()]
    return rows[:60],errors

def ai_interpret(a):
    if not OPENAI_API_KEY:
        fallback = a.get("description") or "The available article text is too limited to produce a verified factual brief."
        return {
            "facts": [fallback],
            "insight": "Add an OpenAI API key to enable source-grounded AI interpretation.",
            "impact": "Potential consequences are not generated until sufficient source text is available.",
            "confidence": "Not assessed",
            "basis": "OPENAI_API_KEY is not configured.",
            "error": "No API key was found. Check Streamlit Secrets and restart the app."
        }

    source_text = a.get("full_text") or a.get("description") or a.get("title", "")
    source_level = "extracted article text" if a.get("full_text") else "publisher-provided headline and RSS excerpt"

    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=45, max_retries=2)

        prompt = f"""You are the news editor for Simpl. Produce a useful, detailed but concise news brief.

STRICT EVIDENCE RULES:
- Use ONLY the supplied source text. Do not use outside knowledge.
- Do not imply you read more than the supplied text.
- Do not invent, estimate, calculate or infer facts, dates, names, figures or numbers.
- If the source does not state a detail, omit it.
- Clearly separate reported facts from interpretation and possible impact.
- If the input is only a headline or short excerpt, say that the brief is limited.

Return valid JSON with exactly these keys:
- facts: an array of 5 to 8 informative bullet points, where the source supports that many.
  Aim for a fuller summary, not headline paraphrases. Capture what happened, who is involved,
  where and when, stated figures, decisions, responses, sequence, and relevant context.
  Each point should be one concise sentence. Do not repeat the headline.
  If the source supports only 1-4 facts, return only those facts; never pad or speculate.
- insight: 1-2 sentences of clearly labelled AI interpretation, max 35 words.
- impact: 1-2 sentences on plausible consequences, conditional and explicitly framed as analysis,
  max 30 words.
- confidence: High, Medium, or Low, based on the amount and specificity of source text.
- basis: explain whether the analysis used full extracted article text or only a headline/excerpt.

Keep facts + insight + impact under 160 words. Return no markdown, only JSON.

HEADLINE: {a.get('title', '')}
PUBLISHER: {a.get('source', '')}
TEXT TYPE: {source_level}
AVAILABLE SOURCE TEXT:
{source_text[:12000]}
ARTICLE URL: {a.get('url', '')}
"""
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": "You are a rigorous fact-checking news editor. Never fabricate facts or figures."},
                {"role": "user", "content": prompt},
            ],
        )
        data = json.loads(response.choices[0].message.content or "{}")
        facts = data.get("facts", [])
        if isinstance(facts, str):
            facts = [facts]
        facts = [clean(item) for item in facts if clean(item)]
        data["facts"] = facts[:8] or ["The accessible source text does not contain enough detail to list verified facts."]
        for field in ("insight", "impact", "confidence", "basis"):
            data[field] = clean(data.get(field, ""))
        data["error"] = ""
        return data

    except Exception as exc:
        fallback = a.get("description") or "The publisher's accessible text did not contain enough detail for a factual summary."
        message = str(exc)
        # Keep actionable diagnostics visible in the Behind the story panel.
        if "401" in message or "Incorrect API key" in message or "invalid_api_key" in message:
            hint = "OpenAI rejected the API key. Check that the key is copied correctly and belongs to an active project."
        elif "429" in message or "insufficient_quota" in message:
            hint = "OpenAI returned a quota/rate-limit error. Check API billing, available credits and usage limits."
        elif "model" in message.lower() and ("not found" in message.lower() or "does not exist" in message.lower()):
            hint = f"The configured model '{OPENAI_MODEL}' may not be available to this API project. Check OPENAI_MODEL."
        else:
            hint = "Check the OpenAI API key, API billing, model access and the detailed error below."
        return {
            "facts": [fallback],
            "insight": "AI interpretation could not be generated for this story.",
            "impact": "Read the original reporting before drawing conclusions.",
            "confidence": "Not assessed",
            "basis": f"Analysis attempted using {source_level}.",
            "error": f"{hint} Technical detail: {message[:350]}"
        }

def ago(dt):
    sec=max(0,int((datetime.now(timezone.utc)-dt).total_seconds()))
    if sec<3600: return f"about {max(1,sec//60)} min ago"
    if sec<86400: return f"about {sec//3600} hours ago"
    return f"about {sec//86400} days ago"

# Session state: note that these are session-only, not persistent multi-user storage.
defaults={"articles":[],"errors":[],"saved":set(),"interests":["Technology","Business","Economy","Geopolitics","Science"],
          "card_index":0,"ai_cache":{},"country":"Global","category":"All","search_query":""}
for k,v in defaults.items():
    if k not in st.session_state: st.session_state[k]=v

def load_feed(cat,country,query=""):
    with st.spinner("Finding stories from around the world…"):
        rows,errs=search_news(cat,country,query)
        st.session_state.articles=rows; st.session_state.errors=errs
        st.session_state.ai_cache={}; st.session_state.card_index=0
        st.session_state.category=cat; st.session_state.country=country
        st.session_state.search_query=query

with st.sidebar:
    st.markdown('<div class="logo">Simpl<span>.</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="eyebrow">YOUR WORLD, UNDERSTOOD</div>',unsafe_allow_html=True)
    nav=st.radio("Navigation",["Discover","Explore","Saved","Profile"],label_visibility="collapsed")
    st.markdown("---")
    st.markdown('<div class="eyebrow">YOUR INTERESTS</div>',unsafe_allow_html=True)
    for item in st.session_state.interests:
        st.markdown(f'<div style="padding:9px 0;font-weight:600">● &nbsp;{html.escape(item)}</div>',unsafe_allow_html=True)
    with st.expander("＋ Add interests"):
        chosen=st.multiselect("Choose topics",CATEGORIES,default=st.session_state.interests)
        if st.button("Save interests",use_container_width=True):
            st.session_state.interests=chosen; st.rerun()
    st.markdown("---")
    st.markdown('<div class="eyebrow">PERSPECTIVE, NOT NOISE</div>',unsafe_allow_html=True)
    st.markdown('<div style="color:#617895;line-height:2.1">Credible reporting.<br>Clearly labelled interpretation.</div>',unsafe_allow_html=True)
    st.caption("A little clarity. Every day.")

titles={"Discover":("A world of perspective.","The stories that matter. The context you need."),
        "Explore":("Follow your curiosity.","Different places. New perspectives."),
        "Saved":("Worth keeping.","Your saved stories, all in one place."),
        "Profile":("Your perspective.","Shape the world you want to understand.")}
left,right=st.columns([8,1])
with left:
    st.markdown(f'<div class="hero-title">{titles[nav][0]}</div><div class="hero-sub">{titles[nav][1]}</div>',unsafe_allow_html=True)
with right:
    st.write(""); st.write("")
    if st.button("↻ Refresh"):
        search_news.clear(); fetch_google_news.clear()
        load_feed(st.session_state.category,st.session_state.country,st.session_state.search_query)
        st.rerun()

if not st.session_state.articles:
    load_feed("All","Global")
articles=st.session_state.articles

if nav=="Discover":
    tabs=st.tabs(["For you","Global","Following","Trending"])
    with tabs[0]:
        c1,c2,c3=st.columns([1.2,1.2,2.6])
        with c1: selected_country=st.selectbox("Geography",["Global"]+list(COUNTRIES),key="feed_country")
        with c2: selected_category=st.selectbox("Topic",["All"]+CATEGORIES,key="feed_category")
        with c3: query=st.text_input("Search stories",placeholder="Search countries, companies, topics…",label_visibility="collapsed")
        if st.button("Apply filters",type="primary"):
            load_feed(selected_category,selected_country,query); st.rerun()
        feed=articles
    with tabs[1]:
        st.markdown("Stories discovered across international reporting."); feed=articles
    with tabs[2]:
        st.markdown("Your selected interests: "+" · ".join(st.session_state.interests))
        feed=[a for a in articles if a["category"] in st.session_state.interests] or articles
    with tabs[3]:
        st.markdown("Latest stories returned by connected sources."); feed=articles

    if st.session_state.errors:
        with st.expander("Source connection notes"):
            for err in st.session_state.errors: st.warning(err)
    if not feed:
        st.info("No stories returned. Try another topic or geography, or refresh in a few minutes.")
    else:
        idx=st.session_state.card_index%len(feed); a=feed[idx]
        key=a["url"] or a["title"]
        if key not in st.session_state.ai_cache:
            with st.spinner("Reading the available reporting and preparing your brief…"):
                enriched = dict(a)
                enriched["full_text"] = fetch_article_text(a.get("url", ""))
                st.session_state.ai_cache[key] = ai_interpret(enriched)
        insight=st.session_state.ai_cache[key]
        image=(f'<img class="story-image" src="{html.escape(a["image"],quote=True)}" alt="News image" />'
               if a["image"] else '<div class="image-placeholder">SIMPL. · THE BIGGER PICTURE</div>')
        st.caption(f"{idx+1} of {len(feed)} stories · Source-linked perspective")
        fact_items = "".join(
            f"<li>{html.escape(point)}</li>"
            for point in insight.get("facts", [])
        )
        st.markdown(f"""
        <div class="story-card">
          <div class="story-meta"><span>◎ &nbsp;{html.escape(a['country'])}</span>
          <span class="pill">{html.escape(a['category'])}</span>
          <span style="margin-left:auto;color:#617895">{ago(a['published'])}</span></div>
          {image}
          <div class="story-body">
            <div class="publisher">◉ &nbsp;{html.escape(a['source'])} &nbsp;·&nbsp; Source reporting</div>
            <div class="story-title">{html.escape(a['title'])}</div>
            <div class="section-label">Key facts · source reporting</div>
            <ol class="story-summary">{fact_items}</ol><hr>
            <div class="section-label">✧ &nbsp; AI insight · interpretation</div>
            <div class="insight-text">{html.escape(insight.get('insight',''))}</div>
            <div class="section-label">Why it matters · possible impact</div>
            <div class="insight-text">{html.escape(insight.get('impact',''))}</div>
            <div style="margin-top:16px;color:#617895;font-size:.9rem">Confidence: {html.escape(insight.get('confidence','Not assessed'))}</div>
          </div>
          <div class="story-footer"><span>Read original · {html.escape(a['source'])}</span><span>Source-linked perspective</span></div>
        </div>""",unsafe_allow_html=True)
        p,n,s,l=st.columns([1,1,1,4])
        with p:
            if st.button("↑ Previous",disabled=len(feed)<2):
                st.session_state.card_index=(idx-1)%len(feed); st.rerun()
        with n:
            if st.button("↓ Next",disabled=len(feed)<2):
                st.session_state.card_index=(idx+1)%len(feed); st.rerun()
        with s:
            if st.button("＋ Save"):
                st.session_state.saved.add(key); st.toast("Story saved")
        with l:
            if a["url"]: st.link_button("Read original article ↗",a["url"])
        with st.expander("Behind the story · source and AI basis"):
            st.write(f"**Publisher:** {a['source']}")
            st.write(f"**Published:** {a['published'].strftime('%d %b %Y, %H:%M UTC')}")
            st.write(f"**Original article:** {a['url']}")
            st.write(f"**AI basis:** {insight.get('basis','Only provider-returned title and excerpt were available.')}")
            if insight.get("error"):
                st.error(insight["error"])
            st.caption("Simpl. attempts to extract publicly accessible article text. Paywalls, publisher restrictions and site layouts may limit extraction. AI interpretation is distinct from source reporting.")

elif nav=="Explore":
    query=st.text_input("Search countries, companies, topics…",placeholder="Try: India, artificial intelligence, energy")
    c1,c2=st.columns(2)
    with c1: cat=st.selectbox("Explore by topic",["All"]+CATEGORIES)
    with c2: country=st.selectbox("Explore by geography",["Global"]+list(COUNTRIES))
    if st.button("Explore stories",type="primary"):
        load_feed(cat,country,query); st.rerun()
    st.markdown("### The bigger picture"); st.caption(f"{len(articles)} stories currently available")
    for a in articles:
        x,y=st.columns([1,5])
        with x:
            if a["image"]: st.image(a["image"],use_container_width=True)
            else: st.markdown("▧")
        with y:
            st.markdown(f"**{html.escape(a['title'])}**")
            st.markdown(f"<span class='small-muted'>{html.escape(a['category'])} · {html.escape(a['source'])} · {ago(a['published'])}</span>",unsafe_allow_html=True)
            if a["url"]: st.markdown(f"[Read reporting ↗]({a['url']})")
        st.divider()

elif nav=="Saved":
    saved=[a for a in articles if (a["url"] or a["title"]) in st.session_state.saved]
    if not saved: st.info("Your saved stories will appear here. Select ＋ Save on any story.")
    for a in saved:
        st.markdown(f"**{html.escape(a['title'])}**"); st.caption(f"{a['source']} · {a['category']}")
        if a["url"]: st.markdown(f"[Read original ↗]({a['url']})")
        if st.button("Remove saved story",key="remove_"+str(hash(a["title"]))):
            st.session_state.saved.discard(a["url"] or a["title"]); st.rerun()
        st.divider()

elif nav=="Profile":
    st.markdown("### Personalise your feed")
    interests=st.multiselect("Your interests",CATEGORIES,default=st.session_state.interests)
    options=["Global"]+list(COUNTRIES)
    current=st.session_state.country if st.session_state.country in options else "Global"
    country=st.selectbox("Preferred geography",options,index=options.index(current))
    if st.button("Save preferences",type="primary"):
        st.session_state.interests=interests; st.session_state.country=country; st.toast("Preferences saved")
    st.markdown("---"); st.markdown("### Connected intelligence sources")
    st.write("Google News RSS · Primary discovery connection (no API key)")
    st.write("NewsAPI · "+("Connected" if NEWSAPI_KEY else "Optional API key not configured"))
    st.write("The Guardian · "+("Connected" if GUARDIAN_API_KEY else "Optional API key not configured"))
    st.write("OpenAI · "+("API key detected" if OPENAI_API_KEY else "API key not configured"))
    if st.button("Test OpenAI connection"):
        if not OPENAI_API_KEY:
            st.error("No OPENAI_API_KEY found. Add it to .streamlit/secrets.toml locally or Streamlit Cloud → Settings → Secrets.")
        else:
            try:
                from openai import OpenAI
                OpenAI(api_key=OPENAI_API_KEY, timeout=20).models.retrieve(OPENAI_MODEL)
                st.success(f"OpenAI connection successful. Model '{OPENAI_MODEL}' is accessible.")
            except Exception as exc:
                st.error(f"OpenAI connection failed: {str(exc)[:500]}")
    st.caption("Coverage, rate limits, content access and redistribution rights vary. Simpl. links to publishers and does not bypass paywalls.")

st.markdown("<div style='text-align:center;color:#8a928d;font-size:.8rem;margin-top:3rem'>Simpl. &nbsp; A little clarity. Every day.</div>",unsafe_allow_html=True)
