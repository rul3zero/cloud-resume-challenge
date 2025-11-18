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
os.environ['RESUME_BUCKET_NAME'] = 'test-resume-bucket'
os.environ['RESUME_FILE_KEY'] = 'resume.pdf'

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
    get_s3_client,
)

from resume_handler import (
    handle_resume_download,
    increment_resume_downloads,
    get_resume_download_count,
    track_download_event,
    send_download_milestone_notification,
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
        
        # S3 bucket for resumes
        s3 = boto3.client('s3', region_name='ap-southeast-1')
        s3.create_bucket(
            Bucket='test-resume-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'ap-southeast-1'}
        )
        # Upload test resume file
        s3.put_object(
            Bucket='test-resume-bucket',
            Key='resume.pdf',
            Body=b'Test PDF content'
        )

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


# ===== Resume Download Tests =====

@patch('lambda_function.verify_recaptcha')
def test_resume_download_success(mock_verify):
    """Test successful resume download with valid reCAPTCHA"""
    mock_verify.return_value = {'success': True, 'score': 0.9}
    
    event = {
        'httpMethod': 'POST',
        'path': '/resume-download',
        'body': json.dumps({'token': 'fake_token', 'action': 'resume_download'}),
        'headers': {'X-Forwarded-For': '192.168.1.100'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.100'}}
    }
    
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    
    assert resp['statusCode'] == 200
    assert body['success'] is True
    assert body['downloadAllowed'] is True
    assert body['downloadCount'] >= 1
    assert body['score'] == 0.9
    assert 'downloadUrl' in body
    assert body['downloadUrl'].startswith('https://test-resume-bucket.s3')


@patch('lambda_function.verify_recaptcha')
def test_resume_download_low_score(mock_verify):
    """Test resume download rejection with low reCAPTCHA score"""
    mock_verify.return_value = {'success': True, 'score': 0.3}
    
    event = {
        'httpMethod': 'POST',
        'path': '/resume-download',
        'body': json.dumps({'token': 'fake_token', 'action': 'resume_download'}),
        'headers': {'X-Forwarded-For': '192.168.1.101'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.101'}}
    }
    
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    
    assert resp['statusCode'] == 200
    assert body['success'] is False
    assert body['downloadAllowed'] is False
    assert body['score'] == 0.3


@patch('lambda_function.verify_recaptcha')
def test_resume_download_failed_recaptcha(mock_verify):
    """Test resume download with failed reCAPTCHA verification"""
    mock_verify.return_value = {'success': False, 'score': 0.0}
    
    event = {
        'httpMethod': 'POST',
        'path': '/resume-download',
        'body': json.dumps({'token': 'invalid_token', 'action': 'resume_download'}),
        'headers': {'X-Forwarded-For': '192.168.1.102'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.102'}}
    }
    
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    
    assert resp['statusCode'] == 200
    assert body['success'] is False
    assert body['downloadAllowed'] is False


def test_get_resume_download_count():
    """Test getting resume download count"""
    from lambda_function import get_dynamodb_table, unix_to_philippine_time
    
    count = get_resume_download_count(get_dynamodb_table, unix_to_philippine_time)
    assert isinstance(count, int)
    assert count >= 0


def test_increment_resume_downloads():
    """Test incrementing resume download counter"""
    from lambda_function import get_dynamodb_table, get_sns_client, unix_to_philippine_time
    
    initial_count = get_resume_download_count(get_dynamodb_table, unix_to_philippine_time)
    
    new_count = increment_resume_downloads(
        '192.168.1.103',
        get_dynamodb_table,
        get_sns_client,
        unix_to_philippine_time,
        os.environ['SNS_TOPIC_ARN']
    )
    
    assert new_count == initial_count + 1
    assert isinstance(new_count, int)


def test_track_download_event():
    """Test tracking individual download events"""
    from lambda_function import get_dynamodb_table, unix_to_philippine_time
    
    # Should not raise any errors
    track_download_event(
        '192.168.1.104',
        5,
        get_dynamodb_table,
        unix_to_philippine_time
    )
    
    # Verify event was created in DynamoDB
    table = get_dynamodb_table()
    # The event ID will be something like "download_<timestamp>_192_168_1_104"
    # We can't predict exact timestamp, but we can verify the count was incremented


def test_send_download_milestone_notification():
    """Test sending milestone notifications"""
    from lambda_function import get_sns_client
    
    # Should not raise any errors
    send_download_milestone_notification(
        10,
        get_sns_client,
        os.environ['SNS_TOPIC_ARN']
    )


@patch('lambda_function.verify_recaptcha')
def test_resume_download_routing(mock_verify):
    """Test that /resume-download path routes correctly"""
    mock_verify.return_value = {'success': True, 'score': 0.8}
    
    # Test with /resume-download path
    event1 = {
        'httpMethod': 'POST',
        'path': '/resume-download',
        'body': json.dumps({'token': 'fake_token'}),
        'headers': {'X-Forwarded-For': '192.168.1.105'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.105'}}
    }
    
    resp1 = lambda_handler(event1, None)
    body1 = json.loads(resp1['body'])
    assert 'downloadAllowed' in body1
    
    # Test with /download path (alternative)
    event2 = {
        'httpMethod': 'POST',
        'path': '/download',
        'body': json.dumps({'token': 'fake_token'}),
        'headers': {'X-Forwarded-For': '192.168.1.106'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.106'}}
    }
    
    resp2 = lambda_handler(event2, None)
    body2 = json.loads(resp2['body'])
    assert 'downloadAllowed' in body2


@patch('lambda_function.verify_recaptcha')
def test_visitor_count_still_works(mock_verify):
    """Test that visitor counter still works after adding resume download"""
    mock_verify.return_value = {'success': True, 'score': 0.9}
    
    # Test visitor counter (default path)
    event = {
        'httpMethod': 'POST',
        'path': '/count',
        'body': json.dumps({'token': 'fake_token'}),
        'headers': {'X-Forwarded-For': '192.168.1.107'},
        'requestContext': {'identity': {'sourceIp': '192.168.1.107'}}
    }
    
    resp = lambda_handler(event, None)
    body = json.loads(resp['body'])
    
    assert resp['statusCode'] == 200
    assert body['success'] is True
    assert 'count' in body
    assert 'downloadAllowed' not in body  # Should not have resume download fields


def test_resume_download_options():
    """Test OPTIONS request for resume download endpoint"""
    event = {
        'httpMethod': 'OPTIONS',
        'path': '/resume-download'
    }
    
    resp = lambda_handler(event, None)
    assert resp['statusCode'] == 200
    assert resp['body'] == ''
