"""Read only the authenticated account's quota; never read or export credentials."""
import json,selectors,subprocess,time
from .store import now

def get_quota(timeout=25):
    try:p=subprocess.Popen(['codex','app-server','--stdio'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,bufsize=1)
    except OSError as exc:return {'status':'unavailable','read_at':now(),'error':str(exc)}
    sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
    def send(x):p.stdin.write(json.dumps(x)+'\n');p.stdin.flush()
    def receive(wanted):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if not sel.select(timeout=.5):continue
            line=p.stdout.readline()
            if not line:break
            try:r=json.loads(line)
            except ValueError:continue
            if r.get('id')==wanted:
                if 'error' in r:raise RuntimeError(str(r['error'].get('message','RPC error')))
                return r['result']
        raise TimeoutError('quota read timed out')
    try:
        send({'id':1,'method':'initialize','params':{'clientInfo':{'name':'fly_brain_quota','version':'1.0'}}});receive(1);send({'method':'initialized'})
        send({'id':2,'method':'account/rateLimits/read'});data=receive(2)
        buckets=data.get('rateLimitsByLimitId') or {'codex':data.get('rateLimits',{})}
        for key,b in buckets.items():
            if key!='codex':continue
            for name in ('primary','secondary'):
                w=b.get(name)
                if w and w.get('windowDurationMins',0)>=10000:
                    return {'status':'available','read_at':now(),'bucket':key,'used_percent':w['usedPercent'],'resets_at':w.get('resetsAt'),'window_minutes':w['windowDurationMins']}
        return {'status':'unknown','read_at':now(),'reason':'weekly bucket unavailable'}
    except Exception as e:return {'status':'unknown','read_at':now(),'reason':str(e)[:250]}
    finally:
        sel.close();p.terminate()
        try:p.wait(timeout=5)
        except subprocess.TimeoutExpired:p.kill();p.wait()
if __name__=='__main__':print(json.dumps(get_quota(),ensure_ascii=False))
