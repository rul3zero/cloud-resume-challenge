"""
Resume Download Handler Module
Handles resume download tracking with reCAPTCHA verification and S3 presigned URLs
"""

import json
import os
from datetime import datetime, timezone, timedelta


def handle_resume_download(event, headers, verify_recaptcha_func, get_dynamodb_table_func, 
                           get_sns_client_func, get_visitor_ip_func, unix_to_philippine_time_func,
                           sns_topic_arn, get_s3_client_func):
    """Handle resume download tracking with reCAPTCHA verification and S3 presigned URL generation"""
    try:
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        token = body.get('token', '')
        action = body.get('action', 'resume_download')
        
        # Get visitor IP
        visitor_ip = get_visitor_ip_func(event)
        
        print(f"Resume download request from IP: {visitor_ip}")
        
        # Verify reCAPTCHA
        recaptcha_result = verify_recaptcha_func(token)
        recaptcha_valid = recaptcha_result.get('success', False)
        score = recaptcha_result.get('score', 0.0)
        
        print(f"reCAPTCHA verification: valid={recaptcha_valid}, score={score}")
        
        # Check if this is a valid download (score threshold)
        download_allowed = recaptcha_valid and score >= 0.5
        
        if download_allowed:
            # Increment download count
            download_count = increment_resume_downloads(
                visitor_ip, 
                get_dynamodb_table_func, 
                get_sns_client_func,
                unix_to_philippine_time_func,
                sns_topic_arn
            )
            
            # Generate presigned S3 URL for resume download
            download_url = generate_resume_presigned_url(get_s3_client_func)
            
            response_body = {
                'success': True,
                'downloadAllowed': True,
                'downloadCount': download_count,
                'downloadUrl': download_url,
                'expiresIn': 300,  # URL expires in 5 minutes
                'score': score,
                'message': 'Download verified successfully'
            }
        else:
            # Get current count without incrementing
            download_count = get_resume_download_count(get_dynamodb_table_func, unix_to_philippine_time_func)
            
            response_body = {
                'success': False,
                'downloadAllowed': False,
                'downloadCount': download_count,
                'score': score,
                'message': 'Download verification failed'
            }
        
        print(f"Resume download response: {json.dumps(response_body)}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        print(f"ERROR in handle_resume_download: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'success': False,
                'downloadAllowed': False,
                'message': 'Internal server error'
            })
        }


def generate_resume_presigned_url(get_s3_client_func, expiration=300):
    """Generate a presigned URL for resume download from S3"""
    try:
        s3_client = get_s3_client_func()
        bucket_name = os.environ.get('RESUME_BUCKET_NAME')
        file_key = os.environ.get('RESUME_FILE_KEY', 'resume.pdf')
        
        if not bucket_name:
            raise ValueError('RESUME_BUCKET_NAME environment variable not set')
        
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key,
                'ResponseContentDisposition': 'attachment; filename="Joshua_Carl_Soguilon_Resume.pdf"'
            },
            ExpiresIn=expiration
        )
        
        print(f"Generated presigned URL for {bucket_name}/{file_key}")
        return presigned_url
        
    except Exception as e:
        print(f"ERROR generating presigned URL: {str(e)}")
        raise


def increment_resume_downloads(visitor_ip, get_dynamodb_table_func, get_sns_client_func,
                               unix_to_philippine_time_func, sns_topic_arn):
    """Increment resume download counter"""
    table = get_dynamodb_table_func()
    
    try:
        # Update the resume download counter
        response = table.update_item(
            Key={'id': 'resume_downloads'},
            UpdateExpression='ADD #count :inc SET last_updated = :timestamp, last_updated_ph = :timestamp_ph',
            ExpressionAttributeNames={
                '#count': 'count'
            },
            ExpressionAttributeValues={
                ':inc': 1,
                ':timestamp': int(datetime.now().timestamp()),
                ':timestamp_ph': unix_to_philippine_time_func(int(datetime.now().timestamp()))
            },
            ReturnValues='UPDATED_NEW'
        )
        
        new_count = int(response['Attributes']['count'])
        print(f"Resume download count incremented to: {new_count}")
        
        # Track individual download with IP and timestamp (for analytics)
        track_download_event(visitor_ip, new_count, get_dynamodb_table_func, unix_to_philippine_time_func)
        
        # Send SNS notification for milestone downloads (every 10 downloads)
        if new_count % 10 == 0:
            send_download_milestone_notification(new_count, get_sns_client_func, sns_topic_arn)
        
        return new_count
        
    except Exception as e:
        print(f"ERROR incrementing resume downloads: {str(e)}")
        return get_resume_download_count(get_dynamodb_table_func, unix_to_philippine_time_func)


def get_resume_download_count(get_dynamodb_table_func, unix_to_philippine_time_func):
    """Get current resume download count"""
    table = get_dynamodb_table_func()
    
    try:
        response = table.get_item(Key={'id': 'resume_downloads'})
        
        if 'Item' in response:
            return int(response['Item'].get('count', 0))
        else:
            # Initialize if doesn't exist
            table.put_item(Item={
                'id': 'resume_downloads',
                'count': 0,
                'last_updated': int(datetime.now().timestamp()),
                'last_updated_ph': unix_to_philippine_time_func(int(datetime.now().timestamp()))
            })
            return 0
            
    except Exception as e:
        print(f"ERROR getting resume download count: {str(e)}")
        return 0


def track_download_event(visitor_ip, download_number, get_dynamodb_table_func, unix_to_philippine_time_func):
    """Track individual download event for analytics"""
    table = get_dynamodb_table_func()
    
    try:
        # Create a download event record
        timestamp = int(datetime.now().timestamp())
        event_id = f"download_{timestamp}_{visitor_ip.replace('.', '_')}"
        
        table.put_item(Item={
            'id': event_id,
            'type': 'resume_download',
            'visitor_ip': visitor_ip,
            'download_number': download_number,
            'timestamp': timestamp,
            'timestamp_ph': unix_to_philippine_time_func(timestamp),
            'ttl': timestamp + (90 * 24 * 60 * 60)  # Keep for 90 days
        })
        
        print(f"Download event tracked: {event_id}")
        
    except Exception as e:
        print(f"ERROR tracking download event: {str(e)}")


def send_download_milestone_notification(download_count, get_sns_client_func, sns_topic_arn):
    """Send SNS notification for download milestones"""
    try:
        sns = get_sns_client_func()
        
        message = f"""
Resume Download Milestone Reached!

Total Downloads: {download_count}
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Congratulations on reaching this milestone!
        """.strip()
        
        sns.publish(
            TopicArn=sns_topic_arn,
            Subject=f'🎉 Resume Download Milestone: {download_count} Downloads',
            Message=message
        )
        
        print(f"Sent milestone notification for {download_count} downloads")
        
    except Exception as e:
        print(f"ERROR sending milestone notification: {str(e)}")
