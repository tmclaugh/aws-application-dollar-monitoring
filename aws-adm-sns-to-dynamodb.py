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
        sns_messages = json.loads(sns_message_string)

        # Debating batching messages upstream.
        if type(sns_messages) == dict:
            sns_messages = [sns_messages]

        for message in sns_messages:
            # DynamoDB can't have empty strings but csv.DictReader uses '' for
            # empty fields.
            for key, value in message.items():
                if value == '':
                    message[key] = None
            _logger.info('Sending item to DynamoDB: {}'.format(json.dumps(message)))
            resp = dynamodb_table.put_item(Item=message)
            _logger.debug(
                'dynamodb response: {}'.format(
                    json.dumps(resp)
                )
            )
            dynamodb_client_responses.append(resp)

    return dynamodb_client_responses
