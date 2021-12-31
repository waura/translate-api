import json
import base64
import boto3
import datetime
from functools import reduce
import os

CHARACTER_COUNT_SUM_LIMIT = float(os.getenv('CHARACTER_COUNT_SUM_LIMIT', default=490000))
translate = boto3.client('translate')
cloudwatch = boto3.client('cloudwatch')

def get_character_count_sum():
    # get metric data per day
    response = cloudwatch.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'characterCountSum',
                'Expression': "SUM(SEARCH('MetricName=\"CharacterCount\"', 'Sum', 86400))"
            },
        ],
        StartTime=datetime.datetime(2021, 12, 1, 0, 0, 0),
        EndTime=datetime.datetime(2021, 12, 31, 23, 59, 59)
    )

    metricDataResults = list(filter(lambda x : x['Id'] == 'characterCountSum', response['MetricDataResults']))

    characterCountSum = 0.0
    for result in metricDataResults:
        characterCountSum += reduce(lambda a, b : a + b, result['Values'])
    
    return characterCountSum

def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    characterCountSum = get_character_count_sum()
    print('characterCountSum = ' + str(characterCountSum))

    # judge threshold
    if characterCountSum >= CHARACTER_COUNT_SUM_LIMIT:
        return {
            "statusCode": 403,
            "body": {
                "error": "CharacterCountLimitExceeded",
                "message": "Monthly character count limit was exceeded. Plase retry after some time."
            }
        }

    # translate text
    params = {}
    if event['isBase64Encoded']:
        params = json.loads(base64.b64decode(event['body']).decode())
    else:
        params = json.loads(event['body'])

    response = translate.translate_text(
        Text=params['Text'],
        SourceLanguageCode=params['SourceLanguageCode'],
        TargetLanguageCode=params['TargetLanguageCode']
    )

    return {
        "statusCode": 200,
        "body": json.dumps(response)
    }
