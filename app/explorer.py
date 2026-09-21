"""Discovery Engine Explorer. Run from the project root:  PYTHONPATH=src streamlit run app/explorer.py"""
import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from engine import cluster, findings, store  # noqa: E402

if not cluster.DB_PATH.exists():  # hosted copy: no local database, use the slim snapshot from `export-demo`
    cluster.DB_PATH = ROOT / "demo" / "engine.db"

st.set_page_config(page_title="Photo Retrieval Discovery Engine", layout="wide")


@st.cache_data(show_spinner="Loading the database")
def load():
    db = store.connect(cluster.DB_PATH)
    ms = cluster.metrics(db)
    by_item = {r["item_id"]: (r["cluster_id"], r["name"]) for r in db.execute(
        "SELECT ci.item_id, c.cluster_id, c.name FROM cluster_items ci JOIN clusters c USING(cluster_id)")}
    url = {r["item_id"]: r["url"] for r in db.execute("SELECT item_id, url FROM raw_items")}
    rows = []
    for i in cluster.load(db):
        cid, cname = by_item.get(i["item_id"], (None, "(none)"))
        rows.append({"item_id": i["item_id"], "source": i["source"], "product": i["product_norm"], "failure_mode": i["failure_mode"],
                     "group": i["group"], "outcome": i["outcome"], "severity": i["severity"], "photo_type": i["photo_type"],
                     "cluster_id": cid, "cluster": cname, "thread": i["thread"], "date": (i["created_at"] or "")[:10],
                     "description": i["rec"]["target_description"], "workaround": i["rec"].get("workaround"),
                     "search_pattern": i["rec"]["search_pattern"], "queries": ", ".join(i["rec"]["queries_tried"]),
                     "text": i["text"], "url": url[i["item_id"]], "extraction": json.dumps(i["rec"], indent=1)})
    return {"metrics": ms, "items": pd.DataFrame(rows), "funnel": pd.DataFrame(findings.funnel(db)),
            "remember": cluster.remember_forget(db), "hyp": findings.hypotheses(db), "behaviour": findings.search_behaviour(db)}


D = load()
items, ms = D["items"], D["metrics"]
ranked = [m for m in ms if m["score"] is not None]

st.title("Photo Retrieval Discovery Engine")
st.warning("Counts are **mentions in a sample of public reviews and forum posts**, not how many people have a problem. Google Photos is about 60% of the "
           "failures, extraction agreed with hand labels about 75% of the time, and one thread can supply many items. Read the limitations in docs/report.md.")

# A selector, not st.tabs: tabs jump back to the first one whenever a widget inside them reruns the page.
VIEWS = ["Insights", "Overview", "Problem clusters", "Remember and forget", "Compare", "Hypotheses", "Items"]
view = st.segmented_control("View", VIEWS, default="Insights", key="view", label_visibility="collapsed") or "Insights"

def insight_card(i):
    with st.container(border=True):
        st.markdown(f"#### {i['headline']}")
        if i["so_what"]:
            st.markdown(f"**Interpretation (a hypothesis to test, not a finding).** {i['so_what']}")
        color = {"high": "green", "medium": "orange", "low": "red"}[i["confidence"]]
        st.markdown(f":{color}[**Confidence: {i['confidence']}**] ({i['n']} items, {i['sources']} sources)"
                    + ("" if i["written_by_llm"] else "  ·  plain text" + ("" if i.get("plain_text") else " (the write-up failed the checks)")))
        if i["caveat"]:
            st.caption(f"Caveat: {i['caveat']}")
        with st.expander("Evidence"):
            st.json(i["facts"])
            for q in i["quotes"]:
                st.markdown(f"> {q['quote']}  \n> *{q['source']}* - [source]({q['url']})")


if view == "Insights":
    ins_path = ROOT / "eval" / "results" / "insights.json"
    if not ins_path.exists():
        st.info("No insights yet. Run `PYTHONPATH=src python -m engine.cli insights`.")
    else:
        data = json.loads(ins_path.read_text(encoding="utf8"))["insights"]
        st.markdown("### What the data says")
        st.caption("Written by the engine from measured contrasts. Every number is checked against the data behind it, confidence is set from sample size and "
                   "source spread, and each card links to its evidence. The other views hold the underlying tables.")
        for i in [x for x in data if not x["weak"]]:
            insight_card(i)
        with st.expander("Weaker signals and blind spots"):
            for i in [x for x in data if x["weak"]]:
                insight_card(i)

