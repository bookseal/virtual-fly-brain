"""Publishing must preserve a failed attempt and every unrelated checkout change."""
from pathlib import Path
import subprocess
import pytest
from lab import publisher


def test_dirty_publisher_checkout_is_preserved(tmp_path,monkeypatch):
    checkout=tmp_path/'publisher-checkout';checkout.mkdir()
    marker=checkout/'unrelated.txt';marker.write_text('keep this work')
    monkeypatch.setattr(publisher,'RUNS',tmp_path)
    calls=[]
    def git(*args,**kwargs):
        calls.append(args)
        return ' M unrelated.txt' if args==('status','--porcelain') else ''
    monkeypatch.setattr(publisher,'git',git)
    with pytest.raises(RuntimeError,match='unexpected changes'):
        publisher.publish_once(tmp_path/'run')
    assert marker.read_text()=='keep this work'
    assert not any(c[0] in ['checkout','add','commit','push'] for c in calls)


def test_unpushed_snapshot_is_retried_before_checkout_advance(tmp_path,monkeypatch):
    (tmp_path/'publisher-checkout').mkdir()
    monkeypatch.setattr(publisher,'RUNS',tmp_path)
    calls=[]
    def git(*args,**kwargs):
        calls.append(args)
        if args[:2]==('rev-list','--count'):return '1'
        if args[0]=='push':raise subprocess.CalledProcessError(1,args,output='injected network failure')
        return ''
    monkeypatch.setattr(publisher,'git',git)
    with pytest.raises(subprocess.CalledProcessError):publisher.publish_once(tmp_path/'run')
    assert ('rebase','origin/main') in calls
    assert not any(c[0]=='checkout' for c in calls)
