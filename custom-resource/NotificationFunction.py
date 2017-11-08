from __future__ import print_function
import boto3
from botocore.vendored import requests
import json
import logging
import os
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)
topic_arn = os.environ['topic_arn']
approval_url= os.environ['approval_url']+'?waitUrl='
sns   = boto3.resource('sns')
topic = sns.Topic(topic_arn)
responseData = {'Staus':'Completed'}

def lambda_handler(event, context):
  #logger.info(json.dumps(event))
  if event['RequestType'] != 'Create':
    sendResponse(event, context,'SUCCESS',responseData)
    return
  wait_url=event['ResourceProperties']['WaitUrl'].encode()
  email_id=event['ResourceProperties']['EmailID']
  encoded_url=base64.b64encode(wait_url);
  response = topic.publish(
  Subject='Request for approval to launch Stack for Product',
  Message='Hi Admin, \n\
    An user has launched a stack. \n\
    End-user Email ID : '+email_id+
    '\nKindly approve by clicking the below URL.\n\n'+
         approval_url+encoded_url.decode()+
    '\n\nPlease ignore if you dont want the stack to be launched.\n\
    Thanks,\n\
    Product Approval Team\n')
  sendResponse(event, context,'SUCCESS',responseData)

def sendResponse(event, context, responseStatus, responseData):
  response_body={'Status': responseStatus,
          'Reason': 'See the details in CloudWatch Log Stream ' + context.log_stream_name,
          'PhysicalResourceId': context.log_stream_name ,
          'StackId': event['StackId'],
          'RequestId': event['RequestId'],
          'LogicalResourceId': event['LogicalResourceId'],
          'Data': responseData}
  try:
    response = requests.put(event['ResponseURL'],
                      data=json.dumps(response_body))
    return True
  except Exception as e:
    logger.info("Failed executing HTTP request: {}".format(e.code))
  return False
