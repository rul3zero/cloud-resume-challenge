import json
import boto3
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import os
from datetime import datetime, timedelta, timezone

# Initialize constants
RECAPTCHA_SECRET = os.environ.get('RECAPTCHA_SECRET_KEY', '')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', 'arn:aws:sns:ap-southeast-1:637423537833:visitor-counter-alert')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE', 'visitor-counter')

# Lazy initialization for AWS clients
_dynamodb = None
_sns = None
_table = None

def get_dynamodb_table():
    """Get or create DynamoDB table resource"""
    global _dynamodb, _table
    if _table is None:
        _dynamodb = boto3.resource('dynamodb')
        _table = _dynamodb.Table(DYNAMODB_TABLE)
    return _table

def get_sns_client():
    """Get or create SNS client"""
    global _sns
    if _sns is None:
        _sns = boto3.client('sns')
    return _sns

def verify_recaptcha(token):
    """Verify reCAPTCHA token with Google"""
    if not RECAPTCHA_SECRET or not token:
        return {'success': False, 'score': 0.0}
    
    url = 'https://www.google.com/recaptcha/api/siteverify'
    data = urllib.parse.urlencode({
        'secret': RECAPTCHA_SECRET,
        'response': token
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data, method='POST')
        response = urllib.request.urlopen(req, timeout=5)
        result = json.loads(response.read().decode())
        return result
    except Exception as e:
        print(f"reCAPTCHA verification error: {str(e)}")
        return {'success': False, 'score': 0.0}

def get_client_ip(event):
    """Extract client IP from API Gateway event"""
    try:
        headers = event.get('headers', {})
        
        # Try X-Forwarded-For first
        x_forwarded_for = headers.get('X-Forwarded-For') or headers.get('x-forwarded-for')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        
        # Fallback to sourceIp
        request_context = event.get('requestContext', {})
        identity = request_context.get('identity', {})
        return identity.get('sourceIp', 'unknown')
    except Exception as e:
        print(f"Error getting IP: {str(e)}")
        return 'unknown'

def is_duplicate_visitor(ip, hours=24):
    """Check if IP has visited within the last N hours"""
    try:
        table = get_dynamodb_table()
        response = table.get_item(Key={'id': f'ip:{ip}'})
        if 'Item' in response:
            print(f"Duplicate visitor: {ip}")
            return True
        return False
    except Exception as e:
        print(f"Error checking duplicate: {str(e)}")
        return False

def record_visitor_ip(ip, hours=24):
    """Record visitor IP with TTL"""
    try:
        table = get_dynamodb_table()
        now = datetime.now()
        now_ts = int(now.timestamp())
        ttl_ts = int((now + timedelta(hours=hours)).timestamp())

        table.put_item(
            Item={
                'id': f'ip:{ip}',
                # keep unix epoch timestamps for TTL and timestamp
                'timestamp': now_ts,
                'ttl': ttl_ts,
                # add human-readable Philippine time strings for display in DynamoDB
                'timestamp_ph': unix_to_philippine_time(now_ts),
                'ttl_ph': unix_to_philippine_time(ttl_ts)
            }
        )
        print(f"Recorded new visitor IP: {ip}")
    except Exception as e:
        print(f"Error recording IP: {str(e)}")

def increment_visitor_count():
    """Increment the global visitor count and check for threshold"""
    try:
        table = get_dynamodb_table()
        # prepare timestamp values
        now_ts = int(datetime.now().timestamp())
        now_ts_ph = unix_to_philippine_time(now_ts)

        response = table.update_item(
            Key={'id': 'visitors'},
            UpdateExpression='ADD #count :inc SET last_updated = :ts, last_updated_ph = :ts_ph',
            ExpressionAttributeNames={'#count': 'count'},
            ExpressionAttributeValues={':inc': 1, ':ts': now_ts, ':ts_ph': now_ts_ph},
            ReturnValues='ALL_NEW'
        )
        count = int(response['Attributes']['count'])
        print(f"Visitor count incremented to: {count}")
        
        # Check if count is divisible by 100
        if count % 20 == 0:
            send_sns_notification(count)
        
        return count
    except Exception as e:
        print(f"Error incrementing count: {str(e)}")
        return None

def send_sns_notification(count):
    """Send SNS notification when visitor count reaches threshold"""
    try:
        sns = get_sns_client()
        message = f"STATUS: Portfolio Website Visitor Counter: TOTAL VISITORS: {count}"
        sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject="Visitor Count Alert"
        )
        print(f"SNS notification sent: {message}")
    except Exception as e:
        print(f"Error sending SNS notification: {str(e)}")

