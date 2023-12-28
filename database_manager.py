from abc import ABC, abstractmethod
from typing import Optional

import psycopg2
import pyodbc

from constants import KEYS


def database_manager_factory(database):
    if database == "mssqllocaldb":
        return MSSQLLocalDbManager()
    elif database == "postgres":
        return PostgresDbManager()


class DatabaseManager(ABC):
    @abstractmethod
    def write_to_database(self, entry: dict):
        pass

    @abstractmethod
    def get_priority_for_url(self, url: str) -> Optional[int]:
        pass

    @abstractmethod
    def check_if_url_exists(self, url: str):
        pass

    @abstractmethod
    def update_priority(self, url: str, new_priority: int):
        pass

    @abstractmethod
    def close_connection(self):
        pass


class MSSQLLocalDbManager(DatabaseManager):
    CONNECTION_STRING = r'DRIVER={ODBC Driver 17 for SQL Server};' \
                        r'SERVER=(localdb)\MSSQLLocalDB;' \
                        r'DATABASE=aspnet-NoviceNet-20230914075751;' \
                        r'Trusted_Connection=yes;'  # This uses Windows Authentication

    def __init__(self):
        self._conn = pyodbc.connect(self.CONNECTION_STRING)
        self._cursor = self._conn.cursor()

    def write_to_database(self, entry: dict):
        entry_tuple = (entry.get(KEYS.URL), entry.get(KEYS.TITLE), entry.get(KEYS.SUMMARY),
                       entry.get(KEYS.DATETIME), entry.get(KEYS.TEXT), entry.get(KEYS.PRIORITY))
        self._cursor.execute("INSERT INTO News (Url, Title, Summary, DateTime, FullText, Priority) "
                             "VALUES (?, ?, ?, ?, ?, ?)", entry_tuple)
        self._conn.commit()

    def get_priority_for_url(self, url: str) -> Optional[int]:
        self._cursor.execute("SELECT Priority FROM News WHERE Url=?", (url,))
        result = self._cursor.fetchone()
        if result:
            return result[0]

    def check_if_url_exists(self, url):
        check_url_sql = "SELECT COUNT(*) FROM News WHERE Url = ?"
        self._cursor.execute(check_url_sql, (url,))
        return self._cursor.fetchone()[0]

    def update_priority(self, url: str, new_priority: int):
        self._cursor.execute("""
                            UPDATE News SET Priority=? WHERE Url=?
                        """, (new_priority, url))
        self._conn.commit()

    def close_connection(self):
        self._conn.close()


class PostgresDbManager(DatabaseManager):
    # TODO This should be read from a appsettings.json file or something
    CONNECTION_STRING = "dbname='novice_net' user='postgres' host='localhost' password='password'"

    def __init__(self):
        self._conn = psycopg2.connect(self.CONNECTION_STRING)
        self._cursor = self._conn.cursor()

    def write_to_database(self, entry: dict):
        entry_tuple = (entry.get(KEYS.URL), entry.get(KEYS.TITLE), entry.get(KEYS.SUMMARY),
                       entry.get(KEYS.DATETIME), entry.get(KEYS.TEXT), entry.get(KEYS.PRIORITY))
        self._cursor.execute("INSERT INTO News (Url, Title, Summary, DateTime, FullText, Priority) "
                             "VALUES (%s, %s, %s, %s, %s, %s)", entry_tuple)
        self._conn.commit()

    def get_priority_for_url(self, url: str) -> Optional[int]:
        self._cursor.execute("SELECT Priority FROM News WHERE Url=%s", (url,))
        result = self._cursor.fetchone()
        if result:
            return result[0]

    def check_if_url_exists(self, url):
        check_url_sql = "SELECT COUNT(*) FROM News WHERE Url = %s"
        self._cursor.execute(check_url_sql, (url,))
        return self._cursor.fetchone()[0]

    def update_priority(self, url: str, new_priority: int):
        self._cursor.execute("""
                            UPDATE News SET Priority=%s WHERE Url=%s
                        """, (new_priority, url))
        self._conn.commit()

    def close_connection(self):
        self._cursor.close()
        self._conn.close()

