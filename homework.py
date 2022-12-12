"""Проверка домашки."""
import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import OutCustomException, WrongResponseCode

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID_TELEGRAM')
PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(funcName)s, %(lineno)d, %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяем доступность переменных окружения."""
    not_tokens = []
    for item in ('PRACTICUM_TOKEN', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID'):
        if not globals()[item]:
            not_tokens.append(item)
    error_message = ', '.join(not_tokens)
    if error_message:
        logger.critical(f'Отсутствует обязательная переменная '
                        f'окружения: {error_message}', exc_info=True)
        return False
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат."""
    try:
        send = bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug('Cообщение в Telegram было отправлено')
        return send

    except Exception as errors:
        logger.error(f'Ошибка при отправке сообщения в Telegram: {errors}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=payload
        )
        if response.status_code != HTTPStatus.OK:
            error = (f'Эндпоинт {ENDPOINT} недоступен.'
                     f'Код ответа API: {response.status_code}'
                     )
            raise WrongResponseCode(error)
        return response.json()
    except Exception as errors:
        logger.error(f'Ошибка при запросе к основному API: {errors}')
        raise WrongResponseCode(f'Ошибка при запросе к API: {errors}')


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logger.error('в ответе API не словарь')
        raise TypeError('В ответе API не словарь')
    if 'homeworks' not in response:
        logger.error('список домашних работ пуст, '
                     'в response нет ключа homeworks', exc_info=True)
        raise KeyError('В response нет ключа homeworks ')
    if 'current_date' not in response:
        logger.error('список домашних работ пуст, '
                     'в response нет ключа current_date', exc_info=True)
        raise KeyError('В response нет ключа current_date')
    if not isinstance(response['homeworks'], list):
        logger.error('в словаре не список')
        raise TypeError('В словаре не список')

    return response


def parse_status(homework):
    """Извлекаем из информации о конкретной домашней работе статус этой работы.
    Далее функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS.
    """
    try:
        if 'homework_name' not in homework:
            logger.error('В response нет ключа homework_name')
            raise KeyError('В response нет ключа homework_name')
        if 'status' not in homework:
            logger.error('В response нет ключа status')
            raise KeyError('В response нет ключа status')

        resp = (f'Изменился статус проверки работы '
                f'"{homework.get("homework_name")}". '
                f'{HOMEWORK_VERDICTS[homework.get("status")]}'
                )
        keys = ['approved', 'reviewing', 'rejected']
        for key in HOMEWORK_VERDICTS:
            if key not in keys:
                raise KeyError(f'В response нет ключа {key}')
            if key == homework.get('status'):
                logger.info(resp)
                return resp

    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        logger.error('Неожиданный статус домашней работы в ответе API')
        raise OutCustomException(f'Неожиданный статус работы в API {message}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(1)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            timestamp = response.get('current_date')
            homeworks = response.get('homeworks')
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
                logging.debug('Сообщение о новом статусе было отправлено')
            else:
                logger.debug('Новых статусов нет')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
