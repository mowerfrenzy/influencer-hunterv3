
import io, re, json, time, random, urllib.robotparser
from urllib.parse import urlparse, urljoin
import pandas as pd
import requests
import feedparser
import streamlit as st
from bs4 import BeautifulSoup

APP = "Influencer Hunter Global"
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
IG_RE = re.compile(r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]+)/?", re.I)
DEFAULT_ACTOR = "apify/instagram-scraper"
COLS = ["username","profile_url","niche","creator_country","audience_countries","followers",
        "avg_likes","avg_comments","engagement_rate","posts_sampled","email","email_source_url",
        "website_url","creator_type","offer_evidence","audience_problem_evidence","trust_evidence",
        "evidence_url","discovered_from","score","qualified","qualification_notes"]

NICHES = {
"Wealth": {
"Trading": ["day trading","options trading","futures","crypto trading"],
"Ecommerce": ["Amazon FBA","Amazon wholesale and private label","Shopify dropshipping","TikTok Shop","print on demand","online and retail arbitrage"],
"Real estate and property": ["wholesaling","rental property investing","house flipping","land flipping","Airbnb and short-term rental arbitrage","short-term rental management","commercial property","agent and realtor coaching"],
"AI and automation": ["AI automation agencies","faceless YouTube automation","short-form clipping","AI content businesses","selling automations to local businesses","micro-SaaS and AI-assisted building"],
"Sales and closing": ["high-ticket closing","appointment setting","cold calling","cold email","sales team training","door-to-door and in-home sales"],
"Agency and consulting": ["social media marketing agencies","growth operating","ghostwriting","consulting","coaching business growth","bookkeeping and accounting firms"],
"Copywriting and marketing skills": ["email copywriting","direct response copywriting","paid media buying","ads agencies"],
"Service and offline businesses": ["construction and contracting","landscaping","cleaning and pressure washing","HVAC, plumbing and roofing","trucking, logistics and dispatching","staffing and recruiting","med spa, salon and barbershop ownership","gym and studio ownership","medical, dental and legal practice growth"],
"Buying and scaling businesses": ["acquiring existing businesses","franchising","business credit and funding"],
"Education and career": ["college and Ivy League admissions","executive career coaching","promotions and salary negotiation","software and tech job coaching","skilled trades and apprenticeships"]},
"Health": {
"Fitness and body composition": ["weight loss and body recomposition","GLP-1 support","strength training for over-40s","running, marathon and hybrid training","postpartum recovery and pre/postnatal training","perimenopause training and nutrition"],
"Sleep and longevity": ["sleep","longevity and healthspan","metabolic health"],
"Hormone health": ["hormone imbalance","PCOS","thyroid","cortisol and stress","menopause","testosterone","fertility and trying to conceive"],
"Gut health": ["IBS","bloating","microbiome","food intolerance","gut healing protocols"],
"Functional and holistic medicine": ["root cause healing","autoimmune protocols","chronic fatigue"],
"Pain, injury and movement": ["chronic pain","sciatica and back pain","injury rehab at home","mobility"],
"Mind and mental health": ["anxiety","depression","trauma and inner child work","nervous system regulation","somatic healing","emotional regulation","adult ADHD and late diagnosis"]},
"Relationships": {
"Dating and attraction": ["dating for men","dating for women","dating after divorce","online dating and apps","matchmaking and dating for wealthy clients"],
"Marriage and long-term relationships": ["marriage counselling","communication and conflict","intimacy","infidelity recovery","premarital coaching","faith-based marriage"],
"Breakups, divorce and recovery": ["breakup recovery","divorce coaching","narcissistic abuse recovery","co-parenting"],
"Attachment patterns": ["anxious attachment","avoidant attachment","the anxious-avoidant pairing","building secure attachment","neurodivergent and ADHD relationships"],
"Boundaries and people-pleasing": ["people-pleasing","boundary setting","codependency","self-worth"],
"Parenting and family": ["gentle and conscious parenting","positive discipline","toddlers and big feelings","parenting teenagers","blended families and step-parenting","homeschooling","special needs parenting","caregiving for ageing parents","estranged and difficult family relationships"],
"Men's work and fatherhood": ["men's work and masculinity","fatherhood"],
"Social skills and confidence": ["social skills for adults","public speaking and stage fright","workplace relationships and managing up","leadership and team management"]}
}
ALL_NICHES = [n for groups in NICHES.values() for vals in groups.values() for n in vals]
HEADERS = {"User-Agent":"InfluencerHunterGlobal/2.0 (public business contact research)"}

