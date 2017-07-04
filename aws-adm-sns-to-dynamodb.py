import boto3
import csv
import json
import logging
from logging.config import fileConfig
import io
import os
import sys
import zipfile

dirname = os.path.dirname(__file__)
logging_conf = os.path.join(dirname, 'logging.conf')
fileConfig(logging_conf, disable_existing_loggers=False)
if os.environ.get('DEBUG'):
    logging.root.setLevel(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

DYNAMODB_TABLE_NAME = os.environ.get('DYNAMODB_TABLE_NAME')

def handler(event, context):
    '''
    Retrieve Billing data from SNS and add to DynamoDB Table.
    '''
    _logger.info('SNS event received: {}'.format(json.dumps(event)))

    # Start inserting DynamoDB entries
    dynamodb_resource = boto3.resource('dynamodb')
    dynamodb_table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)
    dynamodb_client_responses = []

    for record in event.get('Records'):
        sns_data = record.get('Sns')
        sns_message_string = sns_data.get('Message')
        sns_message = json.loads(sns_message_string)
        # DynamoDB can't have empty strings but csv.DictReader uses '' for
        # empty fields.
        for key, value in sns_message.items():
            if value == '':
                sns_message[key] = None
        resp = dynamodb_table.put_item(Item=sns_message)
        _logger.debug(
            'dynamodb response: {}'.format(
                json.dumps(resp)
            )
        )
        dynamodb_client_responses.append(resp)

    return dynamodb_client_responses
