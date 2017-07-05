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

SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
SNS_MESSAGE_BATCH_SIZE = int(os.environ.get('SNS_MESSAGE_BATCH_SIZE', 100))

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

def handler(event, context):
    '''
    Retrieve billing data from S3 and send data to SNS topic.
    '''
    _logger.info('S3 event received: {}'.format(json.dumps(event)))
    # We assume that events are properly filtered at the trigger level.
    event_records = event.get('Records')

    # NOTE: These are used only in testing events.
    start_line_item = event.get('StartLineItem')
    end_line_item = event.get('EndLineItem')

    for record in event_records:
        _logger.info('processing record: {}'.format(json.dumps(record)))
        s3_info = record.get('s3')
        s3_bucket = s3_info.get('bucket').get('name')
        s3_key = s3_info.get('object').get('key')

        billing_file_zip = _fetch_s3_file_object(s3_bucket, s3_key)
        billing_file = _extract_zip_file_object(
            billing_file_zip,
            '.'.join(s3_key.split('.')[:-1])
        )

        sns_publish_responses = []
        file_header = billing_file.readline()

        eof_unreached = True
        while True and eof_unreached:
            lines = [file_header]
            for x in range(SNS_MESSAGE_BATCH_SIZE):
                line = billing_file.readline()
                if line:
                    lines.append(line.strip())
                else:
                    eof_unreached = False
                    break

            _logger.info(
                'Publishing message to SNS: {} billing items'.format(len(lines) - 1)
            )
            _logger.debug(
                'Publishing item to SNS: {}'.format(
                    json.dumps(lines)
                )
            )

            sns_client = boto3.client('sns')
            resp = sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject='AWS billing data: {} items'.format(len(lines) - 1),
                Message=json.dumps(lines)
            )
            _logger.debug('SNS publish response: ()'.format(json.dumps(resp)))
            sns_publish_responses.append(resp)

        return sns_publish_responses