def clean_html(s): return BeautifulSoup(s or "", "html.parser").get_text(" ", strip=True)
def profile_from_text(s):
    m=IG_RE.search(s or "")
    if not m: return "", ""
    u=m.group(1).strip(".")
    if u.lower() in {"p","reel","reels","stories","explore","accounts","about","direct"}: return "", ""
    return u, f"https://www.instagram.com/{u}/"
def er_calc(f,l,c):
    try:
        f=float(f); return ((float(l or 0)+float(c or 0))/f*100) if f>0 else 0
    except: return 0
def empty(): return pd.DataFrame(columns=COLS)
def normalize(df):
    for c in COLS:
        if c not in df: df[c]=""
    df=df[COLS].copy()
    for c in ["followers","avg_likes","avg_comments","engagement_rate","posts_sampled","score"]:
        df[c]=pd.to_numeric(df[c],errors="coerce").fillna(0)
    for c in COLS:
        if c not in ["followers","avg_likes","avg_comments","engagement_rate","posts_sampled","score","qualified"]:
            df[c]=df[c].fillna("").astype(str).str.strip()
    df["username"]=df["username"].str.replace("@","",regex=False)
    df["email"]=df["email"].str.lower()
    return df
def parse_rss(urls):
    rows=[]
    for url in urls:
        try:
            feed=feedparser.parse(url)
            for e in feed.entries:
                blob=" ".join([getattr(e,"title",""),clean_html(getattr(e,"summary","")),getattr(e,"link","")])
                u,p=profile_from_text(blob)
                if u:
                    emails=EMAIL_RE.findall(blob); link=getattr(e,"link","")
                    rows.append({"username":u,"profile_url":p,"email":emails[0] if emails else "",
                    "email_source_url":link if emails else "", "evidence_url":link,"discovered_from":url})
        except Exception as ex: st.warning(f"RSS feed error: {ex}")
    return rows
def apify_run(token, actor, payload, timeout=180):
    url=f"https://api.apify.com/v2/acts/{actor.replace('/','~')}/run-sync-get-dataset-items"
    r=requests.post(url,params={"token":token,"clean":"true","format":"json"},json=payload,timeout=timeout)
    if r.status_code>=400: raise RuntimeError(f"Apify API {r.status_code}: {r.text[:500]}")
    return r.json()
def getv(d,*keys,default=None):
    for k in keys:
        v=d.get(k)
        if v is not None and v!="": return v
    return default
def map_apify(items):
    rows=[]
    for x in items if isinstance(items,list) else []:
        u=getv(x,"username","ownerUsername","owner_username","userName",default="")
        if not u and isinstance(x.get("owner"),dict): u=getv(x["owner"],"username",default="")
        u=str(u).lstrip("@")
        if not u: continue
        posts=getv(x,"latestPosts","latest_posts","posts",default=[])
        if isinstance(posts,str):
            try: posts=json.loads(posts)
            except: posts=[]
        posts=posts if isinstance(posts,list) else []
        likes=[]; comments=[]
        for p in posts:
            likes.append(float(getv(p,"likesCount","likes","like_count",default=0) or 0))
            comments.append(float(getv(p,"commentsCount","comments","comment_count",default=0) or 0))
        followers=float(getv(x,"followersCount","followers_count","followers",default=0) or 0)
        al=sum(likes)/len(likes) if likes else 0
        ac=sum(comments)/len(comments) if comments else 0
        bio=str(getv(x,"biography","bio",default="") or "")
        website=str(getv(x,"externalUrl","external_url","website",default="") or "")
        emails=EMAIL_RE.findall(bio)
        rows.append({"username":u,"profile_url":f"https://www.instagram.com/{u}/","followers":followers,
          "avg_likes":al,"avg_comments":ac,"engagement_rate":er_calc(followers,al,ac),
          "posts_sampled":len(posts),"website_url":website,"email":emails[0] if emails else "",
          "email_source_url":f"https://www.instagram.com/{u}/" if emails else "",
          "evidence_url":f"https://www.instagram.com/{u}/","discovered_from":"Apify profile lookup"})
    return rows
