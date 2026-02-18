from dataclasses import dataclass
from typing import Protocol, Optional


class QueryRunnerProtocol(Protocol):
    def execute(self, query: str, params: Optional[dict] = None) -> list[tuple]:
        ...


@dataclass
class UPCServiceResult:
    upc_dict: dict[int, list]
    success: bool
    errors: list[str]


class MockQueryRunner:
    def __init__(self, mock_data: Optional[list[tuple]] = None):
        self._mock_data = mock_data or []

    def execute(self, query: str, params: Optional[dict] = None) -> list[tuple]:
        return self._mock_data


class UPCService:
    def __init__(self, query_runner: QueryRunnerProtocol):
        self._query_runner = query_runner
        self._upc_cache: Optional[dict[int, list]] = None

    def fetch_upc_dictionary(self, settings: dict) -> UPCServiceResult:
        query = """select 
    dsanrep.anbacd,
    dsanrep.anbbcd,
    strip(dsanrep.anbgcd),
    strip(dsanrep.anbhcd),
    strip(dsanrep.anbicd),
    strip(dsanrep.anbjcd)
from dacdata.dsanrep dsanrep"""

        try:
            results = self._query_runner.execute(query)
            upc_dict: dict[int, list] = {}
            for row in results:
                item_number = row[0]
                category = row[1]
                upc_list = [category, row[2], row[3], row[4], row[5]]
                upc_dict[item_number] = upc_list
            self._upc_cache = upc_dict
            return UPCServiceResult(upc_dict=upc_dict, success=True, errors=[])
        except Exception as e:
            return UPCServiceResult(upc_dict={}, success=False, errors=[str(e)])

    def get_upc_for_item(self, item_number: int) -> Optional[str]:
        if self._upc_cache is None:
            return None
        upc_list = self._upc_cache.get(item_number)
        if upc_list and len(upc_list) > 1:
            return upc_list[1]
        return None

    def get_category_for_item(self, item_number: int) -> Optional[str]:
        if self._upc_cache is None:
            return None
        upc_list = self._upc_cache.get(item_number)
        if upc_list:
            return upc_list[0]
        return None
