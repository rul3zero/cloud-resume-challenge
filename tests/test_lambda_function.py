import pytest
import json
import os
from moto import mock_aws
import boto3
from unittest.mock import patch
import sys
from pathlib import Path

# Set environment variables BEFORE importing lambda function
os.environ['DYNAMODB_TABLE'] = 'visitor-counter'
os.environ['SNS_TOPIC_ARN'] = 'arn:aws:sns:ap-southeast-1:123456789012:test'
os.environ['RECAPTCHA_SECRET_KEY'] = 'test-secret-key'
os.environ['AWS_DEFAULT_REGION'] = 'ap-southeast-1'

# Add lambda directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'lambda'))

from lambda_function import (
    verify_recaptcha,
    get_client_ip,
    is_duplicate_visitor,
    record_visitor_ip,
    get_visitor_count,
    increment_visitor_count,
    send_sns_notification,
    lambda_handler,
)

@pytest.fixture(scope="module", autouse=True)
def aws_resources():
    # Moto mocks
    with mock_aws():
        # DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
        table = dynamodb.create_table(
            TableName='visitor-counter',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        # Initialize visitor count
        table.put_item(Item={'id': 'visitors', 'count': 0})

        # SNS topic
        sns = boto3.client('sns', region_name='ap-southeast-1')
        sns.create_topic(Name='test')

        yield

def test_get_client_ip():
    event = {
        'headers': {'X-Forwarded-For': '192.168.1.1'},
        'requestContext': {'identity': {'sourceIp': '10.0.0.1'}}
    }
    assert get_client_ip(event) == '192.168.1.1'
    event2 = {
        'headers': {},
        'requestContext': {'identity': {'sourceIp': '10.0.0.2'}}
    }
    assert get_client_ip(event2) == '10.0.0.2'

@patch('lambda_function.verify_recaptcha')
def test_lambda_handler_success(mock_verify):
    # Mock valid reCAPTCHA
    mock_verify.return_value = {'success': True, 'score': 0.9}
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({'token': 'fake_token'}),
        'headers': {'X-Forwarded-For': '192.168.1.10'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.10'}}
    }
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    assert resp['statusCode'] == 200
    assert body['success'] is True
    assert body['count'] >= 1
    assert body['duplicate'] is False
    assert body['score'] > 0.5

def test_lambda_handler_read_only():
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({'readOnly': True}),
        'headers': {},
        'requestContext': {'identity': {'sourceIp': '192.168.1.50'}}
    }
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    assert resp['statusCode'] == 200
    assert body['success'] is True
    assert body['message'].startswith('Count fetched')

def test_duplicate_visitor_logic():
    ip = '192.168.1.200'
    # Initially not a duplicate
    assert is_duplicate_visitor(ip) is False
    record_visitor_ip(ip, hours=24)
    # Now it is a duplicate
    assert is_duplicate_visitor(ip) is True

def test_increment_and_get_count():
    initial = get_visitor_count()
    assert isinstance(initial, int)
    count = increment_visitor_count()
    assert count == initial + 1

def test_sns_notification():
    # Should not raise error
    send_sns_notification(100)

def test_options_handler():
    event = {'httpMethod': 'OPTIONS'}
    resp = lambda_handler(event, None)
    assert resp['statusCode'] == 200
    assert resp['body'] == ''

def test_invalid_event_error_handling():
    event = {'httpMethod': 'POST', 'body': 'invalid_json'}
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    assert resp['statusCode'] == 200
    assert body['success'] is True

@patch('lambda_function.verify_recaptcha')
def test_lambda_handler_low_score(mock_verify):
    mock_verify.return_value = {'success': True, 'score': 0.1}
    event = {
        'httpMethod': 'POST',
        'body': json.dumps({'token': 'fake_token'}),
        'headers': {'X-Forwarded-For': '192.168.1.15'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.15'}}
    }
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    assert body['message'] == 'Invalid reCAPTCHA'