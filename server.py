import socket
import threading
import queue
import time
from loguru import logger
import psutil
import os
import configparser

class EKillerServer:
    def __init__(self, config_path='settings.inf'):
        # Чтение настроек
        config = configparser.ConfigParser()
        if os.path.exists(config_path):
            config.read(config_path)
            host = config.get('Server', 'host', fallback='127.0.0.1')
            port = config.getint('Server', 'port', fallback=5000)
        else:
            host = '127.0.0.1'
            port = 5000
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = []
        self.command_queue = queue.Queue()
        self.running = False
        
        # Настройка логирования
        logger.add("server.log", rotation="1 day", retention="7 days")
        
    def start(self):
        """Запуск сервера"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            logger.info(f"Сервер запущен на {self.host}:{self.port}")
            
            # Запуск обработчика очереди команд
            queue_thread = threading.Thread(target=self.process_command_queue)
            queue_thread.daemon = True
            queue_thread.start()
            
            # Основной цикл принятия подключений
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"Новое подключение от {address}")
                    
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    self.clients.append(client_thread)
                    
                except Exception as e:
                    logger.error(f"Ошибка при принятии подключения: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка запуска сервера: {e}")
            self.stop()
            
    def stop(self):
        """Остановка сервера"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("Сервер остановлен")
        
    def handle_client(self, client_socket, address):
        """Обработка клиентского подключения"""
        try:
            while self.running:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                logger.info(f"Получена команда от {address}: {data}")
                # Новый формат: <username>_kill:имя_процесса
                if "_kill:" in data:
                    try:
                        user_part, process_part = data.split('_kill:')
                        process_name = process_part
                        username = user_part
                        self.command_queue.put((client_socket, process_name, username))
                    except Exception as e:
                        logger.error(f"Ошибка парсинга команды: {data}, {e}")
                elif data == "taskstart-ok":
                    logger.info(f"Клиент {address} подтвердил запуск приложения")
        except Exception as e:
            logger.error(f"Ошибка при обработке клиента {address}: {e}")
        finally:
            client_socket.close()
            logger.info(f"Соединение с {address} закрыто")
            
    def process_command_queue(self):
        """Обработка очереди команд"""
        while self.running:
            try:
                if not self.command_queue.empty():
                    # Теперь очередь содержит username
                    item = self.command_queue.get()
                    if len(item) == 3:
                        client_socket, process_name, username = item
                    else:
                        client_socket, process_name = item
                        username = "unknown"
                    # Завершение процесса во всех сессиях
                    self.kill_process(process_name, username)
                    logger.info("Ожидание 2 секунды после завершения процесса")
                    time.sleep(2)
                    client_socket.send("ok-taskkill".encode('utf-8'))
                    while True:
                        try:
                            data = client_socket.recv(1024).decode('utf-8')
                            if data == "taskstart-ok":
                                break
                        except:
                            break
                    time.sleep(5)
            except Exception as e:
                logger.error(f"Ошибка при обработке очереди команд: {e}")
                
    def kill_process(self, process_name, username="unknown"):
        """Завершение процесса во всех сессиях с логированием пользователя"""
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    try:
                        proc.kill()
                        logger.info(f"Пользователь {username}: процесс {process_name} (PID: {proc.info['pid']}) завершён")
                    except psutil.NoSuchProcess:
                        pass
                    except psutil.AccessDenied:
                        logger.warning(f"Нет прав для завершения процесса {process_name}")
        except Exception as e:
            logger.error(f"Ошибка при завершении процесса {process_name}: {e}")

if __name__ == "__main__":
    server = EKillerServer('settings.inf')
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop() 