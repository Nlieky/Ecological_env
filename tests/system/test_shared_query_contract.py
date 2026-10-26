from types import SimpleNamespace

import pandas as pd
import pytest

from shared.data.influxdb_query import fetch_wastewater_df


def client_for(result, queries):
    def query(flux):
        queries.append(flux)
        return result
    return SimpleNamespace(query_api=lambda: SimpleNamespace(query_data_frame=query))


def test_empty_table_list_is_empty():
    assert fetch_wastewater_df(client_for([pd.DataFrame()], []), 'legacy', 'effluent', plant_id='A').empty


def test_real_source_and_escaped_plant_are_explicit(monkeypatch):
    monkeypatch.setenv('INFLUXDB_REAL_BUCKET', 'real-test')
    queries = []
    fetch_wastewater_df(client_for(pd.DataFrame(), queries), 'real-test', 'effluent', plant_id='A"B')
    assert 'r.data_origin == "real"' in queries[0]
    assert 'r.plant_id == "A\\"B"' in queries[0]


def test_unscoped_query_is_rejected():
    with pytest.raises(ValueError, match='plant_id'):
        fetch_wastewater_df(client_for(pd.DataFrame(), []), 'legacy', 'effluent')


def test_dynamic_numeric_fields_exclude_provenance():
    frame = pd.DataFrame({'_time': ['2026-07-14T00:00:00Z'], 'COD': [30.], 'temperature': [22.], '_source_file': ['report.xls'], 'data_origin': ['real']})
    result = fetch_wastewater_df(client_for(frame, []), 'legacy', 'effluent', plant_id='A', include_all_fields=True)
    assert list(result.columns) == ['COD', 'temperature']