def robots_allowed(url):
    p=urlparse(url); rp=urllib.robotparser.RobotFileParser()
    rp.set_url(f"{p.scheme}://{p.netloc}/robots.txt")
    try: rp.read(); return rp.can_fetch(HEADERS["User-Agent"],url)
    except: return False
def website_email(url):
    if not url: return [],""
    if not url.startswith(("http://","https://")): url="https://"+url
    p=urlparse(url)
    if not p.netloc or p.netloc.lower().endswith("instagram.com"): return [],"Invalid or Instagram URL"
    todo=[url]; seen=set(); found=set()
    while todo and len(seen)<4:
        cur=todo.pop(0).split("#")[0]
        if cur in seen or urlparse(cur).netloc!=p.netloc: continue
        seen.add(cur)
        if not robots_allowed(cur): continue
        try:
            r=requests.get(cur,headers=HEADERS,timeout=10); r.raise_for_status()
            if "text/html" not in r.headers.get("content-type",""): continue
            soup=BeautifulSoup(r.text[:1200000],"html.parser")
            found.update(EMAIL_RE.findall(soup.get_text(" ",strip=True)))
            for a in soup.find_all("a",href=True):
                dest=urljoin(cur,a["href"])
                label=(a.get_text(" ",strip=True)+" "+dest).lower()
                if urlparse(dest).netloc==p.netloc and any(k in label for k in ["contact","about","booking","work with","collaborat"]):
                    if dest not in seen and len(todo)+len(seen)<4: todo.append(dest)
            time.sleep(.5)
        except requests.RequestException: pass
    return sorted(found),"Checked supplied site and same-domain contact links; robots.txt respected."
def qualify(df,minf,maxf,minger):
    out=[]
    for _,r in normalize(df).iterrows():
        er=er_calc(r.followers,r.avg_likes,r.avg_comments); notes=[]
        if not r.username: notes.append("Missing Instagram username")
        if not minf<=r.followers<=maxf: notes.append("Follower count outside range or unverified")
        if not er>minger: notes.append(f"Engagement must be strictly above {minger:.2f}%")
        if r.posts_sampled<5: notes.append("Fewer than 5 recent posts sampled; verify manually")
        if not r.niche: notes.append("Niche not confirmed")
        if not r.audience_countries: notes.append("Audience country not verified")
        if not r.email or not EMAIL_RE.fullmatch(r.email): notes.append("No valid public business email")
        if not r.email_source_url: notes.append("Missing public email source URL")
        if r.creator_type.lower() not in ["individual","creator","individual creator"]: notes.append("Individual creator not confirmed")
        if not r.offer_evidence: notes.append("No evidence of a monetized offer")
        score=0
        score += 10 if minf<=r.followers<=maxf else 0
        score += 20 if er>minger else 0
        score += 10 if r.audience_countries else 0
        score += 15 if r.niche else 0
        score += 15 if r.audience_problem_evidence else 0
        score += 15 if r.trust_evidence else 0
        score += 10 if r.offer_evidence else 0
        score += 5 if r.email and r.email_source_url else 0
        r["engagement_rate"]=round(er,2); r["score"]=score
        r["qualified"]=len(notes)==0
        r["qualification_notes"]="Qualified" if not notes else "; ".join(notes)
        out.append(r)
    return pd.DataFrame(out,columns=COLS)

st.set_page_config(page_title=APP,page_icon="🎯",layout="wide")
st.title("🎯 Influencer Hunter — Global")
st.caption("Discover candidates, enrich public profile metrics, score ICP fit, and export verified business leads.")
if "leads" not in st.session_state: st.session_state.leads=empty()
with st.sidebar:
    st.header("Qualification rules")
    minf=st.number_input("Minimum followers",1000,10000000,10000,1000)
    maxf=st.number_input("Maximum followers",1000,10000000,100000,5000)
    minger=st.number_input("Minimum engagement (%)",0.0,100.0,3.0,.25)
    target=st.number_input("Qualified lead target",1,500,100)
    st.caption("Global country targeting: no country whitelist. Record audience countries separately from creator location.")
    st.divider()
    st.caption("Health niche safeguard: for diagnosis, medication or treatment topics, only consider appropriately qualified creators whose offer teaches management rather than direct treatment.")

