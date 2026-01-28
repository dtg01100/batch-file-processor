try:
    import pyodbc

    HAS_PYODBC = True
except ImportError:
    HAS_PYODBC = False
    pyodbc = None


class query_runner:
    def __init__(self, username: str, password: str, as400_hostname: str, driver: str):
        if not HAS_PYODBC:
            raise RuntimeError(
                "pyodbc not available - AS400 query functionality disabled"
            )

        self.connection = pyodbc.connect(
            driver=driver, system=as400_hostname, uid=username, pwd=password, p_str=None
        )
        self.username = ""
        self.password = ""
        self.host = ""

    def run_arbitrary_query(self, query_string):
        if not HAS_PYODBC:
            raise RuntimeError(
                "pyodbc not available - AS400 query functionality disabled"
            )
        cursor = self.connection.cursor()
        query_results = cursor.execute(query_string)
        query_return_list = []
        for entry in query_results:
            query_return_list.append(entry)
        return query_return_list
