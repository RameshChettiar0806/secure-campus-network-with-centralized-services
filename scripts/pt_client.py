import urllib.request,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
def normalize(x):
    if isinstance(x,dict):
        if 'length' in x and all(k=='length' or k.isdigit() for k in x):
            return [normalize(x[str(i)]) for i in range(x['length'])]
        return {k:normalize(v) for k,v in x.items()}
    if isinstance(x,list):return [normalize(v) for v in x]
    return x
def call(name,args=None):
    req=urllib.request.Request('http://127.0.0.1:7532/call',json.dumps({'name':name,'arguments':args or {}}).encode(),{'Content-Type':'application/json'})
    data=json.load(urllib.request.urlopen(req,timeout=60))
    while isinstance(data,dict) and 'code' in data and 'result' in data:data=data['result']
    return normalize(data)
if __name__=='__main__':
    result=call(sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv)>2 else {})
    text=json.dumps(result,indent=2)
    if len(sys.argv)>3:(BASE/'evidence'/sys.argv[3]).write_text(text,encoding='utf-8')
    print(text)
