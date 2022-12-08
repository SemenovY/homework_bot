import os
import requests
import telegram
import time
import logging
from telegram.ext import Updater, Filters, MessageHandler
from dotenv import load_dotenv

load_dotenv()

# Здесь задана глобальная конфигурация для логирования
logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    filemode='w'
)

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


def check_tokens():
    """Проверяем доступность переменных окружения, которые необходимы для работы программы."""
    if PRACTICUM_TOKEN is None:
        logging.critical('Нет PRACTICUM_TOKEN.')
        return False
    if TELEGRAM_TOKEN is None:
        logging.critical('Нет TELEGRAM_TOKEN.')
        return False
    if TELEGRAM_CHAT_ID is None:
        logging.critical('Нет TELEGRAM_CHAT_ID.')
        return False
    return True


def send_message(bot, message):
    """Отправляем сообщение в Telegram чат, определяемый переменной окружения TELEGRAM_CHAT_ID.
    Принимает на вход два параметра: экземпляр класса Bot и строку с текстом сообщения."""
    logging.debug('Удачная отправка сообщения в Telegram')
    logging.error('Сбой при отправке сообщения в Telegram')
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        homework_statuses = homework_statuses.json()
        return homework_statuses
    except Exception as error:
        logging.exception(f'Ошибка при запросе к основному API: {error}')



def check_response(response):
    """Проверяем ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError("в response не словарь")
    if not isinstance(response['homeworks'], list):
        raise TypeError("в значаниях словаря не список")
    if not response.get('homeworks'):
        raise KeyError("в response нет ключа с домашками")


def parse_status(homework):
    """Извлекаем из информации о конкретной домашней работе статус этой работы.
    Далее функция возвращает подготовленную для отправки в Telegram строку,
    содержащую один из вердиктов словаря HOMEWORK_VERDICTS."""
    homework_status = homework[0].get('status')
    homework_name = homework[0].get('homework_name')
    verdict = HOMEWORK_VERDICTS[homework_status]
    for key in HOMEWORK_VERDICTS:
        if key == homework_status:
            return f'Изменился статус проверки работы "{homework_name}". {verdict}'
        logging.error('Неожиданный статус домашней работы, обнаруженный в ответе API')


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    updater = Updater(token=TELEGRAM_TOKEN)
    # timestamp = int(time.time())
    timestamp = 1667504569
    # while check_tokens():
    #     try:
    #         response = (get_api_answer(timestamp))
    #         if check_response(response['homeworks']):
    #             message = parse_status(response['homeworks'])
    #             print('до проверки')
    #             updater.dispatcher.add_handler(MessageHandler(Filters.text, send_message(bot, message)))
    #             print('после проверки')
    #             updater.start_polling(poll_interval=20.0)
    #             print('после апдейта')
    #             # Бот будет работать до тех пор, пока не нажмете Ctrl-C
    #             updater.idle()
    #     except Exception as error:
    #         message = f'Сбой в работе программы: {error}'
    #         print(message)

    if check_tokens():
        response = (get_api_answer(timestamp))
        if check_response(response['homeworks']):
            message = parse_status(response['homeworks'])
            # Регистрируется обработчик MessageHandler;
            updater.dispatcher.add_handler(MessageHandler(Filters.text, send_message(bot, message)))
        else:
            # Метод start_polling() запускает процесс polling,
            # приложение начнёт отправлять регулярные запросы для получения обновлений.
            updater.start_polling(poll_interval=20.0)
            # Бот будет работать до тех пор, пока не нажмете Ctrl-C
            updater.idle()
    else:
        print('Сбой в работе программы')


if __name__ == '__main__':
    main()
