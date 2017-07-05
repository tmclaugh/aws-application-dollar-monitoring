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

def _sanitize_item(item):
    '''
    Handle value constraints of DynamoDB
    '''
    # DynamoDB can't have empty strings but csv.DictReader earlier in system
    # uses '' for empty fields.
    for key, value in item.items():
        if value == '':
            item[key] = None
    return item

def handler(event, context):
    '''
    Retrieve Billing data from SNS and add to DynamoDB Table.
    '''
    _logger.info('SNS event received: {}'.format(json.dumps(event)))

    # Start inserting DynamoDB entries
    dynamodb_resource = boto3.resource('dynamodb')
    dynamodb_table = dynamodb_resource.Table(DYNAMODB_TABLE_NAME)

    for record in event.get('Records'):
        sns_data = record.get('Sns')
        sns_message_string = sns_data.get('Message')
        sns_messages = json.loads(sns_message_string)

        # FIXME: Debating batching messages upstream. Remove this if we decide
        # this is the way forward.
        if type(sns_messages) == dict:
            sns_messages = [sns_messages]

        with dynamodb_table.batch_writer() as batch:
            for message in sns_messages:
                sanitized_message = _sanitize_item(message)
                _logger.info('Sending item to DynamoDB: {}'.format(json.dumps(sanitized_message)))
                batch.put_item(Item=message)

    return
