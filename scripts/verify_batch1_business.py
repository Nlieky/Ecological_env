"""Read-only business acceptance; temporary AI artifacts never enter real sessions.

Run with project Python. --http additionally validates the running backend.
"""
import argparse
import glob
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import requests
from shared.data.import_to_influxdb import DATA_GLOB, FIELD_MAP, parse_xls_report
from shared.data.influxdb_query import get_client_and_bucket, fetch_wastewater_df
from backend.api.v1.plants.routes import _query_dashboard
from shared.data.query_evidence import append_evidence
from shared.data.source_context import sampling_timestamp


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--http', action='store_true')
    args = parser.parse_args()
    client, bucket = get_client_and_bucket()
    sources = []
    try:
        for path in sorted(glob.glob(DATA_GLOB)):
            plant, side, rows = parse_xls_report(path)
            actual = fetch_wastewater_df(client, bucket, side, plant_id=plant, include_all_fields=True)
            expected = pd.DataFrame(rows)
            expected.index = pd.DatetimeIndex([sampling_timestamp(value).tz_localize(None) for value in expected['time']])
            expected = expected.sort_index()
            assert actual.index.equals(expected.index), (plant, side, 'sampling timestamps differ')
            for source, field in FIELD_MAP.items():
                if source in expected and expected[source].notna().any():
                    pd.testing.assert_series_equal(pd.to_numeric(expected[source]).astype(float), actual[field].astype(float),
                                                   check_names=False, check_index_type=False, check_exact=False, rtol=1e-10)
            # All sampling points carry the original file's digest, not just its filename.
            flux = (f'from(bucket: {json.dumps(bucket)}) |> range(start: 0) '
                    f'|> filter(fn: (r) => r._measurement == "wastewater" and r._field == "_source_sha256" '
                    f'and r.plant_id == {json.dumps(plant, ensure_ascii=False)} and r.data_type == {json.dumps(side)} '
                    'and r.data_origin == "real")')
            digests = [record.get_value() for table in client.query_api().query(flux) for record in table.records]
            assert len(digests) == len(rows)
            assert set(digests) == {hashlib.sha256(Path(path).read_bytes()).hexdigest()}
            sources.append({'plant': plant, 'side': side, 'records': len(rows), 'latest': str(actual.index.max()), 'values_and_hash_match': True})
    finally:
        client.close()
    script = ROOT / 'subagents/multi-dimensional-data-perception-agent/skills/data-perception-core/scripts/get_data.py'
    with tempfile.TemporaryDirectory(prefix='batch1-evidence-') as session:
        for plant in dict.fromkeys(row['plant'] for row in sources):
            env = dict(os.environ, SESSION_DIR=session, PYTHONUTF8='1')
            subprocess.run([sys.executable, str(script), '--plant', plant, '--start', '2026-07-14', '--end', '2026-07-15'],
                           env=env, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', check=True, timeout=60)
            artifact = json.loads((Path(session) / 'data_result.json').read_text(encoding='utf-8'))
            result = artifact['result']
            params = {'anchor': '2026-07-14', 'end_date': '2026-07-15'}
            dashboard = (requests.get(f'http://localhost:8000/api/v1/plants/{plant}/dashboard', params=params, timeout=30).json()
                         if args.http else _query_dashboard(plant, 24, params['anchor'], params['end_date']))['data']
            for side in ('influent', 'effluent'):
                expected = [{'time': row['timestamp'], 'value': round(row['COD'], 2)} for row in result[side] if row.get('COD') is not None]
                assert dashboard['indicators']['COD']['series'][side] == expected, (plant, side, 'AI/dashboard COD differ')
            assert dashboard['data_context']['origin'] == result['metadata']['data_context']['origin'] == 'real'
            assert dashboard['data_context']['mode'] == 'historical'
        footer = append_evidence('verification', session)
        assert '历史真实数据，非实时接入' in footer and '异常不等于违规' in footer
        for plant in dict.fromkeys(row['plant'] for row in sources):
            assert plant in footer
    print(json.dumps({'sources': sources, 'total_records': sum(row['records'] for row in sources),
                      'AI_dashboard_COD_match': True, 'multi_plant_evidence': True, 'running_http_checked': args.http}, ensure_ascii=True))


if __name__ == '__main__':
    main()
