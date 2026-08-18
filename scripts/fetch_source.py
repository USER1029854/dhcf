"""Fetch a contract's verified source from Etherscan V2 and save the file tree.
Usage: fetch_source.py <address> <label> <dest_dir> [chainid]
Prints JSON metadata to stdout.
"""
import json, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eslib

def sanitize(p):
    p = p.replace("\\", "/").lstrip("/")
    parts = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            continue
        parts.append(re.sub(r'[^A-Za-z0-9._@\-+]', '_', seg))
    return "/".join(parts) if parts else "Contract.sol"

def unpack_sources(src, contract_name):
    """Return dict {relpath: content}."""
    src = src if src is not None else ""
    out = {}
    s = src.strip()
    # double-brace standard json
    if s.startswith("{{") and s.endswith("}}"):
        try:
            obj = json.loads(s[1:-1])
            sources = obj.get("sources", {})
            for path, v in sources.items():
                out[sanitize(path)] = v.get("content", "") if isinstance(v, dict) else str(v)
            return out
        except Exception as e:
            pass
    # single-brace: could be {path:{content}} or full json input
    if s.startswith("{") and s.endswith("}"):
        try:
            obj = json.loads(s)
            if "sources" in obj and isinstance(obj["sources"], dict):
                for path, v in obj["sources"].items():
                    out[sanitize(path)] = v.get("content","") if isinstance(v,dict) else str(v)
                return out
            # else maybe {path: {content}}
            looks_multi = all(isinstance(v, dict) and "content" in v for v in obj.values()) and len(obj)>0
            if looks_multi:
                for path, v in obj.items():
                    out[sanitize(path)] = v.get("content","")
                return out
        except Exception:
            pass
    # plain single source
    name = contract_name or "Contract"
    out[f"{name}.sol"] = src
    return out

def main():
    address = sys.argv[1]
    label = sys.argv[2]
    dest = sys.argv[3]
    chainid = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    r = eslib.getsource(address, chainid)
    meta = {"address": address, "label": label, "chainid": chainid}
    if not r:
        meta["error"] = "no result"
        print(json.dumps(meta)); return
    name = r.get("ContractName","")
    src = r.get("SourceCode","")
    meta.update({
        "ContractName": name,
        "CompilerVersion": r.get("CompilerVersion",""),
        "OptimizationUsed": r.get("OptimizationUsed",""),
        "Runs": r.get("Runs",""),
        "EVMVersion": r.get("EVMVersion",""),
        "Proxy": r.get("Proxy","0"),
        "Implementation": r.get("Implementation","") or "",
        "ConstructorArguments": r.get("ConstructorArguments",""),
        "LicenseType": r.get("LicenseType",""),
        "verified": bool(src and src.strip()),
    })
    if not (src and src.strip()):
        meta["verified"] = False
        print(json.dumps(meta)); return
    files = unpack_sources(src, name)
    base = os.path.join(dest, f"{label}")
    written = []
    for path, content in files.items():
        full = os.path.join(base, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(content)
        written.append(os.path.relpath(full, "/home/user/dhcf"))
    # save ABI too
    abi = r.get("ABI","")
    if abi and abi != "Contract source code not verified":
        with open(os.path.join(base, "_abi.json"), "w") as f:
            f.write(abi)
    meta["files"] = written
    meta["nfiles"] = len(written)
    meta["dir"] = os.path.relpath(base, "/home/user/dhcf")
    print(json.dumps(meta))

if __name__ == "__main__":
    main()
