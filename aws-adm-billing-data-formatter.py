import boto3
import csv
import json
import logging
from logging.config import fileConfig
import os
import sys

dirname = os.path.dirname(__file__)
logging_conf = os.path.join(dirname, 'logging.conf')
fileConfig(logging_conf, disable_existing_loggers=False)
if os.environ.get('DEBUG'):
    logging.root.setLevel(level=logging.DEBUG)
_logger = logging.getLogger(__name__)

SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
SNS_MESSAGE_BATCH_SIZE = int(os.environ.get('SNS_MESSAGE_BATCH_SIZE', 100))

def _convert_empty_value_to_none(item):
    '''
    Turn empty strings into None, etc.

    DynamoDB can't have empty strings but csv.DictReader earlier in system
    uses '' for empty fields.
    '''
    for key, value in item.items():
        if value == '':
            item[key] = None
    return item

def _is_billing_item(item):
    '''
    Check if item is a billing line item or report data.

    All billing data has a RecordId.   While this does weed out some items
    that cannot be inserted into DynamoDB, that is not this function's
    intended purpose.
    '''
    return item.get('RecordId') != None

def _item_to_dictionary(keys, values):
    '''
    Given a list of keys abd values, return a dictionary.
    '''
    return dict(zip(keys, values))

def _publish_items_to_sns(items):
    sns_client = boto3.client('sns')
    resp = sns_client.publish(TopicArn=SNS_TOPIC_ARN, Message=json.dumps(items))
    return resp

def _sanitize_item(item):
    '''
    Do some record sanity checking.

    Returns corrected data, or None if is not billing line Item.
    '''
    item = _convert_empty_value_to_none(item)
    if not _is_billing_item(item):
        item = None

    return item

def handler(event, context):
    '''
    Sanitize data and convert into a usable format for processing.
    '''
    _logger.info('S3 event received: {}'.format(json.dumps(event)))
    item_list = []
    for record in event.get('Records'):
        sns_data = record.get('Sns')
        sns_message_string = sns_data.get('Message')

        # Message should bee a JSON list item, header should be position 0.
        # We'll need to turn each line into a list of values.
        split_line_strings = json.loads(sns_message_string)

        keys_string = split_line_strings.pop(0).strip()
        keys = []
        for key in keys_string.split(','):
            keys.append(key.strip('"'))
        _logger.debug('keys: {}'.format(json.dumps(keys)))

        for line_string in split_line_strings:
            line = []
            for l in line_string.split(','):
                line.append(l.strip('"'))
            item_dict = _item_to_dictionary(keys, line)
            sanitized_item = _sanitize_item(item_dict)
            _logger.debug('sanitized_item: {}'.format(json.dumps(sanitized_item)))
            if sanitized_item:
                item_list.append(sanitized_item)

    _logger.debug('item_list: {}'.format(json.dumps(item_list)))

    # batch items and publish to SNS
    batch_size = SNS_MESSAGE_BATCH_SIZE
    batched_items = [
        item_list[i:i + batch_size] for i in range(0, len(item_list), batch_size)
    ]
    _logger.debug('batched_items: {}'.format(json.dumps(batched_items)))

    sns_response_list = []
    for items in batched_items:
        _logger.debug('Publishing items to SNS: {}'.format(items))
        resp = _publish_items_to_sns(items)
        _logger.debug('SNS publish response: ()'.format(json.dumps(resp)))
        sns_response_list.append(resp)

    return sns_response_list

