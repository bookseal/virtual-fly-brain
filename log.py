#!/usr/bin/env python3
"""site/timeline.json 기록기.
  log.py add --phase N --title T [--cmd C] [--why W] [--status planned|running|done|failed] [--out O | --out-file F] [--media m...]
  log.py set ID [--status S] [--out O | --out-file F] [--media m...] [--why W] [--title T] [--cmd C]
  log.py phase ID --status S
  log.py note --title T --body B [--date D] [--links 제목=URL ...]
  --cmd-ko: 줄마다 "명령 ||| 한글 직역" 
"""
import argparse, json, datetime, pathlib
from lab.store import lock, atomic
F = pathlib.Path(__file__).with_name('site') / 'timeline.json'
ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='c', required=True)
n = sub.add_parser('note'); n.add_argument('--title', required=True); n.add_argument('--body', required=True); n.add_argument('--date'); n.add_argument('--links', nargs='*', help='제목=URL')
for name in ('add', 'set', 'phase'):
    s = sub.add_parser(name)
    if name != 'add': s.add_argument('id', type=int)
    if name == 'add': s.add_argument('--phase', type=int, required=True)
    for k in ('title', 'cmd', 'why', 'out', 'out_file', 'status', 'cmd_ko'): s.add_argument('--' + k.replace('_', '-'))
    s.add_argument('--media', nargs='*')
a = ap.parse_args()
with lock(F.with_suffix('.lock')):
    d = json.loads(F.read_text())
    if a.c == 'note':
        d.setdefault('notes', []).append({'title': a.title, 'body': a.body, 'date': a.date or datetime.date.today().isoformat(),
                                          'links': [dict(zip(('t', 'u'), x.split('=', 1))) for x in (a.links or [])]})
    elif a.c == 'phase':
        p = next(p for p in d['phases'] if p['id'] == a.id); p['status'] = a.status
    else:
        if a.c == 'add':
            s = {'id': max([s['id'] for s in d['steps']] or [0]) + 1, 'time': datetime.datetime.now().strftime('%m-%d %H:%M'),
                 'phase': a.phase, 'status': 'done', 'media': []}
            d['steps'].append(s)
        else:
            s = next(s for s in d['steps'] if s['id'] == a.id)
        for k in ('title', 'cmd', 'why', 'out', 'status'):
            if getattr(a, k) is not None: s[k] = getattr(a, k)
        if a.out_file: s['out'] = pathlib.Path(a.out_file).read_text(errors='replace')[-4000:]  # ponytail: tail 4000 chars, enough for a tutorial
        if a.cmd_ko:  # 줄마다 "명령 ||| 한글 뜻"
            s['cmd_ko'] = [[x.strip() for x in ln.split('|||', 1)] if '|||' in ln else [ln.strip(), ''] for ln in a.cmd_ko.strip().split('\n') if ln.strip()]
        if a.media: s['media'] = s.get('media', []) + a.media
        print(s['id'])
    d['updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    atomic(F, d)
