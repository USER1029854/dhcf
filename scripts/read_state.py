import sys,json,time; sys.path.insert(0,'scripts'); import eslib
from eth_utils import keccak
def sel(s): return "0x"+keccak(text=s)[:4].hex()
def call(to,data,dec="uint"):
    r=eslib.eth_call(to,data,1); time.sleep(0.34)
    v=r.get("result") if isinstance(r,dict) else None
    if not v or not v.startswith("0x") or v=="0x": return None
    if dec=="uint": return int(v,16)
    if dec=="addr": return "0x"+v[-40:]
    if dec=="bool": return bool(int(v,16))
    if dec=="raw": return v
    return v
def u(to,fn,*args):
    d=sel(fn)
    for a in args: d+=a[2:].rjust(64,"0") if isinstance(a,str) and a.startswith("0x") else hex(a)[2:].rjust(64,"0")
    return call(to,d,"uint")
def ethbal(a):
    import requests
    j=requests.get(eslib.V2,params={"chainid":1,"module":"proxy","action":"eth_getBalance","address":a,"tag":"latest","apikey":eslib.ETHERSCAN_KEY},timeout=30).json()
    time.sleep(0.34)
    try: return int(j["result"],16)
    except: return None

ETH="0x0000000000000000000000000000000000000000"
WBTC="0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599"
A={"ActivePool":"0x77E034c8A1392d99a2C776A6C1593866fEE36a33",
   "DefaultPool":"0xC1f785B74a01dd9FAc0dE6070bC583fe9eaC7Ab5",
   "CollSurplusPool":"0xA622c3bdBFBE749B1984bc127bFB500e196F594b",
   "SP_ETH":"0x6a9f9d6f5d672a9784c5e560a9648de6cbe2c548",
   "SP_WBTC":"0x04556d845f12ff7d8ff04a37f40387dd1b454c4b"}
PARAMS="0x6f9990b242873d7396511f2630412a3fcecacc42"
PF="0x09ab3c0ce6cb41c13343879a667a6bdad65ee9da"
DCHF="0x045da4bFe02B320f4403674B3b7d121737727A36"
MON="0x1ea48b9965bb5086f3b468e50ed93888a661fc17"
CI="0x0fa46e8cbceff8468db2ec2fd77731d8a11d3d86"
MS="0x8bc3702c35d33e5df7cb0f06cb72a0c34ae0c56f"
def wbtcbal(a): return u(WBTC,"balanceOf(address)",a)
def dchfbal(a): return u(DCHF,"balanceOf(address)",a)

state={"config":{},"balances":{},"oracle":{},"issuance":{},"tokens":{},"staking":{}}
# ---- per-asset config ----
E18=10**18
for lbl,asset in [("ETH",ETH),("WBTC",WBTC)]:
    c={}
    for fn in ["MCR(address)","CCR(address)","MIN_NET_DEBT(address)","PERCENT_DIVISOR(address)",
               "BORROWING_FEE_FLOOR(address)","MAX_BORROWING_FEE(address)","REDEMPTION_FEE_FLOOR(address)",
               "DCHF_GAS_COMPENSATION(address)","redemptionBlock(address)"]:
        c[fn.split("(")[0]] = u(PARAMS,fn,asset)
    state["config"][lbl]=c
state["config"]["DECIMAL_PRECISION"]=u(PARAMS,"DECIMAL_PRECISION()")
state["config"]["REDEMPTION_BLOCK_DAY"]=u(PARAMS,"REDEMPTION_BLOCK_DAY()")
# ---- balances vs internal accounting ----
b={}
b["ActivePool"]={"eth_actual":ethbal(A["ActivePool"]),"wbtc_actual":wbtcbal(A["ActivePool"]),
  "assetBal_ETH":u(A["ActivePool"],"getAssetBalance(address)",ETH),"assetBal_WBTC":u(A["ActivePool"],"getAssetBalance(address)",WBTC),
  "DCHFDebt_ETH":u(A["ActivePool"],"getDCHFDebt(address)",ETH),"DCHFDebt_WBTC":u(A["ActivePool"],"getDCHFDebt(address)",WBTC)}
