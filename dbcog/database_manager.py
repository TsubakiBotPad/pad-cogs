import logging
import sqlite3 as lite
from sqlite3 import OperationalError
from typing import Any, Dict, Generator, List, Optional, Tuple, Type, TypeVar, Union

from dbcog.errors import QueryManyFailure

logger = logging.getLogger('red.padbot-cogs.dbcog.database_manager')

T = TypeVar('T')


class DictWithAttrAccess(Dict[str, T]):
    def __init__(self, item: Optional[Dict[str, T]] = None, **items):
        if items:
            item = items
        super(DictWithAttrAccess, self).__init__(item)
        self.__dict__ = self


class DBCogDatabase:
    def __init__(self, data_file: str):
        self._con = lite.connect(data_file, detect_types=lite.PARSE_DECLTYPES)
        self._con.row_factory = lite.Row

    def __del__(self):
        self.close()
        logger.info("Garbage Collecting Old Database")

    def has_database(self) -> bool:
        return self._con is not None

    def close(self) -> None:
        if self._con:
            self._con.close()
        self._con = None

    @staticmethod
    def select_builder(tables, key: Optional[str] = None, where: Optional[str] = None,
                       order: Optional[str] = None, distinct: bool = False) -> str:
        if distinct:
            SELECT_FROM = 'SELECT DISTINCT {fields} FROM {first_table}'
        else:
            SELECT_FROM = 'SELECT {fields} FROM {first_table}'
        WHERE = 'WHERE {condition}'
        JOIN = 'LEFT JOIN {other_table} ON {first_table}.{key}={other_table}.{key}'
        ORDER = 'ORDER BY {order}'
        first_table = None
        fields_lst = []
        other_tables = []
        for table, fields in tables.items():
            if fields is not None:
                fields_lst.extend(['{}.{}'.format(table, f) for f in fields])
            if first_table is None:
                first_table = table
                if key is None:
                    break
            else:
                other_tables.append(table)
        query = [SELECT_FROM.format(first_table=first_table, fields=', '.join(fields_lst))]
        prev_table = first_table
        if key:
            for k, other in zip(key, other_tables):
                query.append(JOIN.format(first_table=prev_table, other_table=other, key=k))
                prev_table = other
        if where:
            query.append(WHERE.format(condition=where))
        if order:
            query.append(ORDER.format(order=order))
        return ' '.join(query)

    def query_one(self, query: str, param: Tuple = None) -> Optional[DictWithAttrAccess]:
        if param is None:
            param = ()

        cursor = self._con.cursor()
        cursor.execute(query, param)
        res = cursor.fetchone()
        if res is not None:
            return DictWithAttrAccess(res)
        return None

    def query_many(self, query: str, param: Tuple = None, idx_key: Optional[str] = None,
                   as_generator: bool = False, as_type: Type[T] = DictWithAttrAccess) \
            -> Union[Generator[T, None, None],
                     List[T],
                     Dict[Any, T]]:
        if param is None:
            param = ()

        cursor = self._con.cursor()
        try:
            cursor.execute(query, param)
        except OperationalError:
            raise QueryManyFailure

        if cursor.rowcount == 0:
            return []
        if as_generator:
            return (as_type(**res) for res in cursor.fetchall())
        else:
            if idx_key is None:
                return [as_type(**res) for res in cursor.fetchall()]
            else:
                return {res[idx_key]: as_type(**res) for res in cursor.fetchall()}