tabs=st.tabs(["1 · Discover","2 · Verify profiles","3 · Enrich & qualify","4 · Review & export","5 · Niche library"])
with tabs[0]:
    st.subheader("Discover candidate Instagram profiles")
    st.markdown("**Option A — Google Alerts RSS (free):** create alerts for niche keywords and paste RSS feed URLs.")
    feeds=st.text_area("RSS feed URLs — one per line",height=90,placeholder="https://www.google.com/alerts/feeds/...")
    if st.button("Import RSS discoveries",type="primary"):
        rows=parse_rss([x.strip() for x in feeds.splitlines() if x.strip()])
        if rows:
            st.session_state.leads=normalize(pd.concat([st.session_state.leads,pd.DataFrame(rows)],ignore_index=True).drop_duplicates("username",keep="first"))
            st.success(f"Imported {len(rows)} candidate records (before deduplication).")
        else: st.info("No Instagram profile URLs found in these feeds.")
    st.divider()
    st.markdown("**Option B — Generate Instagram search dorks**")
    st.caption('Builds searches in the format: site:instagram.com "father" "gmail.com" "56.5k followers".')
    chosen=st.multiselect("Choose niches / keywords",ALL_NICHES,default=["AI automation agencies","Shopify dropshipping","weight loss and body recomposition","dating for men","parenting teenagers"])
    email_term=st.text_input("Public contact email term",value="gmail.com",help="Examples: gmail.com, business email, contact")
    per_niche=st.slider("Random follower-count queries per niche",1,20,8)
    if st.button("Generate Discover dorks",type="primary",disabled=not chosen):
        query_lines=[]
        for niche in chosen:
            # Generate random one-decimal follower counts from 10.0k through 99.9k.
            counts=random.sample(range(100,1000), k=per_niche)
            for count in counts:
                follower_text=f"{count/10:.1f}k followers"
                query_lines.append(f'site:instagram.com "{niche}" "{email_term}" "{follower_text}"')
        st.session_state["discover_dorks"]="\n".join(query_lines)
    if st.session_state.get("discover_dorks"):
        st.text_area("Copy these into Google Search",value=st.session_state["discover_dorks"],height=260)
        st.download_button("Download Discover dorks", st.session_state["discover_dorks"], "instagram_discover_dorks.txt")
    st.info("Discovery sources return candidates, not proof of follower count, audience geography, engagement, or buying intent. Do not treat search snippets as verification.")
with tabs[1]:
    st.subheader("Bulk verify public Instagram profiles with Apify")
    st.write("This optional connector retrieves public profile data and recent posts through an Apify Actor. You supply your own Apify token and pay any Actor charges. No Instagram password or cookies are requested.")
    token=st.text_input("Apify API token",type="password",help="Stored only in this running local app session; never add it to a CSV.")
    actor=st.text_input("Apify Actor ID",value=DEFAULT_ACTOR,help="Default: apify/instagram-scraper. You can change this to another compatible Actor.")
    urls=st.text_area("Instagram profile URLs or usernames — one per line",height=130,placeholder="https://www.instagram.com/creatorname/\n@anothercreator")
    limit=st.slider("Maximum recent posts per profile (where supported)",5,24,12)
    custom=st.text_area("Advanced Actor input JSON (optional)",height=110,placeholder='Leave blank to use a standard directUrls input.')
    if st.button("Run bulk profile verification",type="primary",disabled=not token or not urls.strip()):
        prof=[]
        for line in urls.splitlines():
            line=line.strip()
            if not line: continue
            if line.startswith("@"): line="https://www.instagram.com/"+line[1:]+"/"
            elif "instagram.com" not in line: line="https://www.instagram.com/"+line.strip("/")+"/"
            prof.append(line)
        try:
            payload=json.loads(custom) if custom.strip() else {"directUrls":prof,"resultsType":"details","resultsLimit":limit}
            with st.spinner("Running profile lookup…"):
                data=apify_run(token,actor,payload)
            mapped=map_apify(data)
            if mapped:
                st.session_state.leads=normalize(pd.concat([st.session_state.leads,pd.DataFrame(mapped)],ignore_index=True).drop_duplicates("username",keep="last"))
                st.success(f"Received {len(mapped)} profile records. Check recent-post sample counts and review each profile.")
                st.dataframe(pd.DataFrame(mapped)[["username","followers","avg_likes","avg_comments","engagement_rate","posts_sampled","website_url"]],use_container_width=True)
            else: st.warning("No profile rows were returned. Check Actor ID, input format, and dataset output schema.")
        except Exception as e: st.error(str(e))
    st.caption("Apify Actor input schemas differ. If your chosen Actor uses different field names, paste its exact input JSON in Advanced Actor input. Set a hard spend cap in Apify Console before starting a run.")
