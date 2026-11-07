"""Verify the current Packet Tracer file against the reopened remediation capture."""

import argparse
import hashlib
import json
from pathlib import Path
import zipfile


BASE = Path(__file__).resolve().parents[1]
DEFAULT_RUN = BASE / 'evidence/AUDIT-REMEDIATION-20261105-182333'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def require(condition, message):
    """Integrity checks must remain active under python -O."""
    if not condition:
        raise ValueError(message)


def verify(run, record=False):
    run = run.resolve()
    require(run.is_relative_to((BASE / 'evidence').resolve()), 'Run must be inside project evidence')
    progress = read_json(run / 'progress.json')
    meta = progress['currentCheckpoint']
    iteration = meta['iteration']
    label = f'iteration{iteration}'
    require(progress['iterations'][str(iteration)] == 'passed and verified after reopening',
            'Checkpoint validation failed: iteration was not verified after reopening')
    require(meta['file'] == 'Secure_Campus_Network_Submission.pkt', 'Unexpected submission filename')
    packet = (BASE / meta['file']).read_bytes()
    require(len(packet) == meta['bytes'] and digest(packet) == meta['sha256'], 'Saved simulation differs from the verified checkpoint')
    with zipfile.ZipFile(run / f'{label}-checkpoint-private.zip') as archive:
        require(digest(archive.read(meta['file'])) == meta['sha256'], 'Recovery archive differs from the verified checkpoint')
    summary_path = run / f'{label}-reopened-summary.json'
    state_path = run / f'{label}-reopened-state.json'
    summary, state = read_json(summary_path), read_json(state_path)
    require(summary['passed'] and summary['sha256'] == state['submissionSha256'] == meta['sha256'],
            'Reopened evidence failed or refers to a different submission')
    require(len(state['endpoints']) == len({v['ip'] for v in state['endpoints'].values()}) == 52,
            'Expected 52 endpoints with unique addresses')
    require(all(v['ip'] != '0.0.0.0' for v in state['endpoints'].values()),
            'An endpoint has no assigned address')
    export = run / f'{label}-verified-configs'
    files = [summary_path, state_path, run / f'{label}-submission.json']
    if iteration:
        regression = run / f'{label}-regression-summary.json'
        require(read_json(regression)['allPassed'], 'Regression checks failed')
        files.append(regression)
    if iteration == 4:
        files += [run / 'iteration4-monitoring-reopened.json', run / 'iteration4-ospf-behavior.json']
        require(read_json(files[-1])['passed'], 'OSPF behavior checks failed')
    if iteration >= 5:
        failover = run / f'{label}-core-failover.json'
        core_cases = read_json(failover)
        require(set(core_cases) == {'SW1-CORE', 'SW5-CORE'}, 'Missing core outage case')
        for case in core_cases.values():
            require(case['failureRecovery']['passed'] and case['restoration']['passed'],
                    'Core failure recovery or restoration failed')
            require(case['campusClients'] == 50 and case['externalClients'] == 49 and case['isolationPassed'],
                    'Core outage reachability or isolation checks failed')
            require(case['dhcpRenewals'] == 3 and case['portalClients'] == 4 and case['externalHttpClients'] == 3,
                    'Core outage DHCP or HTTP checks failed')
        files += [failover, run / f'{label}-reopened-routing.json']
    if iteration >= 6:
        inspection = run / 'iteration6-firewall-behavior.json'
        require(read_json(inspection)['passed'], 'Firewall inspection checks failed')
        files.append(inspection)
    if record:
        export.mkdir(exist_ok=True)
        for name, config in state['configs'].items():
            require(name.replace('-', '').isalnum(), 'Invalid device name for configuration export')
            (export / f'{name}.txt').write_text(config['running'] + '\n', encoding='utf-8')
        files.extend(sorted(export.glob('*.txt')))
    result = {
        **meta,
        'reopenedAt': summary['observedAt'],
        'networkDevices': sum(d['type'] in (0, 1, 8, 9, 16) for d in state['devices']),
        'links': len(state['links']),
        'endpoints': len(state['endpoints']),
        'evidence': {p.relative_to(BASE).as_posix(): digest(p.read_bytes()) for p in files},
    }
    manifest = run / 'verified-submission.json'
    if record:
        write_json(manifest, result)
        (BASE / 'SUBMISSION_SHA256.txt').write_text(meta['sha256'].upper() + '  ' + meta['file'] + '\n', encoding='utf-8')
    elif manifest.exists():
        saved = read_json(manifest)
        require(saved['sha256'] == meta['sha256'], 'Recorded manifest is stale')
        for name, expected in saved['evidence'].items():
            path = (BASE / name).resolve()
            require(path.is_relative_to(run.resolve()) and digest(path.read_bytes()) == expected, name)
        result = saved
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=DEFAULT_RUN)
    parser.add_argument('--record', action='store_true', help='Record the verified checkpoint and export sanitized configurations')
    arguments = parser.parse_args()
    result = verify(arguments.run, arguments.record)
    print(f"Verified iteration {result['iteration']} · {result['networkDevices']} devices · {result['links']} links · {result['sha256']}")
