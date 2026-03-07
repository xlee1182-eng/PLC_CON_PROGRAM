# DBManager.py

import traceback
import oracledb

from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

## utils
# import app.utils.WriteConsoleLog as __UTIL_WRITECONSOLELOG
# import app.utils.WriteDBLog as __UTIL_WRITEDBLOG
# import app.functions.CommonFunction as __FUNCTION_COMMON

# LOGGER = __UTIL_WRITECONSOLELOG.SETLOGGER()

class DBManager():

    def __init__(self):

        self.engines = {}
        self.configs = {}
        self.conn = {}

    ############################################################
    # DB 등록
    ############################################################
    def ADD(self, dbname, config):

        try:

            db_type = config['DB_TYPE']

            if db_type == "ORACLE":

                SQLALCHEMYSTR = f'oracle+oracledb://{config["USERNAME"]}:{config["PASSWORD"]}@{config["IP"]}:{config["PORT"]}/?service_name={config["SERVICE"]}'
                conn = oracledb.connect(
                    user = config["USERNAME"],
                    password = config["PASSWORD"],
                    host = config["IP"],
                    port = config["PORT"],
                    service_name = config["SERVICE"]
                )
                self.conn[dbname] = conn
            elif db_type == "POSTGRES":

                SQLALCHEMYSTR = f'postgresql://{config["USERNAME"]}:{config["PASSWORD"]}@{config["IP"]}:{config["PORT"]}/{config["SCHEMA"]}'

            elif db_type == "MYSQL":

                SQLALCHEMYSTR = f'mysql+pymysql://{config["USERNAME"]}:{config["PASSWORD"]}@{config["IP"]}:{config["PORT"]}/{config["SCHEMA"]}'

            elif db_type == "MSSQL":

                SQLALCHEMYSTR = f'mssql+pymssql://{config["USERNAME"]}:{config["PASSWORD"]}@{config["IP"]}:{config["PORT"]}/{config["SCHEMA"]}'

            engine = create_engine(
                SQLALCHEMYSTR,
                pool_size = 10,
                max_overflow = 20,
                pool_timeout = 30,
                pool_recycle = 3600,
                pool_pre_ping=True,
                echo = False
            )

            self.engines[dbname] = engine
            self.configs[dbname] = config

            logger.info(f"DB TYPE: {db_type}, IP: {config['IP']}, PORT: {config['PORT']}")

        except:
            logger.error(f"{dbname} ADD error: {traceback.format_exc()}")

    ############################################################
    # SQL 실행
    ############################################################
    def EXECUTE(self, dbname, mode, query, params=None):

        try:

            engine = self.engines.get(dbname)

            if engine is None:
                raise Exception(f"{dbname} engine not found")

            with Session(engine) as session:

                try:

                    if mode == "GET":

                        result = session.execute(
                            text(query),
                            params,
                            execution_options={'timeout':10}
                        ).mappings().fetchall()

                        if len(result) > 0:

                            result = [dict(row) for row in result]

                            # result = __FUNCTION_COMMON.DICTKEYTOUPPER(result)

                        return result

                    elif mode == "SET":

                        session.execute(
                            text(query),
                            params,
                            execution_options={'timeout':10}
                        )

                        session.commit()

                        return True

                except:

                    session.rollback()
                    raise

        except:
            logger.error(f"{dbname} EXECUTE error: {traceback.format_exc()}")

    def CREATECURSOR(self, dbname):

        try:

            conn = self.conn.get(dbname)

            if conn is None:
                raise Exception(f"{dbname} connection not found")

            cursor = conn.cursor()

            return cursor

        except:
            logger.error(f"{dbname} CREATECURSOR error: {traceback.format_exc()}")
    ############################################################
    # 재연결
    ############################################################
    def RECONNECT(self, dbname):

        logger.info(f"########### {dbname} RECONNECT ###########")
        
        try:

            config = self.configs.get(dbname)

            if config is None:
                return
            
            if dbname in self.engines:
                self.engines[dbname].dispose()
            self.ADD(dbname, config)

        except:
            logger.error(f"{dbname} RECONNECT error: {traceback.format_exc()}")