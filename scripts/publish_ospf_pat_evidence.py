"""Build the extension viewer manifest from measured, passing evidence only."""
import hashlib
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUN = BASE/'evidence/OSPF-PAT-20261102'
read = lambda name: json.loads((RUN/name).read_text(encoding='utf-8'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    ext=read('extension-summary.json')
    campus=read('after-summary.json')
    recovery=read('failure-check-summary.json')
    persistence=read('persistence-summary.json')
    inventory=read('topology-preservation.json')
    submission=read('submission.json')
    assert all(d['allPassed'] for d in [ext,campus,recovery,persistence])
    assert sha(BASE/submission['file'])==submission['sha256']
    assert inventory['networkDevices']==58 and inventory['links']==57 and inventory['all55OriginalLinksRetained']
    assert ext['externalPing']=={'passed':50,'total':50} and ext['externalHttp']=={'passed':50,'total':50}
    files=['extension-summary.json','after-summary.json','persistence-summary.json','failure-check-summary.json','topology-preservation.json','ospf-full.json','pat-translations.json','external-router-routes.json','external-pings.json','external-http.json','external-other-host-denied.json','unsolicited-wan-denied.json','pat-disabled.json','pat-disabled-state.json','pat-restored.json','ospf-disabled.json','ospf-disabled-state.json','campus-during-ospf-outage.json','ospf-restored.json','reopened-dhcp-renewal.json','reopened-ssh-denied.json','after-dns.json','http-all.json']
    paths=[RUN/name for name in files]+[BASE/'configs/R1-CAMPUS-OSPF-PAT.txt',BASE/'configs/R2-EXTERNAL.txt']
    assets=[dict(path=p.relative_to(BASE).as_posix(),sha256=sha(p)) for p in paths]
    pat=read('pat-translations.json')['translations']
    pat_lines=pat.splitlines()
    sample=[pat_lines[0]]
    for address in ['192.168.10.2','192.168.10.66','192.168.10.98']:
        row=next((line for line in pat_lines if re.search(r'\b'+re.escape(address)+r'(?=[:\s])',line)),None)
        if row:sample.append(row)
    checks=[
        {'label':'Campus gateway / central server ping','result':'50/50 clients passed each check'},
        {'label':'Campus DNS and HTTP','result':'50/50 clients passed each check'},
        {'label':'Department policy','result':'4 allowed and 5 blocked cases matched policy'},
        {'label':'External ICMP and hostname HTTP','result':'50/50 clients passed each check'},
        {'label':'PAT address sharing','result':f"{ext['patMultipleInsideAddresses']} inside-local addresses observed sharing 198.51.100.1"},
        {'label':'OSPF','result':'FULL adjacency; 203.0.113.0/24 learned dynamically'},
        {'label':'External access restrictions','result':'Other external host and unsolicited inbound ping blocked'},
        {'label':'Failure and restoration','result':'PAT and OSPF dependency demonstrated; both restored'},
        {'label':'Persistence and management','result':'DHCP renewed in all three client VLANs; 5 allowed and 3 blocked SSH checks passed'},
    ]
    manifest=dict(runId='OSPF-PAT-20261102',capturedAt=datetime.now(timezone(timedelta(hours=5,minutes=30))).isoformat(timespec='seconds'),submissionFile=submission['file'],submissionSha256=submission['sha256'],verifiedAfterReopen=True,inventory=inventory,checks=checks,evidence=assets,
        observations=dict(ospf=read('ospf-full.json')['neighbors']+'\n'+ '\n'.join(line for line in read('ospf-full.json')['routes'].splitlines() if line.startswith('O ')),
            http='http://external.campus.test\nDNS server: 192.168.10.130\nResolved external server: 203.0.113.10\n50/50 clients received the external HTTP page after reopening.',
            pat='\n'.join(sample)+f"\n\n{ext['patMultipleInsideAddresses']} distinct inside-local addresses observed in the full table.",
            policy='Student → Administration: denied\nFaculty → Students: denied\nAll client VLANs → 203.0.113.10 TCP/80 and ICMP Echo: permitted\nStudent → 203.0.113.1: denied\nExternal server → 198.51.100.1 unsolicited ICMP Echo: denied',
            recovery='PAT disabled: three departmental clients received 0/4 replies.\nPAT restored: all three clients succeeded.\nOSPF made passive on transit: external route withdrawn and external ping failed.\nCampus server ping during OSPF outage: succeeded.\nOSPF restored: FULL adjacency, learned route and external access returned.'))
    (BASE/'data/ospf-pat-extension.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    text='# OSPF / PAT extension acceptance\n\nVerified after reopening in Cisco Packet Tracer 9.0.1 on 2 November 2026 (IST).\n\n'
    text+='The existing submission now has 58 network devices and 57 links. All 55 original campus links were retained; one router, one server and two Ethernet links were added. Campus subnets and switch configurations are retained.\n\n'
    text+='| Check | Result |\n| --- | --- |\n'+''.join('| '+c['label']+' | '+c['result']+' |\n' for c in checks)
    text+='\nThe four campus service groups account for 200 client checks; external ping and HTTP add 100 client checks. The 4 permitted/5 denied campus cases and management tests are additional. These checks do not recapture the historical 2,958-case matrix.\n\n'
    text+='Saved submission SHA-256: `'+submission['sha256']+'`. The hash identifies the saved file reopened for these checks; counters and transient flows can evolve while it runs.\n\n'
    text+='Evidence: `evidence/OSPF-PAT-20261102/`. The manifest `data/ospf-pat-extension.json` lists hash-verified public evidence. `campus-before-ospf-pat.zip` in the evidence directory is the local recovery archive.\n\n'
    text+='The [walkthrough](docs/ospf-pat-extension.md) explains the addressing, CLI sequence and failure checks. The website includes an **OSPF & PAT** tab; its other sections retain the original campus capture.\n\n'
    text+='Scope: simulated external network; single-area OSPF, not multi-area or failover; HTTP and ICMP to one external server; stateless ACLs; same-VLAN traffic bypasses routed ACLs. No throughput claim is made.\n'
    (BASE/'OSPF_PAT_ACCEPTANCE.md').write_text(text,encoding='utf-8')
    print('Published measured extension manifest:',len(assets),'evidence assets; saved file hash verified')


if __name__=='__main__':build()
