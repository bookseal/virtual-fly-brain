"""Recover five failed films without erasing the original failure history."""
from .store import *
from .video import render_one,retrospective
from .report import build_report
from .publisher import publish_once

def main():
    run=RUNS/'20261014-115448'
    event(run,'correction','첫 회차 영상 복구 시작',actor='gpt-6.1-sol',detail='기존 실패 기록을 보존하고 최신 검증된 렌더러로 재시도합니다. 공개 회고는 개인 계정 정보가 있는 준비 구간을 제외합니다.')
    for p in sorted((run/'intervals').glob('*.json')):
        if read(p).get('render',{}).get('status')=='failed':render_one(run,p)
    retrospective(run,public_only=True);build_report(run);publish(run);print(publish_once(run),flush=True)
if __name__=='__main__':main()
