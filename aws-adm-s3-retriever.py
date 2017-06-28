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

def _extract_zip_file_object(fileobj, filename):
    '''
    Return an uncompressed file-like string object.
    '''
    zip_file = zipfile.ZipFile(fileobj)
    file_data = zip_file.read(filename)
    file_data_string = file_data.decode()

    # We're dealing with CSV files so just convert to string here.
    return io.StringIO(file_data_string)

def _fetch_s3_file_object(bucket, key):
    '''
    Fetch a file from a URL and return a file-like byte object.
    '''
    _logger.debug('Fetching object; Bucket={}, Key={}'.format(bucket, key))
    s3_client = boto3.client('s3')
    s3_object = s3_client.get_object(Bucket=bucket, Key=key)
    s3_object_body = s3_object.get('Body').read()

    # Turn stream bytes into a file-like object
    zip_file = io.BytesIO(s3_object_body)

    return zip_file

def _get_billing_data_from_event_record(record, start_line_item=None, end_line_item=None):
    '''
    Get billing data
    '''
    # This will be a list of OrderedDict items from the csv.DictReader()
    _logger.debug('processing record: {}'.format(json.dumps(record)))
    s3_info = record.get('s3')
    s3_bucket = s3_info.get('bucket').get('name')
    s3_key = s3_info.get('object').get('key')

    billing_file_zip = _fetch_s3_file_object(s3_bucket, s3_key)
    billing_file = _extract_zip_file_object(
        billing_file_zip,
        '.'.join(s3_key.split('.')[:-1])
    )

    billing_data_items = csv.DictReader(billing_file)
    billing_data_items_list = []
    for row in billing_data_items:
        billing_data_items_list.append(row)

    _logger.debug(
        'billing data: {}'.format(
            json.dumps(billing_data_items_list)
        )
    )

    return billing_data_items_list[start_line_item:end_line_item]

def handler(event, context):
    '''
    Retrieve Billing data from S3 and send data to S3.
    '''
    _logger.info('S3 event received: {}'.format(json.dumps(event)))
    # We assume that events are properly filtered at the trigger level.
    event_records = event.get('Records')

    # NOTE: These are used only in testing events.
    start_line_item = event.get('StartLineItem')
    end_line_item = event.get('EndLineItem')

    # This will be a list of OrderedDict items from the csv.DictReader()
    billing_data_items_total = []
    for record in event_records:
        billing_data_items = _get_billing_data_from_event_record(
            record,
            start_line_item,
            end_line_item
        )

    billing_data_items_total.extend(billing_data_items)

    return billing_data_items_total
