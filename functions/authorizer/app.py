import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    logger.info("event = " + str(event))
    return {
        "isAuthorized": True
    }
