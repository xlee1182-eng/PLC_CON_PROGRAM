import uvicorn

# configs
import app.configs.AppConfig as __CONFIG_APPCONFIG

__CONFIG_APPCONFIG.SET()



if __name__ == '__main__':
  uvicorn.run(
    'app.main:app',
    host = '0.0.0.0',
    port = 5000,
    use_colors = True,
    log_config = None,
    timeout_graceful_shutdown = 1, # 정상 종료(graceful shutdown)를 얼마나 기다릴지 = 1 → 1초 기다림
  )