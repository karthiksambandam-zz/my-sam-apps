import boto3
import json
import os

client = boto3.client('ec2')
def handler(event,context):
  response = client.describe_volumes(Filters=[
       { 'Name': 'tag:'+ os.environ['tag_key'],
            'Values': [ os.environ['tag_value'] ]
        },])
  for volume in response['Volumes']:
    volume_id = volume['VolumeId']
    response = client.create_snapshot(VolumeId=volume_id)
  return 'completed'
