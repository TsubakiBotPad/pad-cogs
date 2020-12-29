import sqlite3 as lite

import logging

logger = logging.getLogger('red.padbot-cogs.dadguide.database_manager')


class DadguideTableNotFound(Exception):
    def __init__(self, table_name):
        self.message = '{} not found'.format(table_name)


class DadguideDatabase(object):
    def __init__(self, data_file):
        self._con = lite.connect(data_file, detect_types=lite.PARSE_DECLTYPES)
        self._con.row_factory = lite.Row

    def __del__(self):
        self.close()
        logger.info("Garbage Collecting Old Database")

    def has_database(self):
        return self._con is not None

    def close(self):
        if self._con:
            self._con.close()
        self._con = None

    @staticmethod
    def select_builder(tables, key=None, where=None, order=None, distinct=False):
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

    def query_one(self, query, param):
        cursor = self._con.cursor()
        cursor.execute(query, param)
        res = cursor.fetchone()
        if res is not None:
            return DictWithAttrAccess(res)
        return None

    @staticmethod
    def as_generator(cursor):
        res = cursor.fetchone()
        while res is not None:
            yield DictWithAttrAccess(res)
            res = cursor.fetchone()

    def query_many(self, query, param, idx_key=None, as_generator=False):
        cursor = self._con.cursor()
        cursor.execute(query, param)
        if cursor.rowcount == 0:
            return []
        if as_generator:
            return (DictWithAttrAccess(res)
                    for res in cursor.fetchall())
        else:
            if idx_key is None:
                return [DictWithAttrAccess(res) for res in cursor.fetchall()]
            else:
                return DictWithAttrAccess({res[idx_key]: DictWithAttrAccess(res) for res in cursor.fetchall()})

    def get_table_fields(self, table_name: str):
        # SQL inject vulnerable :v
        table_info = self.query_many('PRAGMA table_info(' + table_name + ')', (), dict)
        pk = None
        fields = []
        for c in table_info:
            if c['pk'] == 1:
                pk = c['name']
            fields.append(c['name'])
        if len(fields) == 0:
            raise DadguideTableNotFound(table_name)
        return fields, pk


class DictWithAttrAccess(dict):
    def __init__(self, item):
        super(DictWithAttrAccess, self).__init__(item)
        self.__dict__ = self
