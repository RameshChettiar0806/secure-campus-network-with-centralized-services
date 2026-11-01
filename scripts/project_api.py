import json,re
from pt_client import call,BASE
def js(code):
 r=call('getDeviceInfo',{'deviceName':'PROJECT:'+code})
 if not r.get('success'):raise RuntimeError(r)
 return r.get('result')
def save(name,data):
 (BASE/'evidence'/name).write_text(json.dumps(data,indent=2),encoding='utf-8')
if __name__=='__main__':
 code='var out={}; var net=ipc.network(); for(var i=0;i<net.getDeviceCount();i++){var d=net.getDeviceAt(i); if(d.getType()===0 || d.getType()===1){out[d.getName()]=d.enterCommand("show running-config","enable").second;} else if(d.getType()===8 || d.getType()===9){out[d.getName()]=d.serializeToXml();}} return out;'
 data=js(code);save('N0-final-configs.json',data)
 print('Captured',list(data))
 print('Server XML excerpt',data.get('Server0','')[:2500])
