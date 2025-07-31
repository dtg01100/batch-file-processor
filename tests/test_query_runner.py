import pytest
import query_runner

def test_query_runner_invalid_query():
    with pytest.raises(Exception):
        query_runner.run_query(None)
