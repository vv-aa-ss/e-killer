import requests
import os
import shutil
import sys
import subprocess
import json
import time

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'updater_config.json')
UPDATE_SERVER = "http://192.168.87.3:54321"


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_remote_versions():
    url = UPDATE_SERVER + "/versions.json"
    resp = requests.get(url, timeout=10)
    return json.loads(resp.text)

def download_new_exe(exe_name, config):
    # Получаем имя файла и добавляем remote_path_prefix, если есть
    remote_prefix = config.get("remote_path_prefix", "")
    url = f"{UPDATE_SERVER.rstrip('/')}/{remote_prefix.strip('/')}/{exe_name}"
    print(f"Скачиваю: {url}")

    resp = requests.get(url, stream=True, timeout=30)
    print(f"HTTP статус: {resp.status_code} {resp.reason}")
    if resp.status_code != 200:
        raise Exception(f"Ошибка загрузки: {resp.status_code} {resp.reason}")

    new_name = os.path.join(os.path.dirname(__file__), exe_name.replace('.exe', '_new.exe'))
    print(f"Будет сохранён как: {new_name}")

    with open(new_name, "wb") as f:
        shutil.copyfileobj(resp.raw, f)
        print("Копирование новой версии завершено")

    return new_name


def update_client(config, remote_versions):
    local_ver = config["local_client_version"]
    remote_ver = remote_versions.get("client")
    exe_name = config["client_exe"]
    current_dir = os.path.dirname(__file__)
    exe_path = os.path.abspath(os.path.join(current_dir, exe_name))

    print(f"Ожидаемый путь к текущему .exe: {exe_path}")

    if remote_ver and remote_ver != local_ver:
        print(f"Доступно обновление клиента: {local_ver} -> {remote_ver}")
        new_name = download_new_exe(exe_name, config)
        print(f"Заменяю {exe_path} ← {new_name}")
        os.replace(new_name, exe_path)
        print("Клиент обновлён. Перезапуск...")
        subprocess.Popen([exe_path] + sys.argv[1:])
        sys.exit(0)
    else:
        print("Обновление клиента не требуется.")



def replace_exe(exe_name, new_name):
    exe_path = os.path.abspath(exe_name)
    os.replace(new_name, exe_path)

def restart_service(service_name):
    # Останавливаем службу
    subprocess.run(["sc", "stop", service_name], check=False)
    time.sleep(3)
    # Запускаем службу
    subprocess.run(["sc", "start", service_name], check=False)

def update_server(config, remote_versions):
    local_ver = config["local_server_version"]
    remote_ver = remote_versions.get("server")
    exe_name = config["server_exe"]
    service_name = config["server_service_name"]
    if remote_ver and remote_ver != local_ver:
        print(f"Доступно обновление сервера: {local_ver} -> {remote_ver}")
        new_name = download_new_exe(exe_name)
        replace_exe(exe_name, new_name)
        print("Сервер обновлён. Перезапуск службы...")
        restart_service(service_name)
    else:
        print("Обновление сервера не требуется.")

def main():
    try:
        config = load_config()
        remote_versions = get_remote_versions()
        print("Проверяю обновления...")
        update_client(config, remote_versions)
        update_server(config, remote_versions)
        print("Проверка завершена.")
    except Exception as e:
        print(f"Ошибка обновления: {e}")

if __name__ == "__main__":
    main() 
