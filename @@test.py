import pyodbc

def connect_to_sql_server():
    # Defina os parâmetros de conexão
    server = '172.16.17.101\W_ACCESS'  # Nome do servidor ou endereço IP
    database = 'W_ACCESS'  # Nome do banco de dados
    username = 'w-access'  # Nome de usuário
    password = 'db_W-X-S@Wellcare924_'  # Senha

    # String de conexão com SQL Server
    connection_string = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=no;'
    print(connection_string)
    try:
        # Estabelecer a conexão
        connection = pyodbc.connect(connection_string)
        print("Conexão bem-sucedida!")
        
        return connection

    except pyodbc.Error as e:
        print("Erro ao conectar ao SQL Server:", e)
        return None

def execute_query(connection, query):
    try:
        # Criar um cursor para executar consultas
        cursor = connection.cursor()
        
        # Executar a consulta
        cursor.execute(query)
        
        # Se for uma consulta SELECT, buscar os resultados
        if query.strip().lower().startswith('select'):
            results = cursor.fetchall()
            for row in results:
                print(row)
        
        # Se for uma consulta de modificação (INSERT, UPDATE, DELETE), commit a transação
        else:
            connection.commit()
            print("Consulta executada com sucesso!")

    except pyodbc.Error as e:
        print("Erro ao executar a consulta:", e)

def close_connection(connection):
    if connection:
        connection.close()
        print("Conexão fechada.")

if __name__ == "__main__":
    # Conectar ao SQL Server
    connection = connect_to_sql_server()

    if connection:
        # Executar uma consulta de exemplo
        query = "select count(*) from CHMain"
        execute_query(connection, query)