if view == "Overview":
    f = D["funnel"]
    c = st.columns(4)
    c[0].metric("Raw items collected", int(f["items"].sum()))
    c[1].metric("Classified as about finding photos", int(f["relevant"].sum()))
    c[2].metric("Extracted", int(f["extracted"].sum()))
    c[3].metric("Real retrieval failures", int(f["failures"].sum()))
    st.subheader("Ranked problem clusters")
    table = pd.DataFrame([{"#": m["id"], "score": m["score"], "cluster": m["name"], "items": m["items"], "threads": m["threads"],
                           "sources": len(m["sources"]), "not found %": round(100 * m["not_found_rate"]), "workaround %": round(100 * m["workaround_rate"]),
                           "recent %": round(100 * m["recent_share"])} for m in ms])
    st.dataframe(table, hide_index=True, width="stretch")
    st.caption("Click a column header to sort. Clusters marked [residual] were too mixed to rank. Cluster 5 is a borderline pass in the human check.")
    st.altair_chart(alt.Chart(pd.DataFrame([{"cluster": m["name"], "threads": m["threads"]} for m in ranked])).mark_bar()
                    .encode(x="threads:Q", y=alt.Y("cluster:N", sort="-x", title=None)), width="stretch")
    with st.expander("How the score is computed"):
        st.write("Five measures, each scaled 0 to 1 across the ranked clusters, then weighted: "
                 + ", ".join(f"**{k}** {v:.0%}" for k, v in cluster.WEIGHTS.items())
                 + ". The weights are a judgment, not a measurement. Order under other weightings:")
        st.json(cluster.sensitivity(ms))
    st.subheader("Where the items came from")
    st.dataframe(f.rename(columns={"items": "raw items", "passed": "kept by keyword filter", "classified": "classified by Gemini",
                                   "relevant": "called retrieval", "extracted": "extracted", "failures": "retrieval failures"}),
                 hide_index=True, width="stretch")

if view == "Problem clusters":
    pick = st.selectbox("Cluster", [m["id"] for m in ms], format_func=lambda i: next(f"#{m['id']}  {m['name']}" for m in ms if m["id"] == i))
    m = next(m for m in ms if m["id"] == pick)
    st.markdown(f"**{m['name']}**  \n{m['definition']}")
    c = st.columns(5)
    c[0].metric("Items", m["items"])
    c[1].metric("Threads", m["threads"])
    c[2].metric("Not found", f"{m['not_found_rate']:.0%}")
    c[3].metric("Workaround", f"{m['workaround_rate']:.0%}")
    c[4].metric("Score", "n/a" if m["score"] is None else m["score"])
    left, right = st.columns(2)
    left.write("Sources")
    left.bar_chart(pd.Series(m["sources"]))
    right.write("Products")
    right.bar_chart(pd.Series(m["products"]))
    st.write("Quotes (open the link to read the original post)")
    for q in m["quotes"]:
        row = items[items["item_id"] == q["item_id"]].iloc[0]
        st.markdown(f"> {q['quote']}  \n> *{q['source']}* - [source]({row['url']})")
    st.write("Items in this cluster")
    st.dataframe(items[items["cluster_id"] == pick][["source", "product", "date", "failure_mode", "outcome", "description", "url"]],
                 hide_index=True, width="stretch", column_config={"url": st.column_config.LinkColumn("link")})

