import sys
import os
import socket
import subprocess
import time
import configparser
import psutil
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QLabel, QPushButton, QLineEdit, QMessageBox)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QPainter, QColor
from loguru import logger

class SplashScreen(QWidget):
    def __init__(self, logo_path, logo_size, duration):
        super().__init__()
        logger.info(f"Инициализация сплэш-скрина: logo_path={logo_path}, size={logo_size}, duration={duration}")
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Создаем layout
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Создаем и настраиваем логотип
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.logo_label)
        
        # Загружаем и устанавливаем логотип
        if not os.path.exists(logo_path):
            logger.error(f"Файл логотипа не найден: {logo_path}")
            raise FileNotFoundError(f"Файл логотипа не найден: {logo_path}")
            
        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            logger.error(f"Не удалось загрузить логотип: {logo_path}")
            raise ValueError(f"Не удалось загрузить логотип: {logo_path}")
            
        scaled_pixmap = pixmap.scaled(logo_size, logo_size, Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation)
        self.logo_label.setPixmap(scaled_pixmap)
        
        # Настройка анимации
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # Таймер для закрытия сплэша
        self.close_timer = QTimer()
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.close)
        self.close_timer.start(duration)
        logger.info("Сплэш-скрин инициализирован")
        
    def showEvent(self, event):
        super().showEvent(event)
        self.animation.start()
        logger.info("Сплэш-скрин показан")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EKiller Client")
        self.setFixedSize(400, 300)
        
        # Настройка логирования
        log_path = os.path.join(os.path.expanduser("~"), "Documents", "ekiller", "log.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        logger.add(log_path, rotation="1 day", retention="7 days")
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Статус подключения
        self.status_label = QLabel("Статус: Отключено")
        layout.addWidget(self.status_label)
        
        # Поле ввода имени процесса
        self.process_input = QLineEdit()
        self.process_input.setPlaceholderText("Введите имя процесса")
        layout.addWidget(self.process_input)
        
        # Кнопка завершения процесса
        self.kill_button = QPushButton("Завершить процесс")
        self.kill_button.clicked.connect(self.kill_process)
        layout.addWidget(self.kill_button)
        
        # Инициализация сокета
        self.socket = None
        self.connected = False
        
        # Таймер для проверки подключения
        self.connection_timer = QTimer()
        self.connection_timer.timeout.connect(self.check_connection)
        self.connection_timer.start(5000)
        
        # Подключение к серверу
        self.connect_to_server()
        
    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('localhost', 5000))
            self.connected = True
            self.status_label.setText("Статус: Подключено")
            logger.info("Подключено к серверу")
        except Exception as e:
            self.connected = False
            self.status_label.setText("Статус: Ошибка подключения")
            logger.error(f"Ошибка подключения к серверу: {e}")
            
    def check_connection(self):
        if not self.connected:
            self.connect_to_server()
            
    def kill_process(self):
        if not self.connected:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к серверу")
            return
            
        process_name = self.process_input.text().strip()
        if not process_name:
            QMessageBox.warning(self, "Ошибка", "Введите имя процесса")
            return
            
        try:
            # Отправка команды на сервер
            self.socket.send(f"kill:{process_name}".encode('utf-8'))
            logger.info(f"Отправлена команда завершения процесса: {process_name}")
            
            # Ожидание ответа от сервера
            response = self.socket.recv(1024).decode('utf-8')
            if response == "ok-taskkill":
                # Поиск полного пути к исполняемому файлу
                process_path = None
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    if proc.info['name'].lower() == process_name.lower():
                        process_path = proc.info['exe']
                        break
                
                if process_path:
                    # Запуск приложения с полным путем
                    subprocess.Popen([process_path])
                    logger.info(f"Запущено приложение: {process_path}")
                else:
                    # Если путь не найден, пробуем запустить по имени
                    subprocess.Popen([process_name])
                    logger.info(f"Запущено приложение по имени: {process_name}")
                
                # Ожидание 5 секунд
                time.sleep(5)
                
                # Отправка подтверждения
                self.socket.send("taskstart-ok".encode('utf-8'))
                logger.info("Отправлено подтверждение запуска")
                
                QMessageBox.information(self, "Успех", "Процесс успешно завершен и перезапущен")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось завершить процесс")
                
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {e}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {str(e)}")
            
    def closeEvent(self, event):
        if self.socket:
            self.socket.close()
        event.accept()

