"""Etherscan V2 + Blockscout helpers for the DCHF audit repo."""
import json, os, time, sys, urllib.parse
import requests

ETHERSCAN_KEY = os.environ.get("ETHERSCAN_KEY", "R6PYYNEX4CNFAXX4YX3K8W4NXSBGGG4QGJ")
BLOCKSCOUT_KEY = os.environ.get("BLOCKSCOUT_KEY", "proapi_CXlzRYJyLN9T7Uxugw1KTDV51rjzCrMXVSKTfyf5Tn5CUzrqEWYCSWcXQUiKfmNB_fNH9s")
V2 = "https://api.etherscan.io/v2/api"
S = requests.Session()

def _get(params, retries=5):
    for i in range(retries):
        try:
            r = S.get(V2, params=params, timeout=40)
            j = r.json()
            return j
        except Exception as e:
            if i == retries-1:
                raise
            time.sleep(1.5*(i+1))
    return None

def _rl(v):
    """True if a proxy result is a transient rate-limit / error string, not hex."""
    return isinstance(v,str) and not v.startswith("0x")

def _proxy_retry(fn,*a,**k):
    import time
    for i in range(6):
        r=fn(*a,**k)
        if isinstance(r,str) and _rl(r):
            time.sleep(0.7*(i+1)); continue
        return r
    return r

def getsource(address, chainid=1):
    j = _get({"chainid":chainid,"module":"contract","action":"getsourcecode",
              "address":address,"apikey":ETHERSCAN_KEY})
    time.sleep(0.22)
    return j["result"][0] if j and j.get("result") else None

def getabi(address, chainid=1):
    j = _get({"chainid":chainid,"module":"contract","action":"getabi",
              "address":address,"apikey":ETHERSCAN_KEY})
    time.sleep(0.22)
    return j.get("result") if j else None

def _getcode_raw(address, chainid=1):
    j = _get({"chainid":chainid,"module":"proxy","action":"eth_getCode",
              "address":address,"tag":"latest","apikey":ETHERSCAN_KEY})
    time.sleep(0.28)
    return j.get("result") if j else None

def getcode(address, chainid=1):
    return _proxy_retry(_getcode_raw, address, chainid)

def eth_call(to, data, chainid=1, frm="0x000000000000000000000000000000000000dEaD", value=None):
    p = {"chainid":chainid,"module":"proxy","action":"eth_call","to":to,
         "data":data,"tag":"latest","from":frm,"apikey":ETHERSCAN_KEY}
    j = _get(p)
    time.sleep(0.22)
    return j

def get_storage(address, slot, chainid=1):
    j = _get({"chainid":chainid,"module":"proxy","action":"eth_getStorageAt",
              "address":address,"position":slot,"tag":"latest","apikey":ETHERSCAN_KEY})
    time.sleep(0.22)
    return j.get("result") if j else None

def get_balance(address, chainid=1):
    j = _get({"chainid":chainid,"module":"account","action":"balance",
              "address":address,"tag":"latest","apikey":ETHERSCAN_KEY})
    time.sleep(0.22)
    return j.get("result") if j else None

def creation(address, chainid=1):
    j = _get({"chainid":chainid,"module":"contract","action":"getcontractcreation",
              "contractaddresses":address,"apikey":ETHERSCAN_KEY})
    time.sleep(0.22)
    return j["result"][0] if j and j.get("result") else None

if __name__ == "__main__":
    print(json.dumps(getsource(sys.argv[1]), indent=2)[:500])
