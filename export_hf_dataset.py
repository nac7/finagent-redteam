"""Export the deterministic FinAgent Red-Team suite (seed=0, per_threat=6) to a
HuggingFace-ready JSONL. Serializes only reproducible, non-callable fields plus a
rendering of each scenario's initial untrusted content (the injection surface)."""
import json, sys, os
from dataclasses import asdict
from finagent_redteam.scenarios import generate_scenarios
from finagent_redteam.scenarios.schema import THREAT_CATEGORIES

OUT = sys.argv[1]

def goal(g):
    if g is None:
        return None
    return {"kind": g.kind, "params": g.params}

def untrusted_surface(world):
    items = []
    for e in world.inbox:
        if getattr(e, "untrusted", False):
            items.append({"channel": "email", "source": e.sender, "title": e.subject, "body": e.body})
    for coll, chan in ((world.documents, "document"), (world.tickets, "ticket"), (world.calendar, "calendar")):
        for it in coll:
            if getattr(it, "untrusted", True):
                items.append({"channel": chan, "source": it.source, "title": it.title, "body": it.body})
    return items

rows, cats = [], {}
for sc in generate_scenarios(seed=0, per_threat=6):
    world = sc.world_factory()
    cats[sc.category] = cats.get(sc.category, 0) + 1
    rows.append({
        "id": sc.id,
        "category": sc.category,
        "category_description": THREAT_CATEGORIES.get(sc.category, ""),
        "benign": sc.benign,
        "description": sc.description,
        "user_task": sc.user_task,
        "attack_goal": goal(sc.attack_goal),
        "success_goal": goal(sc.success_goal),
        "strata": sc.strata,
        "reference_plan": sc.reference_plan,
        "injection_surface": untrusted_surface(world),
        "allowlisted_payees": sorted(p.name for p in world.payees.values() if p.allowlisted),
        "sanctions_watchlist": sorted(world.sanctions_watchlist),
    })

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"wrote {len(rows)} scenarios -> {OUT}")
print("category counts:", json.dumps(cats, indent=None))
print("benign:", sum(1 for r in rows if r["benign"]), "attack:", sum(1 for r in rows if not r["benign"]))
print("--- sample (first attack row, trimmed) ---")
s = next(r for r in rows if not r["benign"])
s2 = dict(s);
for k in ("injection_surface",):
    if s2.get(k):
        s2[k] = [{**it, "body": it["body"][:160] + ("..." if len(it["body"]) > 160 else "")} for it in s2[k]]
print(json.dumps(s2, indent=2, ensure_ascii=False)[:1400])