with tabs[2]:
    st.subheader("Import data and enrich public business contacts")
    st.write("Use CSV for candidates or to add manually verified audience-country, niche, offer and trust evidence.")
    up=st.file_uploader("Upload CSV",type=["csv"])
    if up:
        try:
            imported=normalize(pd.read_csv(up))
            st.session_state.leads=normalize(pd.concat([st.session_state.leads,imported],ignore_index=True).drop_duplicates("username",keep="last"))
            st.success(f"Imported {len(imported)} rows.")
        except Exception as e: st.error(f"CSV import failed: {e}")
    if not st.session_state.leads.empty:
        st.markdown("**Find public business emails on creator websites**")
        choices=st.session_state.leads.index[st.session_state.leads.website_url.astype(str).str.len()>5].tolist()
        if choices:
            idx=st.selectbox("Choose a creator website to check",choices,format_func=lambda i: st.session_state.leads.loc[i,"username"] or f"Row {i+1}")
            if st.button("Check website for public email"):
                emails,note=website_email(st.session_state.leads.loc[idx,"website_url"])
                if emails:
                    st.session_state.leads.loc[idx,"email"]=emails[0]
                    st.session_state.leads.loc[idx,"email_source_url"]=st.session_state.leads.loc[idx,"website_url"]
                    st.success("Found: "+", ".join(emails))
                else: st.info("No email found. "+note)
    st.markdown("**Edit candidate records**")
    st.caption("Enter audience countries, creator niche, individual/creator type, and evidence. A creator's residence is not a substitute for audience geography.")
    edited=st.data_editor(normalize(st.session_state.leads),num_rows="dynamic",use_container_width=True,
      column_config={"creator_type":st.column_config.SelectboxColumn(options=["Needs review","Individual","Creator","Brand"]),
       "niche":st.column_config.SelectboxColumn(options=ALL_NICHES),"qualified":st.column_config.CheckboxColumn(disabled=True),
       "engagement_rate":st.column_config.NumberColumn(disabled=True),"score":st.column_config.NumberColumn(disabled=True)})
    if st.button("Save edits"):
        st.session_state.leads=normalize(edited); st.success("Edits saved.")
with tabs[3]:
    st.subheader("Qualification and export")
    if st.session_state.leads.empty: st.info("Discover or import candidates first.")
    else:
        df=qualify(st.session_state.leads,minf,maxf,minger)
        st.session_state.leads=df
        a,b,c=st.columns(3)
        a.metric("Candidates",len(df)); b.metric("Qualified",int(df.qualified.sum())); c.metric("Target",target)
        st.dataframe(df.sort_values(["qualified","score"],ascending=[False,False]),use_container_width=True)
        qualified=df[df.qualified]
        st.download_button("Export qualified leads CSV",qualified.to_csv(index=False).encode("utf-8-sig"),"qualified_influencer_leads.csv","text/csv",disabled=qualified.empty)
        st.download_button("Export all candidates CSV",df.to_csv(index=False).encode("utf-8-sig"),"all_influencer_candidates.csv","text/csv")
        st.caption("Hard filters: 10k–100k default follower band, engagement strictly above 3%, at least 5 recent posts sampled, niche and audience geography confirmed, public business email with source URL, individual creator confirmed, and evidence of a monetized offer. Adjust follower/ER settings in the sidebar.")
with tabs[4]:
    st.subheader("Niche library from your prospecting PDF")
    st.caption("The three pillars and sub-niches below follow your uploaded 'Prospecting Niches To Get You Started' PDF.")
    for pillar,groups in NICHES.items():
        with st.expander(pillar,expanded=False):
            for group,items in groups.items():
                st.markdown("**"+group+"**")
                st.write(", ".join(items))

st.divider()
st.caption("Privacy and responsible use: collect only public professional contact details relevant to creator business inquiries; record source URLs; respect robots.txt for website checks; do not access private accounts, login-only data, DMs, or bypass access controls. Before outreach, check the marketing, privacy and platform rules that apply to you and the recipient.")
