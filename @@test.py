import pyodbc

connection_string = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=172.16.17.101\W_ACCESS;'
    'DATABASE=W_Access;'
    'UID=W-Access;'
    'PWD=db_W-X-S@Wellcare924_;'
    'TrustServerCertificate=yes'
)
try:
    connection = pyodbc.connect(connection_string)
    print("Connection successful!")
except pyodbc.Error as e:
    print("Error:", e)
