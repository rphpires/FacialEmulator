
# Descrição: Arquivo base para conexão com o banco de dados
# Desenvolvido por: Raphael Pires
# Última Revisão: 09/08/2023

import threading
import pyodbc
import configparser
from dotenv import load_dotenv
import os


load_dotenv()

class DatabaseReader:
    def __init__(self):
        self.server = os.getenv("WXS_DATABASE_SERVER")
        self.database = os.getenv("WXS_DATABASE_NAME")
        self.username = os.getenv("WXS_DATABASE_USER")
        self.password = os.getenv("WXS_DATABASE_PASSWORD")
        self.lock = threading.Lock()

    def _create_connection(self):
        connection_string = (
            f"DRIVER={{SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"UID={self.username};"
            f"PWD={self.password};"
            "Encrypt=no;"
        )
        # print(f'ConnString: {connection_string}')
        return pyodbc.connect(connection_string)

    def _execute_query(self, query):
        connection = self._create_connection()
        cursor = connection.cursor()

        try:
            cursor.execute(query)
            connection.commit()
            return True
        except Exception as e:
            print(f"Error executing query: {str(e)}")
            connection.rollback()
            return False
        finally:
            cursor.close()
            connection.close()

    def read_data(self, query):
        with self.lock:
            connection = self._create_connection()
            cursor = connection.cursor()

            try:
                cursor.execute(query)
                result = cursor.fetchall()
            except Exception as e:
                result = None
                print(f"Error executing query: {str(e)}")
            finally:
                cursor.close()
                connection.close()

        return result

    def read_single_row(self, query):
        with self.lock:
            connection = self._create_connection()
            cursor = connection.cursor()

            try:
                cursor.execute(query)
                result = cursor.fetchone()
            except Exception as e:
                result = None
                print(f"Error executing query: {str(e)}")
            finally:
                cursor.close()
                connection.close()

        return result

    def execute_update(self, query):
        return self._execute_query(query)

    def execute_insert(self, query):
        return self._execute_query(query)

    def execute_procedure(self, procedure_name, params=None):
        with self.lock:
            connection = self._create_connection()
            cursor = connection.cursor()

            try:
                if params:
                    cursor.execute(f"EXEC {procedure_name} {', '.join(params)}")
                else:
                    cursor.execute(f"EXEC {procedure_name}")
                connection.commit()
                return True
            except Exception as e:
                print(f"Error executing procedure: {str(e)}")
                connection.rollback()
                return False
            finally:
                cursor.close()
                connection.close()

    # def get_odbc_client(self):
    #     try:
    #         from GlobalFunctions import check_os
            
    #         match check_os():
    #             case 'Linux':
    #                 odbc = '{ODBC Driver 18 for SQL Server}'
    #             case 'Windows':
    #                 odbc = '{SQL Server}'
    #             case _:
    #                 odbc = '{SQL Server}'
    #     except Exception as ex:
    #         print('*** Error getting drive ODBC')

    #     finally:
    #         return odbc
