import sys
import time

import os
import logging
from http import HTTPStatus

import requests
import telegram

from dotenv import load_dotenv

load_dotenv()

FORMATTER = logging.Formatter("%(time)s — %(name)s — %(level)s — %(message)s")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
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
        except Exception as error:
            logger.error(f'Сбой при отправке сообщения в Telegram: {error}')


def get_api_answer(current_timestamp):
    """Делает запрос к эндпоинту API - сервиса Яндекс Практикум."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        logger.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        message = f'Ошибка при запросе к API.' \
                  f' Код ответа: {response.status_code}'
        logger.error(message)
        raise Exception(message)
    return response.json()


def check_response(response):
    """Распаковывает словарь ответа API, получает первый экземпляр списка."""
    try:
        homeworks = response.get('homeworks')
    except IndexError as error:
        logger.error(
            f'Ошибка при получении списка с домашним заданием: {error}'
        )
    except KeyError as error:
        logger.error(
            f'Ошибка при получении списка с домашним заданием: {error}'
        )
    except Exception as error:
        logger.error(
            f'Ошибка при получении списка с домашним заданием: {error}'
        )
    if not isinstance(response, dict):
        return Exception('<response> не словарь')
    elif not isinstance(response['homeworks'], list):
        raise Exception('<response[homeworks]> не список')
    return homeworks


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    """
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    message = (
        f'Недокументированный статус домашней работы {homework_name}'
    )
    logger.error(message)
    raise Exception(message)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if (PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID) is None:
        return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    if check_tokens() is False:
        logger.critical(
            'Отсутствует обязательная переменная окружения,'
            'программа принудительно остановлена.'
        )
        sys.exit()

    while True:
        try:
            response = get_api_answer(current_timestamp)
            if response.get('homeworks') is not []:
                homeworks = check_response(response)
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
