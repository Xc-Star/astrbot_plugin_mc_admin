import sqlite3

from astrbot.core import logger


class DbUtils:

    def __init__(self):
        # 连接数据库
        self.db_conn = sqlite3.connect('./data/mc_admin.db', check_same_thread=False)
        # 初始化数据表
        cur = self.db_conn.cursor()
        try:
            sql = '''
            CREATE TABLE IF NOT EXISTS "task" (
                "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                "name" TEXT NOT NULL,
                "location" TEXT NOT NULL,
                "dimension" TEXT NOT NULL,
                "create_user" TEXT NOT NULL,
                "create_user_id" TEXT NOT NULL,
                PRIMARY KEY ("id")
            );
                
            CREATE TABLE IF NOT EXISTS "material" (
              "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
              "name" TEXT,
              "name_id" text,
              "total" integer,
              "recipient" TEXT,
              "commit_count" integer,
              "number" INTEGER,
              "task_id" INTEGER,
              "location" TEXT
            );
            '''
            cur.execute(sql)
        except:
            logger.error('数据库创建失败')

    def get_conn(self):
        return self.db_conn

    def close(self):
        self.db_conn.close()
