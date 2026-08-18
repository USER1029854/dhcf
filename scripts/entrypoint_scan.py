import re, os, json, subprocess

# canonical file for each unique project contract
FILES = {
 "ActivePool":"contracts/verified/ActivePool/contracts/ActivePool.sol",
 "DefaultPool":"contracts/verified/DefaultPool/contracts/DefaultPool.sol",
 "CollSurplusPool":"contracts/verified/CollSurplusPool/contracts/CollSurplusPool.sol",
 "StabilityPool":"contracts/verified/StabilityPool_WBTC/contracts/StabilityPool.sol",
 "StabilityPoolManager":"contracts/verified/StabilityPoolManager/contracts/StabilityPoolManager.sol",
 "TroveManager":"contracts/verified/TroveManagerHelpers/contracts/TroveManager.sol",
 "TroveManagerHelpers":"contracts/verified/TroveManagerHelpers/contracts/TroveManagerHelpers.sol",
 "BorrowerOperations":"contracts/verified/BorrowerOperations/contracts/BorrowerOperations.sol",
 "SortedTroves":"contracts/verified/SortedTroves/contracts/SortedTroves.sol",
 "DCHFToken":"contracts/verified/DCHFToken/contracts/DCHFToken.sol",
 "DfrancParameters":"contracts/verified/DfrancParameters/contracts/DfrancParameters.sol",
 "AdminContract":"contracts/verified/AdminContract/contracts/AdminContract.sol",
 "PriceFeed":"contracts/verified/PriceFeed/contracts/PriceFeed.sol",
 "CommunityIssuance":"contracts/verified/CommunityIssuance/contracts/MON/CommunityIssuance.sol",
 "MONStaking":"contracts/verified/MONStaking/contracts/MON/MONStaking.sol",
 "MONToken":"contracts/verified/MONToken/contracts/MON/MONToken.sol",
 "ERC20Permit":"contracts/verified/DCHFToken/contracts/Dependencies/ERC20Permit.sol",
 "DfrancBase":"contracts/verified/BorrowerOperations/contracts/Dependencies/DfrancBase.sol",
 "SafetyTransfer":"contracts/verified/DefaultPool/contracts/Dependencies/SafetyTransfer.sol",
 "DfrancMath":"contracts/verified/CommunityIssuance/contracts/Dependencies/DfrancMath.sol",
 "Initializable":"contracts/verified/CommunityIssuance/contracts/Dependencies/Initializable.sol",
 "CheckContract":"contracts/verified/CommunityIssuance/contracts/Dependencies/CheckContract.sol",
}

# function signature regex spanning multiple lines
fnre = re.compile(r'\bfunction\s+([A-Za-z0-9_]+)\s*\(', re.M)
out={}
for name, path in FILES.items():
    if not os.path.exists(path):
        out[name]=[{"err":"missing"}]; continue
    src=open(path).read()
    lines=src.split('\n')
    fns=[]
    for m in fnre.finditer(src):
        fname=m.group(1)
        start=m.start()
        lineno=src[:start].count('\n')+1
        # capture header up to the opening brace or semicolon at depth 0
        i=m.end()-1; depth=0; header=[]
        while i < len(src):
            c=src[i]; header.append(c)
            if c=='(': depth+=1
            elif c==')':
                depth-=1
                if depth==0:
                    # continue to '{' or ';'
                    j=i+1
                    while j<len(src) and src[j] not in '{;':
                        header.append(src[j]); j+=1
                    header.append(src[j] if j<len(src) else '')
                    break
            i+=1
        h=''.join(header)
        h=re.sub(r'\s+',' ',h)
        vis='internal'
        if re.search(r'\bexternal\b',h): vis='external'
        elif re.search(r'\bpublic\b',h): vis='public'
        elif re.search(r'\bprivate\b',h): vis='private'
        elif re.search(r'\binternal\b',h): vis='internal'
        else:
            # no explicit visibility: modifiers/constructors, or interface decl
            vis='(none)'
        mods=[]
        for mod in ['onlyOwner','isController','initializer','nonReentrant','whenNotPaused','override','view','pure','payable','virtual']:
            if re.search(r'\b'+mod+r'\b',h): mods.append(mod)
        # custom modifiers: words after ) that aren't keywords
        tail=h.split(')',1)[1] if ')' in h else ''
        known={'external','public','internal','private','view','pure','payable','override','virtual','returns','memory','calldata','storage'}
        custom=[w for w in re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', tail.split('returns')[0]) if w not in known]
        fns.append({"fn":fname,"line":lineno,"vis":vis,"mods":sorted(set(mods+custom))})
    out[name]=fns

tot_ext=0
for name,fns in out.items():
    ext=[f for f in fns if f["vis"] in ("external","public")]
    tot_ext+=len(ext)
    print(f"\n########## {name}  ({len(ext)} external/public of {len(fns)} fns) ##########")
    for f in ext:
        print(f"  L{f['line']:<5} {f['vis']:<8} {f['fn']:<42} mods={','.join(f['mods']) or '-'}")
print(f"\n=== TOTAL external/public functions across project contracts: {tot_ext} ===")
json.dump(out, open('/tmp/entrypoints.json','w'), indent=1)
