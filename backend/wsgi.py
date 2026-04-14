import os
import pymysql

# Patch Django to use PyMySQL for database connections
pymysql.install_as_MySQLdb()
pymysql.version_info = (2, 2, 1, "final", 0)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
application = get_wsgi_application()