class EKillerClient:
    def __init__(self, config_path):
        logger.info(f"Инициализация клиента с конфигурацией: {config_path}")
        if not os.path.exists(config_path):
            logger.error(f"Файл конфигурации не найден: {config_path}")
            raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")
            
        self.config = self.load_config(config_path)
        self.setup_logging()
        self.socket = None
        self.connected = False
        self.process_name = self.config['Process']['name']
        logger.info(f"Клиент инициализирован, процесс для завершения: {self.process_name}")
        
    def load_config(self, config_path):
        config = configparser.ConfigParser()
        try:
            config.read(config_path)
            logger.info("Конфигурация успешно загружена")
            return config
        except Exception as e:
            logger.error(f"Ошибка при загрузке конфигурации: {e}")
            raise
            
    def setup_logging(self):
        try:
            # Используем os.path.expandvars для корректной обработки переменных окружения
            log_path = os.path.expandvars(self.config['Logging']['log_path'])
            # Заменяем прямые слеши на обратные для Windows
            log_path = log_path.replace('/', os.path.sep)
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            logger.add(
                log_path,
                rotation=self.config['Logging']['rotation'],
                retention=self.config['Logging']['retention']
            )
            logger.info(f"Логирование настроено: {log_path}")
        except Exception as e:
            logger.error(f"Ошибка при настройке логирования: {e}")
            raise
            
    def connect_to_server(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            host = self.config['Server']['host']
            port = int(self.config['Server']['port'])
            logger.info(f"Подключение к серверу {host}:{port}")
            self.socket.connect((host, port))
            self.connected = True
            logger.info("Подключено к серверу")
            return True
        except Exception as e:
            self.connected = False
            logger.error(f"Ошибка подключения к серверу: {e}")
            return False
            
    def kill_process(self):
        if not self.connected:
            logger.error("Нет подключения к серверу")
            return False
            
        try:
            # Отправка команды на сервер
            command = f"kill:{self.process_name}"
            logger.info(f"Отправка команды на сервер: {command}")
            self.socket.send(command.encode('utf-8'))
            
            # Ожидание ответа от сервера
            logger.info("Ожидание ответа от сервера")
            response = self.socket.recv(1024).decode('utf-8')
            logger.info(f"Получен ответ от сервера: {response}")
            
            if response == "ok-taskkill":
                # Получаем путь к программе из настроек
                process_path = self.config['Process']['path']
                process_path = process_path.replace('/', os.path.sep)
                
                if os.path.exists(process_path):
                    logger.info(f"Запуск программы по указанному пути: {process_path}")
                    subprocess.Popen([process_path])
                else:
                    logger.warning(f"Указанный путь не существует: {process_path}")
                    # Пробуем найти программу в системе
                    found_path = None
                    for proc in psutil.process_iter(['pid', 'name', 'exe']):
                        if proc.info['name'].lower() == self.process_name.lower():
                            found_path = proc.info['exe']
                            break
                    
                    if found_path:
                        logger.info(f"Найден путь к программе: {found_path}")
                        subprocess.Popen([found_path])
                    else:
                        logger.warning(f"Путь к программе не найден, пробуем запустить по имени: {self.process_name}")
                        subprocess.Popen([self.process_name])
                
                # Ожидание указанной задержки
                delay = int(self.config['Process']['restart_delay'])
                logger.info(f"Ожидание {delay} секунд перед отправкой подтверждения")
                time.sleep(delay)
                
                # Отправка подтверждения
                self.socket.send("taskstart-ok".encode('utf-8'))
                logger.info("Отправлено подтверждение запуска")
                return True
            else:
                logger.error(f"Неожиданный ответ от сервера: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при выполнении команды: {e}")
            return False
            
    def close(self):
        if self.socket:
            logger.info("Закрытие соединения с сервером")
            self.socket.close()

def main():
    try:
        logger.info("Запуск клиента")
        app = QApplication(sys.argv)
        
        # Создаем клиент для загрузки конфигурации
        client = EKillerClient('settings_c.inf')
        
        # Создаем и показываем сплэш-скрин
        splash = SplashScreen(
            logo_path=client.config['Splash']['logo_path'],
            logo_size=int(client.config['Splash']['logo_size']),
            duration=int(client.config['Splash']['duration'])
        )
        splash.show()
        
        # Ждем завершения сплэш-скрина
        logger.info("Ожидание завершения сплэш-скрина")
        while splash.isVisible():
            app.processEvents()
        
        # Подключаемся к серверу и выполняем команду
        logger.info("Начало выполнения основной логики")
        if client.connect_to_server():
            client.kill_process()
        
        # Закрываем клиент
        client.close()
        
        # Завершаем приложение
        logger.info("Завершение работы клиента")
        app.quit()
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 