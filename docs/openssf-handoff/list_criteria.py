import re, sys, yaml
class L(yaml.SafeLoader): pass
L.add_constructor('tag:yaml.org,2002:omap', lambda l,n: dict(l.construct_pairs(n, deep=True)) if False else {k: v for k, v in ((l.construct_object(k_, deep=True), l.construct_object(v_, deep=True)) for kv in n.value for k_, v_ in kv.value)})
crit = yaml.load(open(sys.argv[1]), Loader=L)
en = yaml.safe_load(open(sys.argv[2]))["en"]["criteria"]
level = sys.argv[3]
for major, minors in crit[level].items():
    for minor, items in minors.items():
        for key, c in items.items():
            if c.get("obsolete") or c.get("future"): continue
            d = en.get(level, {}).get(key, {}).get("description", "")
            d = re.sub(r"<[^>]+>", "", d).replace("\n", " ")
            flags = ("N" if c.get("na_allowed") else "") + ("U" if c.get("met_url_required") else "") + ("J" if c.get("met_justification_required") else "")
            print(f"{c['category'][:4]} {key} [{flags}] {d[:230]}")
