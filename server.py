import uvicorn

# configs
import app.configs.AppConfig as __CONFIG_APPCONFIG
import app.db.DBManager as __DB_MANAGER
import app.db.DBConfig as __DB_CONFIG

__CONFIG_APPCONFIG.SET()

db = __DB_MANAGER.DBManager()
db.ADD('MES_DB', __DB_CONFIG.MES_DB)
db.ADD('WMS_DB', __DB_CONFIG.WMS_DB)

if __name__ == '__main__':
  uvicorn.run('app.main:app', host = '0.0.0.0', port = 5000, use_colors = True, log_config = None)