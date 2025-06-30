import requests
import os
import shutil
import sys
import subprocess
import json
import time
import logging

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'updater_config.json')

"""Логирование"""
LOG_PATH = os.path.join(os.path.dirname(__file__), 'updater.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)  # Чтобы видеть и в консоли
    ]
)

logger = logging.getLogger(__name__)



def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_remote_versions(config):
    update_server = config["update_server"]
    url = update_server.rstrip('/') + "/versions.json"
    resp = requests.get(url, timeout=10)
    return json.loads(resp.text)

def download_new_exe(exe_name, config):
    update_server = config["update_server"]
    remote_prefix = config.get("remote_path_prefix", "")
    url = f"{update_server.rstrip('/')}/{remote_prefix.strip('/')}/{exe_name}"
    logger.info(f"Скачиваю: {url}")

    resp = requests.get(url, stream=True, timeout=30)
    logger.info(f"HTTP статус: {resp.status_code} {resp.reason}")
    if resp.status_code != 200:
        raise Exception(f"Ошибка загрузки: {resp.status_code} {resp.reason}")

    new_name = os.path.join(os.path.dirname(__file__), exe_name.replace('.exe', '_new.tmp'))
    logger.info(f"Будет сохранён как: {new_name}")

    with open(new_name, "wb") as f:
        shutil.copyfileobj(resp.raw, f)
        logger.info("Копирование новой версии завершено")

    return new_name



def update_client(config, remote_versions):
    local_ver = config["local_client_version"]
    remote_ver = remote_versions.get("client")
    exe_name = config["client_exe"]
    current_dir = os.path.dirname(__file__)
    exe_path = os.path.abspath(os.path.join(current_dir, exe_name))

    logger.info(f"Ожидаемый путь к текущему Клиент.exe: {exe_path}")

    if remote_ver != local_ver:
        logger.info(f"Доступно обновление клиента: {local_ver} -> {remote_ver}")
        new_name = download_new_exe(exe_name, config)
        logger.info(f"Заменяю {exe_path} ← {new_name}")
        if replace_exe(exe_path, new_name) == 0:
            update_config_version("local_client_version", remote_ver)
    else:
        logger.info("Обновление клиента не требуется.")


def update_server(config, remote_versions):
    local_ver = config["local_server_version"]
    remote_ver = remote_versions.get("server")
    exe_name = config["server_exe"]
    service_name = config["server_service_name"]
    current_dir = os.path.dirname(__file__)
    exe_path = os.path.abspath(os.path.join(current_dir, exe_name))
    if remote_ver != local_ver:
        logger.info(f"Доступно обновление сервера: {local_ver} -> {remote_ver}")
        new_name = download_new_exe(exe_name, config)
        logger.info(f"Заменяю {exe_path} ← {new_name}")
        logger.info("Останавливаю сервис...")
        subprocess.run(["sc", "stop", service_name], check=False)
        time.sleep(4)
        if replace_exe(exe_path, new_name) == 0:
            logger.info("Обновляю версию сервера...")
            update_config_version("local_server_version", remote_ver)
        logger.info("Запускаю сервис...")
        subprocess.run(["sc", "start", service_name], check=False)
    else:
        logger.info("Обновление сервера не требуется.")

def restart_service(service_name):
    # Останавливаем службу
    subprocess.run(["sc", "stop", service_name], check=False)
    time.sleep(3)
    # Запускаем службу
    subprocess.run(["sc", "start", service_name], check=False)

def update_config_version(key, new_version):
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        config[key] = new_version

        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        logger.info(f"{key} обновлён до версии {new_version}")
    except Exception as e:
        logger.info(f"Не удалось обновить конфигурацию: {e}")


def replace_exe(exe_name, new_name):
    try:
        exe_path = os.path.abspath(exe_name)
        os.replace(new_name, exe_path)
        return 0
    except Exception as e:
        logger.info(f"Ошибка при замене: {e}")
        return 1






def main():
    try:
        config = load_config()
        # check_update_flag_and_patch_config(config)
        remote_versions = get_remote_versions(config)
        logger.info("Проверяю обновления...")
        update_client(config, remote_versions)
        update_server(config, remote_versions)
        logger.info("Проверка завершена.")
    except Exception as e:
        logger.info(f"Ошибка обновления: {e}")


if __name__ == "__main__":
    main() 
