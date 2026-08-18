"""Probe address-returning getters on a contract via its ABI, return live wiring.
Usage: probe.py <address> <abi_path> [chainid]
"""
import json, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eslib
from eth_utils import keccak
from eth_abi import decode as abi_decode

def selector(sig):
    return "0x" + keccak(text=sig)[:4].hex()

def canon_sig(fn):
    ins = ",".join(i["type"] for i in fn.get("inputs",[]))
    return f'{fn["name"]}({ins})'

def main():
    address = sys.argv[1]
    abi_path = sys.argv[2]
    chainid = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    try:
        abi = json.load(open(abi_path))
    except Exception as e:
        print(json.dumps({"address":address,"error":f"abi load: {e}"})); return
    results = {}
    for fn in abi:
        if fn.get("type") != "function": continue
        if fn.get("stateMutability") not in ("view","pure"): continue
        if fn.get("inputs"): continue
        outs = fn.get("outputs",[])
        if len(outs) != 1: continue
        if outs[0]["type"] != "address": continue
        sig = canon_sig(fn)
        sel = selector(sig)
        r = eslib.eth_call(address, sel, chainid)
        res = r.get("result") if isinstance(r, dict) else None
        if res and res != "0x" and len(res) >= 66:
            try:
                addr = "0x"+res[-40:]
                results[fn["name"]] = addr
            except Exception:
                results[fn["name"]] = res
        else:
            results[fn["name"]] = None
    print(json.dumps({"address":address,"getters":results}, indent=2))

if __name__ == "__main__":
    main()
