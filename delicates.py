import logging
import time
import requests
import os
import sys
from http import HTTPStatus
from dotenv import load_dotenv
from exceptions import WrongResponseCode, OutCustomException, NegativeValueException

load_dotenv()

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
    '%(asctime)s, %(name)s, %(filename)s, %(funcName)s, %(levelname)s, %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    if PRACTICUM_TOKEN is None:
        logger.critical(f'Нет {PRACTICUM_TOKEN}.')
        return False
    logger.info('PRACTICUM_TOKEN доступен, все ок')
    return True


def get_api_answer(timestamp):
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if homework_statuses.status_code != HTTPStatus.OK:
            logger.error(f'Ответ API не возвращает {HTTPStatus.OK}')
            raise WrongResponseCode(f'Ответ API не возвращает {HTTPStatus.OK}')
        homework_statuses = homework_statuses.json()
        logger.info(f'Получили ответ от API, все ок')
        return homework_statuses
    except Exception as errors:
        logger.exception(f'Ошибка при запросе к основному API: {errors}')


def check_response(response):
    if not isinstance(response, dict):
        raise TypeError('В ответе API не словарь')
    if not isinstance(response['homeworks'], list):
        raise TypeError('В словаре не список')
    if not response.get('homeworks'):
        raise KeyError('Список домашних работ пуст')
    logger.info('ответ API соответстветствует документации, все ок')
    return True


def parse_status(homework):
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
        raise OutCustomException(f'Неожиданный статус домашней работы, обнаруженный в ответе API {message}')


def main():
    # timestamp = int(time.time())
    timestamp = 0
    while True:
        try:
            response = (get_api_answer(timestamp))
            if check_response(response):
                message = parse_status(response['homeworks'])
                logger.info(message)
            time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.info(message)


if __name__ == '__main__':
    if check_tokens():
        main()
    else:
        logger.critical('Нет PRACTICUM_TOKEN.')
        raise NegativeValueException('Нет PRACTICUM_TOKEN.')
