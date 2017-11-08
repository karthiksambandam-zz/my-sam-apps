import boto3
import json
import datetime
import os

client = boto3.client('ec2')

def handler(event, context):
    source_id = event['detail']['source']
    key=os.environ['tag_key']
    value=os.environ['tag_value']
    retention_type=os.environ['retention_type']
    retention_value=os.environ['retention_value']
    split_arr = source_id.split('/')
    vol_id = split_arr.pop()
    volume_describe_resp = client.describe_volumes(VolumeIds=[vol_id],
                  Filters=[{'Name': 'tag:'+ key, 'Values': [ value]},])
    if len(volume_describe_resp['Volumes']) > 0:
        snapshots_resp = client.describe_snapshots(
                    Filters=[{'Name': 'volume-id','Values': [vol_id]},])
        snapshots = snapshots_resp['Snapshots']
        snapshots.sort(key=lambda ss:ss['StartTime'],reverse=True)
        if retention_type == 'ByCount':
            for index, item in enumerate(snapshots):
                if index >= int(retention_value):
                    snapshot_del_response = client.delete_snapshot(SnapshotId=item['SnapshotId'])
        elif retention_type == 'ByDays':
            for item in snapshots:
                timeLimit = datetime.datetime.now(item['StartTime'].tzinfo) - datetime.timedelta(days=int(retention_value))
                if item['StartTime'] <= timeLimit :
                    snapshot_del_response = client.delete_snapshot(SnapshotId=item['SnapshotId'])
    return 'completed'
