"""Проверка домашки"""
import os
import sys
import requests
import telegram
import time
import logging
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import WrongResponseCode, OutCustomException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID_TELEGRAM')
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
    '%(asctime)s, %(levelname)s, %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяем доступность переменных окружения,
    которые необходимы для работы программы."""

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
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code != HTTPStatus.OK:
            logger.error(f'Ответ API не возвращает {HTTPStatus.OK}')
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
    if 'homeworks' not in response or 'current_date' not in response:
        logger.error('список домашних работ пуст')
        raise KeyError('В response нет ключа homeworks')
    if not isinstance(response['homeworks'], list):
        logger.error('в словаре не список')
        raise TypeError('В словаре не список')

    if response.get('homeworks'):
        return response


def parse_status(homework):
    """Извлекаем из информации о конкретной домашней работе статус этой работы.
    Далее функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS."""
    try:
        if 'homework_name' not in homework:
            logger.error('В response нет ключа homework_name')
            raise KeyError('В response нет ключа homework_name')
        if 'status' not in homework:
            logger.error('В response нет ключа status')
            raise KeyError('В response нет ключа status')
        homework_status = homework.get('status')
        homework_name = homework.get('homework_name')
        verdict = HOMEWORK_VERDICTS[homework_status]
        for key in HOMEWORK_VERDICTS:
            if key == homework_status:
                logger.info(f'Изменился статус проверки работы'
                            f'{homework_name}. {verdict}')
                return (f'Изменился статус проверки работы'
                        f'{homework_name}. {verdict}')
    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        logger.error('Неожиданный статус домашней работы в ответе API')
        raise OutCustomException(f'Неожиданный статус работы в API {message}')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        message = 'Отсутствуют переменные окружения!'
        logger.critical(message)
        sys.exit()
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
            logger.error(message, exc_info=True)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