b["DefaultPool"]={"eth_actual":ethbal(A["DefaultPool"]),"wbtc_actual":wbtcbal(A["DefaultPool"]),
  "assetBal_ETH":u(A["DefaultPool"],"getAssetBalance(address)",ETH),"assetBal_WBTC":u(A["DefaultPool"],"getAssetBalance(address)",WBTC),
  "DCHFDebt_ETH":u(A["DefaultPool"],"getDCHFDebt(address)",ETH),"DCHFDebt_WBTC":u(A["DefaultPool"],"getDCHFDebt(address)",WBTC)}
b["CollSurplusPool"]={"eth_actual":ethbal(A["CollSurplusPool"]),"wbtc_actual":wbtcbal(A["CollSurplusPool"]),
  "assetBal_ETH":u(A["CollSurplusPool"],"getAssetBalance(address)",ETH),"assetBal_WBTC":u(A["CollSurplusPool"],"getAssetBalance(address)",WBTC)}
b["SP_ETH"]={"eth_actual":ethbal(A["SP_ETH"]),"assetBalance":u(A["SP_ETH"],"getAssetBalance()"),"totalDCHFDeposits":u(A["SP_ETH"],"getTotalDCHFDeposits()")}
b["SP_WBTC"]={"wbtc_actual":wbtcbal(A["SP_WBTC"]),"assetBalance":u(A["SP_WBTC"],"getAssetBalance()"),"totalDCHFDeposits":u(A["SP_WBTC"],"getTotalDCHFDeposits()")}
state["balances"]=b
# ---- tokens ----
state["tokens"]["DCHF_totalSupply"]=u(DCHF,"totalSupply()")
state["tokens"]["MON_totalSupply"]=u(MON,"totalSupply()")
state["tokens"]["MON_treasury"]=call(MON,sel("treasury()"),"addr")
# ---- oracle ----
o={"status":u(PF,"status()"),"TIMEOUT":u(PF,"TIMEOUT()"),
   "MAX_PRICE_DEVIATION_FROM_PREVIOUS_ROUND":u(PF,"MAX_PRICE_DEVIATION_FROM_PREVIOUS_ROUND()"),
   "MAX_PRICE_DIFFERENCE_BETWEEN_ORACLES":u(PF,"MAX_PRICE_DIFFERENCE_BETWEEN_ORACLES()")}
for lbl,asset in [("ETH",ETH),("WBTC",WBTC)]:
    o[f"lastGoodPrice_{lbl}"]=u(PF,"lastGoodPrice(address)",asset)
    o[f"lastGoodIndex_{lbl}"]=u(PF,"lastGoodIndex(address)",asset)
# chainlink freshness
for lbl,agg in [("ETHUSD","0x5f4ec3df9cbd43714fe2740f5e3616155c5b8419"),
                ("BTCUSD","0xf4030086522a5beea4988f8ca5b36dbc97bee88c"),
                ("CHFUSD","0x449d117117838ffa61263b61da6301aa2a88b13a")]:
    r=eslib.eth_call(agg,sel("latestRoundData()"),1); time.sleep(0.34)
    v=r.get("result")
    if v and len(v)>=2+5*64:
        vv=v[2:]
        ans=int(vv[64:128],16); updated=int(vv[192:256],16)
        o[f"chainlink_{lbl}"]={"answer":ans,"updatedAt":updated}
state["oracle"]=o
# ---- issuance ----
iss={"monToken":call(CI,sel("monToken()"),"addr"),"CI_MON_balance":u(MON,"balanceOf(address)",CI)}
for lbl,sp in [("SP_ETH",A["SP_ETH"]),("SP_WBTC",A["SP_WBTC"])]:
    iss[f"MONSupplyCap_{lbl}"]=u(CI,"MONSupplyCaps(address)",sp)
    iss[f"totalMONIssued_{lbl}"]=u(CI,"totalMONIssued(address)",sp)
    iss[f"monDistributionsByPool_{lbl}"]=u(CI,"monDistributionsByPool(address)",sp)
state["issuance"]=iss
# ---- staking ----
state["staking"]["paused"]=call(MS,sel("paused()"),"bool")
state["staking"]["MON_staked_in_contract"]=u(MON,"balanceOf(address)",MS)
json.dump(state,open("state/live_state.json","w"),indent=2)
print("WROTE state/live_state.json")
