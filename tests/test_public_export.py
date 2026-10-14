import importlib.util,json,xml.etree.ElementTree as ET
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('export_public',Path(__file__).resolve().parents[1]/'scripts/export_public.py')
export=importlib.util.module_from_spec(spec);spec.loader.exec_module(export)

def test_private_metadata_and_local_identity_are_removed():
    data={'quota':{'used_percent':40},'pid':123,'seed':11,'command':str(export.ROOT)+'/lab/learning.py','detail':'사용자(local, SAMPLE PERSON)'}
    cleaned=export.clean(data)
    assert 'quota' not in cleaned and 'pid' not in cleaned and cleaned['seed']==11
    assert str(export.ROOT) not in cleaned['command'] and 'SAMPLE PERSON' not in cleaned['detail']

def test_export_preserves_snapshot_evidence_and_valid_svg(tmp_path,monkeypatch):
    monkeypatch.setattr(export,'ROOT',tmp_path)
    site=tmp_path/'site';site.mkdir();(site/'timeline.json').write_text(json.dumps({'steps':[],'phases':[]}))
    run=tmp_path/'runs/example';(run/'media').mkdir(parents=True)
    svg='<svg xmlns="http://www.w3.org/2000/svg"><text>시작 시 주간 사용률 17%</text></svg>'
    (run/'media/start.svg').write_text(svg)
    row={'id':'start','index':0,'result':'시작 시 주간 사용률 17%','media':['artifacts/example/media/start.svg'],'render':{'status':'done','video':'artifacts/example/private.mp4'}}
    original={'run':{'started_at':'2026-01-01','quota_start':{'used_percent':17}},'state':{'status':'training','pid':1},'intervals':[row],'evaluations':[],'summaries':[],'quota':{'used_percent':20}}
    (run/'manifest.json').write_text(json.dumps(original));output=tmp_path/'public';output.mkdir()
    manifest=export.export_run(run,output);export.audit(output)
    assert manifest['publication']['mode']=='snapshot' and manifest['state']['status']=='training'
    assert manifest['intervals'][0]['render']['status']=='omitted'
    ET.parse(output/'artifacts/example/media/start.svg')
    assert not (output/'artifacts/example/private.mp4').exists()
    assert json.loads((run/'manifest.json').read_text())==original

def test_public_audit_rejects_credentials_and_account_data(tmp_path):
    file=tmp_path/'data.json';file.write_text(json.dumps({'used_percent':25}))
    with pytest.raises(ValueError):export.audit(tmp_path)
    file.write_text(json.dumps({'value':'github_pat_'+'a'*30}))
    with pytest.raises(ValueError):export.audit(tmp_path)
