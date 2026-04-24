from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    import pymysql
    import yaml
except ImportError as exc:
    missing = getattr(exc, "name", None) or str(exc)
    print(
        f"缺少依赖 {missing}，请先在当前 Python 环境安装 backend/requirements.txt 中的依赖。",
        file=sys.stderr,
    )
    sys.exit(1)


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
CONFIG_PATH = BACKEND_DIR / "config.yaml"
SQL_SCRIPT_PATH = BACKEND_DIR / "sql" / "write_sql.py"


def load_db_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise RuntimeError(
            f"未找到配置文件：{CONFIG_PATH}\n"
            "请从 config.yaml.example 复制一份为 config.yaml 并填入正确的配置。"
        )

    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}

    db_config = loaded.get("database", {})
    
    config = {
        "host": db_config.get("host"),
        "port": db_config.get("port"),
        "user": db_config.get("user"),
        "password": db_config.get("password"),
        "database": db_config.get("name"),
        "charset": db_config.get("charset", "utf8mb4"),
    }

    if not config["password"]:
        config["password"] = os.environ.get("DB_PASSWORD", "")

    return config


def connect_mysql(db_config: dict[str, Any], include_database: bool) -> pymysql.Connection:
    connect_kwargs: dict[str, Any] = {
        "host": db_config["host"],
        "port": int(db_config["port"]),
        "user": db_config["user"],
        "password": db_config["password"],
        "charset": db_config["charset"],
    }

    if include_database:
        connect_kwargs["database"] = db_config["database"]

    return pymysql.connect(**connect_kwargs)


def database_has_content() -> bool:
    db_config = load_db_config()

    try:
        server_conn = connect_mysql(db_config, include_database=False)
    except pymysql.MySQLError as exc:
        raise RuntimeError(
            "无法连接到 MySQL，请确认数据库服务已经启动，且 backend/config.yaml 中的账号密码正确。"
        ) from exc

    try:
        with server_conn.cursor() as cursor:
            cursor.execute(
                "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = %s",
                (db_config["database"],),
            )
            if cursor.fetchone() is None:
                print(f"数据库 {db_config['database']} 不存在，准备初始化数据。")
                return False
    finally:
        server_conn.close()

    try:
        db_conn = connect_mysql(db_config, include_database=True)
    except pymysql.MySQLError as exc:
        raise RuntimeError(
            f"数据库 {db_config['database']} 已存在，但无法连接，请检查配置。"
        ) from exc

    try:
        with db_conn.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE %s", ("buildings",))
            if cursor.fetchone() is None:
                print("未检测到 buildings 表，准备初始化数据。")
                return False

            cursor.execute("SELECT 1 FROM buildings LIMIT 1")
            has_rows = cursor.fetchone() is not None
            if has_rows:
                print("数据库中已存在建筑数据，跳过初始化写库。")
            else:
                print("buildings 表为空，准备初始化数据。")
            return has_rows
    finally:
        db_conn.close()


def run_command(command: list[str], cwd: Path, description: str) -> None:
    print(f"{description}：{' '.join(command)}")
    try:
        subprocess.run(command, cwd=str(cwd), check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(f"未找到命令 {command[0]}，请确认它已安装并加入 PATH。") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"{description} 失败，退出码：{exc.returncode}") from exc


def seed_database_if_needed() -> None:
    if database_has_content():
        return

    if not SQL_SCRIPT_PATH.exists():
        raise RuntimeError(f"未找到初始化脚本：{SQL_SCRIPT_PATH}")

    run_command(
        [sys.executable, str(SQL_SCRIPT_PATH)],
        cwd=ROOT_DIR,
        description="执行数据库初始化脚本",
    )


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def ensure_frontend_dependencies() -> None:
    node_modules_dir = FRONTEND_DIR / "node_modules"
    if node_modules_dir.exists():
        print("检测到 frontend/node_modules，跳过 npm install。")
        return

    run_command(
        [npm_command(), "install"],
        cwd=FRONTEND_DIR,
        description="安装前端依赖",
    )


def start_process(command: list[str], cwd: Path, name: str) -> subprocess.Popen[Any]:
    print(f"启动{name}：{' '.join(command)}")
    try:
        return subprocess.Popen(command, cwd=str(cwd))
    except FileNotFoundError as exc:
        raise RuntimeError(f"启动{name}失败，未找到命令 {command[0]}。") from exc


def stop_process(name: str, process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return

    print(f"正在停止{name}...")
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
        return

    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def monitor_processes(processes: dict[str, subprocess.Popen[Any]]) -> int:
    exit_code = 0
    try:
        while True:
            for name, process in processes.items():
                current_code = process.poll()
                if current_code is not None:
                    print(f"{name} 已退出，退出码：{current_code}")
                    exit_code = current_code
                    return exit_code
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n收到中断信号，正在关闭服务...")
        return exit_code
    finally:
        for name, process in reversed(list(processes.items())):
            stop_process(name, process)


def main() -> int:
    if not BACKEND_DIR.exists():
        raise RuntimeError(f"未找到后端目录：{BACKEND_DIR}")
    if not FRONTEND_DIR.exists():
        raise RuntimeError(f"未找到前端目录：{FRONTEND_DIR}")

    seed_database_if_needed()
    ensure_frontend_dependencies()

    backend_process = start_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "main:app",
            "--reload",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
        ],
        cwd=BACKEND_DIR,
        name="后端服务",
    )

    frontend_process = start_process(
        [npm_command(), "run", "dev"],
        cwd=FRONTEND_DIR,
        name="前端服务",
    )

    print("后端默认地址：http://localhost:8000")
    print("前端默认地址：http://localhost:5173")
    print("按 Ctrl+C 可同时关闭前后端服务。")

    return monitor_processes(
        {
            "前端服务": frontend_process,
            "后端服务": backend_process,
        }
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"启动失败：{exc}", file=sys.stderr)
        raise SystemExit(1)
