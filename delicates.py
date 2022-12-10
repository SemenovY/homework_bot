
def main():
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