def get_visitor_count():
    """Get current visitor count"""
    try:
        table = get_dynamodb_table()
        response = table.get_item(Key={'id': 'visitors'})
        if 'Item' in response:
            count = response['Item'].get('count', 0)
            print(f"Current visitor count: {count}")
            return int(count)
        
        # Initialize count if doesn't exist
        table.put_item(Item={'id': 'visitors', 'count': 0})
        return 0
    except Exception as e:
        print(f"Error getting count: {str(e)}")
        return 0

def lambda_handler(event, context):
    """Main Lambda handler"""
    
    print(f"Received event: {json.dumps(event)}")
    
    headers = {
        'Access-Control-Allow-Origin': 'https://joshcarl.dev',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Content-Type': 'application/json'
    }
    
    # Handle preflight OPTIONS request
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''
        }
    
    try:
        # Parse request body
        body_str = event.get('body', '{}')
        print(f"Request body: {body_str}")
        body = json.loads(body_str)
        
        token = body.get('token', '')
        read_only = body.get('readOnly', False)  # Check if read-only mode
        
        print(f"Token: {token[:20] if token else 'None'}..., ReadOnly: {read_only}")
        
        # Check if this is read-only mode (fallback)
        if read_only or token == 'fallback':
            print("Read-only mode: Only fetching count, no increment")
            count = get_visitor_count()
            
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({
                    'success': True,
                    'count': count,
                    'score': 0.0,
                    'duplicate': False,
                    'message': 'Count fetched (read-only)'
                })
            }
        
        # Normal mode: Verify reCAPTCHA
        score = 0.0
        recaptcha_valid = False
        
        if token:
            result = verify_recaptcha(token)
            if result.get('success'):
                score = result.get('score', 0.0)
                print(f"reCAPTCHA score: {score}")
                
                # Only increment if score is high enough (>= 0.5)
                if score >= 0.5:
                    recaptcha_valid = True
                else:
                    print(f"reCAPTCHA score too low ({score}), not incrementing")
            else:
                print("reCAPTCHA verification failed")
        
        # Get IP and check for duplicates (only if reCAPTCHA is valid)
        ip = get_client_ip(event)
        print(f"Client IP: {ip}")
        
        is_dup = False
        
        if recaptcha_valid:
            is_dup = is_duplicate_visitor(ip)
            
            # Only increment if reCAPTCHA valid AND not duplicate
            if not is_dup:
                record_visitor_ip(ip)
                increment_visitor_count()
                print("New valid visitor - count incremented")
            else:
                print("Duplicate visitor - count not incremented")
        else:
            print("Invalid reCAPTCHA - count not incremented")
        
        # Always return current count
        count = get_visitor_count()
        
        response_body = {
            'success': True,
            'count': count,
            'score': score,
            'duplicate': is_dup,
            'message': 'Duplicate visit' if is_dup else ('New visitor' if recaptcha_valid else 'Invalid reCAPTCHA')
        }
        
        print(f"Returning response: {json.dumps(response_body)}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        print(f"ERROR in lambda_handler: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Even on error, try to return the count
        try:
            count = get_visitor_count()
        except Exception as e2:
            print(f"ERROR getting fallback count: {str(e2)}")
            count = 0
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({
                'success': True,
                'count': count,
                'score': 0.0,
                'duplicate': False,
                'message': 'Error but returning count'
            })
        }

def unix_to_philippine_time(ts: int) -> str:

    dt_utc = datetime.fromtimestamp(ts, timezone.utc)
    # convert to Philippine timezone (UTC+8)
    philippine_tz = timezone(timedelta(hours=8))
    dt_ph = dt_utc.astimezone(philippine_tz)
    return dt_ph.strftime('%Y-%m-%d %H:%M:%S')
