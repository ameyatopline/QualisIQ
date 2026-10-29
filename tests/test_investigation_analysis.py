from decimal import Decimal
import pytest
from app import models as m


def record(client, headers, incoming, key, **changes):
    body = {**incoming, 'source_record_id': key, 'idempotency_key': key, **changes}
    response = client.post('/api/v1/lab/results', headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_chart_history_is_bounded_comparable_and_ends_at_case(env, token, incoming):
    client, _ = env
    headers = token('qc_analyst')
    prior = [record(client, headers, incoming, f'PRIOR-{i:02}', value=str(99 + i / 10),
                    measured_at=f'2026-10-{20+i:02}T10:00:00Z')['result_id'] for i in range(5)]
    case = record(client, headers, incoming, 'CASE-CURRENT')
    excluded = [
        record(client, headers, incoming, 'FUTURE-RESULT', value='99.5', measured_at='2026-10-30T10:00:00Z')['result_id'],
        record(client, headers, incoming, 'LATER-TIE', value='99.5')['result_id'],
        record(client, headers, incoming, 'OTHER-SITE', value='99.5', measured_at='2026-10-28T10:00:00Z', site_code='DQ-002', batch_number='DON-SYN-B-0000002', inspection_lot='DON-SYN-L-0000002', sample_number='DON-SYN-S-0000002')['result_id'],
        record(client, headers, incoming, 'OTHER-MATERIAL', value='99.5', measured_at='2026-10-28T10:00:00Z', material_code='DON-MAT-002', batch_number='DON-SYN-B-0000003', inspection_lot='DON-SYN-L-0000003', sample_number='DON-SYN-S-0000003')['result_id'],
        record(client, headers, incoming, 'OTHER-TEST', value='93', test_name='Dissolution', measured_at='2026-10-28T10:00:00Z')['result_id'],
    ]
    response = client.get(f'/api/v1/workbench/events/{case["event_id"]}/analysis?limit=3', headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    ids = [p['result_id'] for p in data['history']]
    assert ids == prior[-2:] + [case['result_id']]
    assert not set(ids).intersection(excluded)
    assert data['window']['available'] == 6
    assert data['window']['shown'] == 3 and data['window']['truncated'] is True
    assert sum(p['is_current'] for p in data['history']) == 1
    assert data['history'][-1]['measured_at'] == incoming['measured_at']
    assert data['specification'] == {'version': 'DEMO-SPEC-v1', 'lower': '95.000000', 'upper': '105.000000', 'within_limits': False}
    assert data['oot_status'] == 'CONTEXT_ONLY_OOS'
    assert data['cohort']['site'] == 'DQ-001'
    assert data['cohort']['material'] == 'DON-MAT-001'
    assert abs(Decimal(data['history'][-1]['signed_z']) - Decimal('-6.666666666666666666666666667')) < Decimal('.00000001')
    assert data['baseline']['threshold'] == '3.000'
    assert client.get(f'/api/v1/workbench/events/{case["event_id"]}/analysis?limit=101', headers=headers).status_code == 422


@pytest.mark.parametrize(('value', 'z'), [('102.65', '3.5'), ('96.35', '-3.5')])
def test_oot_chart_retains_signed_direction_and_distinct_specification(env, token, incoming, value, z):
    client, _ = env
    headers = token('qc_analyst')
    case = record(client, headers, incoming, 'OOT-SIGNED-CASE', value=value)
    assert case['outcome'] == 'OOT'
    data = client.get(f'/api/v1/workbench/events/{case["event_id"]}/analysis', headers=headers).json()
    assert data['specification']['within_limits'] is True
    assert data['oot_status'] == 'ASSESSED_DEMO'
    assert Decimal(data['history'][0]['signed_z']) == Decimal(z)
    assert data['window']['shown'] == 1
    assert data['window']['truncated'] is False
    assert Decimal(data['baseline']['mean']) == Decimal('99.5')
    assert Decimal(data['baseline']['sigma']) == Decimal('.9')


@pytest.mark.parametrize('problem', ['missing', 'retired', 'sigma', 'insufficient'])
def test_unusable_baseline_does_not_generate_fake_z_scores(env, token, incoming, problem):
    client, Factory = env
    headers = token('qc_analyst')
    case = record(client, headers, incoming, 'OOS-NO-BASELINE')
    with Factory() as db:
        result = db.get(m.TestResult, case['result_id'])
        profile = db.get(m.OOTProfile, result.oot_profile_id)
        if problem == 'missing': result.oot_profile_id = None
        elif problem == 'retired': profile.approved_for_demo = False
        elif problem == 'sigma': profile.sigma = Decimal('0')
        else: profile.baseline_n = 7
        db.commit()
    response = client.get(f'/api/v1/workbench/events/{case["event_id"]}/analysis', headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data['oot_status'] == 'NOT_ASSESSED'
    assert data['baseline'] is None and data['oot_reason']
    assert data['history'][0]['signed_z'] is None
    assert data['specification']['within_limits'] is False


def test_history_does_not_mix_oot_baseline_versions(env, token, incoming):
    client, Factory = env
    headers = token('qc_analyst')
    prior = record(client, headers, incoming, 'PRIOR-BASELINE', value='99.5', measured_at='2026-10-28T10:00:00Z')
    case = record(client, headers, incoming, 'CURRENT-BASELINE')
    with Factory() as db:
        result = db.get(m.TestResult, prior['result_id'])
        old = m.OOTProfile(specification_id=result.specification_id, version='RETIRED-BASELINE', mean=Decimal('97'), sigma=Decimal('1'), z_threshold=Decimal('2'), baseline_n=30, approved_for_demo=False)
        db.add(old); db.flush(); result.oot_profile_id = old.id; db.commit()
    data = client.get(f'/api/v1/workbench/events/{case["event_id"]}/analysis', headers=headers).json()
    assert data['history'][0]['signed_z'] is None
    assert data['history'][-1]['signed_z'] is not None
    assert data['baseline']['version'] == 'DEMO-BASE-v1'


def test_analysis_authorization_and_foreign_site_access(env, token, incoming):
    client, Factory = env
    headers = token('qc_analyst')
    case = record(client, headers, incoming, 'CHART-AUTH-CASE')
    path = f'/api/v1/workbench/events/{case["event_id"]}/analysis'
    assert client.get(path).status_code == 401
    assert client.get('/api/v1/workbench/events/99999/analysis', headers=headers).status_code == 404
    with Factory() as db:
        user = db.query(m.User).filter_by(email='qc_analyst@don-demo.test').one()
        user.site_id = 2; db.commit()
    assert client.get(path, headers=headers).status_code == 404


def test_analysis_rejects_other_tenants(env, token, incoming):
    from app.security import hash_password
    client, Factory = env
    headers = token('qc_analyst')
    case = record(client, headers, incoming, 'TENANT-CHART-CASE')
    with Factory() as db:
        t = m.Tenant(code='CHART-OTHER', name='Other synthetic tenant', synthetic=True)
        db.add(t); db.flush()
        db.add(m.User(tenant_id=t.id, email='auditor@other-chart.test', role='auditor', password_hash=hash_password('OtherChartOnly123!')))
        db.commit()
    auth = client.post('/api/v1/auth/login', json={'email':'auditor@other-chart.test','password':'OtherChartOnly123!','tenant_code':'CHART-OTHER'})
    assert auth.status_code == 200
    other = {'Authorization':'Bearer '+auth.json()['access_token']}
    assert client.get(f'/api/v1/workbench/events/{case["event_id"]}/analysis', headers=other).status_code == 404
