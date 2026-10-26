from types import SimpleNamespace

import pandas as pd
import pytest

from backend.services.data_service import DataService


def service():
    instance = DataService.__new__(DataService)
    incoming = pd.DataFrame()
    outgoing = pd.DataFrame({'COD': [30., None]}, index=pd.to_datetime(['2026-07-14 08:00', '2026-07-14 09:00']))
    instance._loader = SimpleNamespace(maybe_reload=lambda: None, influent=lambda: incoming, effluent=lambda: outgoing,
                                      latest_timestamp=outgoing.index.max(), _bucket='monitoring-real', _plant_id='A',
                                      window=lambda side, _: incoming if side == 'influent' else outgoing)
    return instance


def test_latest_finite_measurement_not_missing_row():
    result = service().get_realtime_data()
    assert result['effluent']['COD'] == 30
    assert result['flow_rate'] is None
    assert result['timestamp'] == '2026-07-14T01:00:00Z'


@pytest.mark.parametrize('aggregation', ['raw', 'hourly', 'daily'])
def test_effluent_only_history(aggregation):
    result = service().query_history_data(aggregation=aggregation)
    assert result['records']
    assert result['records'][0]['influent'] == {}


def test_effluent_only_aggregation():
    result = service().get_aggregated_data()
    assert result['data']['influent'] == {}
    assert result['data']['effluent']['2026-07-14']['COD_avg'] == 30


def test_nonfinite_values_are_json_safe():
    assert DataService._round_or_none(float('inf')) is None


def test_sum_does_not_turn_missing_days_into_zero():
    instance = service()
    outgoing = pd.DataFrame({'COD': [None, 30.]}, index=pd.to_datetime(['2026-07-14 08:00', '2026-07-16 08:00']))
    instance._loader.effluent = lambda: outgoing
    result = instance.get_aggregated_data(metrics='sum')['data']['effluent']
    assert result['2026-07-14']['COD_sum'] is None
    assert result['2026-07-15']['COD_sum'] is None
