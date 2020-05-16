
import cx_Oracle
from autofarma import settings

#Crea una conexión a la base de datos mediante la libreria cx_Oracle
class ConexionBD:

    dsn = cx_Oracle.makedsn("localhost", 1521, service_name="xepdb1")

    #Obtiene el usuario y la contraseña de la base de datos de settings.py
    bd_user = settings.DATABASES.get('default').get('USER')
    bd_password = settings.DATABASES.get('default').get('PASSWORD')

    #devuelve una conexión para utilizar la base de datos
    def conectar(self):
        conn = cx_Oracle.connect(self.bd_user, self.bd_password, self.dsn, encoding="UTF-8")
        return conn