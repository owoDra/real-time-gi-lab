#!/usr/bin/env python3
"""049 development summary: first warm-passing configuration and its cost per role family."""
import re
import sys
from collections import defaultdict

ROW=re.compile(r'^(\S+)\s+(\S+)\s+k=\s*(\d+) n=\s*(\d+) us=\s*([\d.]+) warm_pass=(True|False)')


def main(paths):
    rows=defaultdict(list)
    for p in paths:
        for line in open(p):
            m=ROW.match(line)
            if m:seq,role,k,n,us,ok=m.groups();rows[(seq,role)].append((int(k),int(n),float(us),ok=='True'))
    seqs=sorted({s for s,_ in rows});roles=sorted({r for _,r in rows})
    print('sequence'.ljust(15)+''.join(r.rjust(18) for r in roles))
    for s in seqs:
        cells=[]
        for r in roles:
            ok=[x for x in rows.get((s,r),[]) if x[3]]
            cells.append((f'k{min(ok)[0]}:{min(ok,key=lambda x:x[2])[2]/1000:.2f}ms' if ok else ('FAIL' if rows.get((s,r)) else '-')).rjust(18))
        print(s.ljust(15)+''.join(cells))


if __name__=='__main__':main(sys.argv[1:])
