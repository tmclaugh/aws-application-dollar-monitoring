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

def _extract_file_object(fileobj, filename):
    '''
    Return an uncompressed file object
    '''
    zip_file = zipfile.ZipFile(fileobj)
    return zip_file.open(filename)

def _fetch_object(bucket, key):
    '''
    Fetch a file from a URL and return a file-like object.
    '''
    _logger.debug('Fetching object; Bucket={}, Key={}'.format(bucket, key))
    s3_client = boto3.client('s3')
    s3_object = s3_client.get_object(Bucket=bucket, Key=key)
    s3_object_body = s3_object.get('Body').read()

    # Turn stream bytes into a file-like object
    zip_file = io.BytesIO(s3_object_body)

    return zip_file

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
    billing_data_total = []
    for record in event_records:
        _logger.debug('processing record: {}'.format(json.dumps(record)))
        s3_info = record.get('s3')
        s3_bucket = s3_info.get('bucket').get('name')
        s3_key = s3_info.get('object').get('key')

        billing_file_zip = _fetch_object(s3_bucket, s3_key)
        billing_file = _extract_file_object(
            billing_file_zip,
            '.'.join(s3_key.split('.')[:-1])
        )
        billing_data_items = csv.DictReader(billing_file)

        billing_data = []
        for row in billing_data_items:
            billing_data.append(row)

        _logger.debug(
            'billing data: {}'.format(
                json.dumps(billing_data[start_line_item:end_line_item])
            )
        )
        billing_data_total.extend(billing_data)

    return billing_data_total[start_line_item:end_line_item]


