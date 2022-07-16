import os
import sys

import time
import logging
import requests
import json
import telegram

from http import HTTPStatus
from dotenv import load_dotenv
from telegram import TelegramError

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
strfmt = '[%(asctime)s] [%(name)s] [%(levelname)s] > %(message)s'
datefmt = '%Y-%m-%d %H:%M:%S'
FORMATTER = logging.Formatter(fmt=strfmt, datefmt=datefmt)
handler.setFormatter(FORMATTER)
logger.addHandler(handler)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

last_message = ''


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    global last_message
    if message != last_message:
        try:
            bot.send_message(TELEGRAM_CHAT_ID, message)
            logger.info(f'Сообщение <{message}> отправлено в телеграм')
            last_message = message
        except TelegramError as error:
            logger.error(f'Сбой при отправке сообщения в Telegram: {error}')
            raise Exception(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API - сервиса Яндекс Практикум."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK:
            return response.json()
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        logger.error(f'Http Error: {error}')
        raise Exception(f'Http Error: {error}')
    except requests.exceptions.ConnectionError as error:
        logger.error(f'Error Connecting: {error}')
        raise Exception(f'Error Connecting: {error}')
    except requests.exceptions.Timeout as error:
        logger.error(f'Timeout Error: {error}')
        raise Exception(f'Timeout Error: {error}')
    except requests.exceptions.RequestException as error:
        logger.critical(f'{ENDPOINT} не отвечает: {error}')
        sys.exit()
    except json.decoder.JSONDecodeError:
        logger.error('Не в формате JSON')
        raise Exception('Не в формате JSON')


def check_response(response):
    """Распаковывает словарь ответа API."""
    homeworks = response['homeworks']
    if not response:
        logger.error('Ответ API пустой словарь')
        raise Exception('Ответ API пустой словарь')
    if not isinstance(response['homeworks'], list):
        logger.error('<response[homeworks]> не список')
        raise Exception('<response[homeworks]> не список')
    return homeworks


def parse_status(homework):
    """Извлекает из информации о домашней работе статус этой работы."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        message = f'Отсутствует ключ: {error}'
        logger.error(message)
        raise KeyError(message)
    if homework_status not in HOMEWORK_STATUSES:
        message = 'Неверный или отсутствует ключ homework_status'
        logger.error(message)
        raise KeyError(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID) is None:
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if not check_tokens():
        logger.critical(
            'Отсутствует обязательная переменная окружения,'
            'программа принудительно остановлена.'
        )
        sys.exit()

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) != 0:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            current_timestamp = response.get('current_date')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        else:
            logger.info('Программа работает в штатном режиме')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
