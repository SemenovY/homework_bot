import os
import sys
import requests
import telegram
import time
import logging
from dotenv import load_dotenv
from http import HTTPStatus
from exceptions import WrongResponseCode, OutCustomException, NegativeValueException


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

# # Здесь задана глобальная конфигурация для логирования
# logging.basicConfig(
#     level=logging.INFO,
#     filename='program.log',
#     format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
#     filemode='w'
# )

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s, %(name)s, %(filename)s, %(funcName)s, %(levelname)s, %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяем доступность переменных окружения, которые необходимы для работы программы."""
    if PRACTICUM_TOKEN is None:
        logger.critical(f'Отсутствует обязательная переменная окружения: PRACTICUM_TOKEN.')
        return False
    if TELEGRAM_TOKEN is None:
        logger.critical('Отсутствует обязательная переменная окружения: TELEGRAM_TOKEN.')
        return False
    if TELEGRAM_CHAT_ID is None:
        logger.critical('Отсутствует обязательная переменная окружения: TELEGRAM_CHAT_ID.')
        return False
    logger.info('TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN доступен, все ок')
    return True


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
            raise WrongResponseCode(f'Ответ API не возвращает {HTTPStatus.OK}')
        response = response.json()
        logger.info(f'Получили ответ от API, все ок')
        logger.info(f'Привели его из формата JSON к типам данных Python - {response["homeworks"][0]}')
        return response
    except Exception as errors:
        logger.error(f'Ошибка при запросе к основному API: {errors}')


def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logger.error('отсутствие ожидаемых ключей в ответе API, в ответе API не словарь')
        raise TypeError('В ответе API не словарь')
    if not isinstance(response['homeworks'], list):
        logger.error('отсутствие ожидаемых ключей в ответе API, в словаре не список')
        raise TypeError('В словаре не список')
    if not response.get('homeworks'):
        logger.error('отсутствие ожидаемых ключей в ответе API, список домашних работ пуст')
        raise KeyError('Список домашних работ пуст')
    logger.info('ответ API соответстветствует документации, все ок')
    return True


def parse_status(homework):
    """Извлекаем из информации о конкретной домашней работе статус этой работы.
    Далее функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS."""
    try:
        logger.info('Запрашиваем статус домашки')
        homework_status = homework[0].get('status')
        homework_name = homework[0].get('homework_name')
        verdict = HOMEWORK_VERDICTS[homework_status]
        for key in HOMEWORK_VERDICTS:
            if key == homework_status:
                logger.info(f'Изменился статус проверки работы "{homework_name}". {verdict}')
                return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        message = f'Сбой в работе программы: {error}'
        logger.error('Неожиданный статус домашней работы, обнаруженный в ответе API')
        raise OutCustomException(f'Неожиданный статус домашней работы, обнаруженный в ответе API {message}')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    while True:
        try:
            response = (get_api_answer(timestamp))
            if check_response(response):
                message = parse_status(response['homeworks'])
                send_message(bot, message)
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            logger.info(f'Сбой в работе программы: {error}')


if __name__ == '__main__':
    if check_tokens():
        main()
    else:
        raise NegativeValueException('Отсутствует переменная окружения')
