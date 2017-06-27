import boto3
import csv
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

def _fetch_billing_file(bucket, key):
    '''
    Fetch a file from a URL and return a file-like object.
    '''
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
    # We assume that events are properly filtered at the trigger level.
    event_records = event.get('Records')

    # NOTE: These are used only in testing events.
    start_line_item = event.get('StartLineItem')
    end_line_item = event.get('EndLineItem')

    billing_data_total = []
    for record in event_records:
        s3_info = record.get('s3')
        s3_bucket = s3_info.get('bucket').get('name')
        s3_key = s3_info.get('object').get('key')

        billing_file = _fetch_billing_file(s3_bucket, s3_key)
        billing_data = csv.DictReader(billing_file)

        return billing_data_total.extend(billing_data)

    return billing_data_total[start_line_item:end_line_item]