if view == "Remember and forget":
    st.info("What people say they know about a photo they are looking for. Counts are small, and most 'appearance' cues are example search words, not memories of one specific photo.")
    rf = D["remember"]["retrieval_failures"]
    cue_df = pd.DataFrame([{"cue": k, "status": s, "count": n} for k, v in rf.items() for s, n in v.items() if n])
    st.altair_chart(alt.Chart(cue_df).mark_bar().encode(x="count:Q", y=alt.Y("cue:N", sort="-x"), color="status:N"), width="stretch")
    st.write("The three cues the extractor marked as forgotten (all about *when*). On reading: one is a hypothetical example query, one is indirect, and only one is a clear first-person statement.")
    forgotten = store.connect(cluster.DB_PATH).execute(
        "SELECT m.cue_value, m.quote, x.source, x.url FROM cue_mentions m JOIN raw_items x USING(item_id) WHERE m.status='forgotten'").fetchall()
    st.dataframe(pd.DataFrame([dict(r) for r in forgotten]), hide_index=True, width="stretch",
                 column_config={"url": st.column_config.LinkColumn("link")})
    st.subheader("How people search")
    st.bar_chart(pd.Series(D["behaviour"]))
    st.caption("'not_stated' dominates: most posts do not say how the person searched.")
    q = items[items["queries"] != ""][["source", "queries", "search_pattern", "url"]]
    st.write(f"Queries people say they typed ({len(q)} posts):")
    st.dataframe(q, hide_index=True, width="stretch", column_config={"url": st.column_config.LinkColumn("link")})

if view == "Compare":
    st.write("How the retrieval failures spread across products and sources. Small cells are noise; treat non-Google products with care.")
    axis = st.radio("Compare clusters by", ["product", "source"], horizontal=True)
    cells = items[items["cluster_id"].notna()].groupby([axis, "cluster"]).size().reset_index(name="items")
    n_rows = cells["cluster"].nunique()
    st.altair_chart(alt.Chart(cells).mark_rect().encode(
        x=alt.X(f"{axis}:N", title=None, axis=alt.Axis(labelAngle=-35, labelOverlap=False)),
        y=alt.Y("cluster:N", title=None, axis=alt.Axis(labelLimit=420, labelOverlap=False)),
        color=alt.Color("items:Q", scale=alt.Scale(scheme="blues")), tooltip=[axis, "cluster", "items"]).properties(height=30 * n_rows),
        width="stretch")
    st.dataframe(items.groupby("product").agg(items=("item_id", "count"), threads=("thread", "nunique"),
                                              not_found=("outcome", lambda s: round(100 * (s == "not_found").mean()))).reset_index(),
                 hide_index=True, width="stretch")

if view == "Hypotheses":
    st.write("The seven hypotheses written down before the analysis (docs/context.md, section 10), with what the data says.")
    h = D["hyp"]
    text = {1: "Most retrieval failures for old photos come from missing or wrong metadata, not bad search.",
            2: "Users remember who and event far better than when and where.",
            3: "Screenshots and functional images are a distinct retrieval problem.",
            4: "Post-LLM search complaints are about loss of control and predictability more than accuracy.",
            5: "Migration is a disproportionate source of unrecoverable old-photo failures.",
            6: "Reddit users describe workarounds that reveal unmet needs the app-store reviews only hint at.",
            7: "Many 'retrieval' complaints are really account, sync or deletion problems."}
    for k in range(1, 8):
        verdict, why = findings.VERDICTS[k]
        with st.expander(f"H{k}. {text[k]}  -  {verdict}"):
            st.write(why)
            st.json(h[k])

if view == "Items":
    fcol = st.columns(4)
    src = fcol[0].multiselect("Source", sorted(items["source"].unique()))
    prod = fcol[1].multiselect("Product", sorted(items["product"].unique()))
    clus = fcol[2].multiselect("Cluster", sorted(items["cluster"].unique()))
    mode = fcol[3].multiselect("Failure mode", sorted(items["failure_mode"].unique()))
    term = st.text_input("Search the post text")
    view = items
    for col, sel in (("source", src), ("product", prod), ("cluster", clus), ("failure_mode", mode)):
        if sel:
            view = view[view[col].isin(sel)]
    if term:
        view = view[view["text"].str.contains(term, case=False, regex=False)]
    st.write(f"{len(view)} item{'' if len(view) == 1 else 's'}")
    st.dataframe(view[["source", "product", "date", "cluster", "failure_mode", "outcome", "description", "url"]].head(500), hide_index=True,
                 width="stretch", column_config={"url": st.column_config.LinkColumn("link")})
    if len(view):
        i = st.selectbox("Open an item", view["item_id"].head(200), format_func=lambda x: f"{x}  -  {view.set_index('item_id').loc[x, 'description'][:70]}")
        row = items[items["item_id"] == i].iloc[0]
        st.markdown(f"[Open the original post]({row['url']})")
        st.text(row["text"][:3000])
        st.code(row["extraction"], language="json")
