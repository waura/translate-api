import json
import base64
import boto3
import datetime
import calendar
from functools import reduce
import os
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

CHARACTER_COUNT_SUM_LIMIT = float(os.getenv('CHARACTER_COUNT_SUM_LIMIT', default=490000))
translate = boto3.client('translate')
cloudwatch = boto3.client('cloudwatch')

def get_character_count_sum():
    now = datetime.datetime.now()
    endDayOfMonth = calendar.monthrange(now.year, now.month)[1]

    # get metric data per day
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'characterCountSum',
                'Expression': "SUM(SEARCH('MetricName=\"CharacterCount\"', 'Sum', 86400))"
            },
        ],
        StartTime=datetime.datetime(now.year, now.month, 1, 0, 0, 0),
        EndTime=datetime.datetime(now.year, now.month, endDayOfMonth, 23, 59, 59)
    )

    metricDataResults = list(filter(lambda x : x['Id'] == 'characterCountSum', response['MetricDataResults']))

    characterCountSum = 0.0
    for result in metricDataResults:
        characterCountSum += reduce(lambda a, b : a + b, result['Values'])
    
    return characterCountSum

def get_error_response(code, name, message):
    return {
        "statusCode": code,
        "body": {
            "error": name,
            "message": message
        }
    }

def lambda_handler(event, context):
    logger.info(event)

    characterCountSum = get_character_count_sum()
    logger.info('characterCountSum = ' + str(characterCountSum))

    # judge threshold
    if characterCountSum >= CHARACTER_COUNT_SUM_LIMIT:
        return get_error_response(403, "CharacterCountLimitExceeded", "Monthly character count limit was exceeded. Plase retry after some time.")

    # check parameter
    if not 'body' in event:
        return get_error_response(400, "InvalidParameter", "Request body isn't exist.")

    # translate text
    params = {}
    if event['isBase64Encoded']:
        params = json.loads(base64.b64decode(event['body']).decode())
    else:
        params = json.loads(event['body'])

    try:
        response = translate.translate_text(
            Text=params['Text'],
            SourceLanguageCode=params['SourceLanguageCode'],
            TargetLanguageCode=params['TargetLanguageCode']
        )
        logger.info("translate_text response = " + str(response))
        return {
            "statusCode": 200,
            "body": json.dumps({
                    "TranslatedText": response['TranslatedText'],
                    "SourceLanguageCode": response['SourceLanguageCode'],
                    "TargetLanguageCode": response['TargetLanguageCode']
                }, ensure_ascii=False)
        }
    except Exception as e:
        logger.error(e)
        return get_error_response(500, "Unknown", "Unknown error occured.")

