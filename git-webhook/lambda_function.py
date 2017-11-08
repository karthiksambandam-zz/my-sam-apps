#  Copyright 2016 Amazon Web Services, Inc. or its affiliates. All Rights Reserved.
#  This file is licensed to you under the AWS Customer Agreement (the "License").
#  You may not use this file except in compliance with the License.
#  A copy of the License is located at http://aws.amazon.com/agreement/ .
#  This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied.
#  See the License for the specific language governing permissions and limitations under the License.

import boto3
from botocore.vendored import requests
import string
import json
import os
import zipfile
import logging
import os


#Set to False to allow self-signed/invalid ssl certificates
verify=False

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.handlers[0].setFormatter(logging.Formatter('[%(asctime)s][%(levelname)s] %(message)s'))
logging.getLogger('boto3').setLevel(logging.ERROR)
logging.getLogger('botocore').setLevel(logging.ERROR)

s3_client = boto3.client('s3')
def lambda_handler(event, context):
    OAUTH_token=os.environ['gittoken']
    OutputBucket=os.environ['outputbucket']
    temp_archive = '/tmp/archive.zip'
    tmp_folder = '/tmp/'
    headers = event['headers']
    body_json= json.loads(event['body'])

     # Identify git host flavour
    hostflavour='generic'
    if 'X-Hub-Signature' in headers.keys():
        hostflavour='githubent'
    elif 'X-Gitlab-Event' in headers.keys():
        hostflavour='gitlab'
    elif 'User-Agent' in headers.keys():
        if headers['User-Agent'].startswith('Bitbucket-Webhooks'):
            hostflavour='bitbucket'
    headers={}
    if hostflavour == 'githubent':
        archive_url = body_json["repository"]["archive_url"]
        owner = body_json["repository"]["owner"]["name"]
        name = body_json["repository"]["name"]
        # replace the code archive download and branch reference placeholders
        archive_url= archive_url.replace('{archive_format}','zipball').replace('{/ref}','/master')
        # add access token information to archive url
        archive_url= archive_url+'?access_token='+OAUTH_token
    elif hostflavour == 'gitlab':
        archive_url = body_json["project"]["http_url"].replace('.git','/repository/archive.zip?ref=master')+'&private_token='+OAUTH_token
        owner = body_json["project"]["namespace"]
        name = body_json["project"]["name"]
    elif hostflavour == 'bitbucket':
        archive_url = body_json["repository"]["links"]["html"]["href"]+'/get/master.zip'
        owner = body_json["repository"]["owner"]['username']
        name = body_json["repository"]["name"]
        r = requests.post('https://bitbucket.org/site/oauth2/access_token',data = {'grant_type':'client_credentials'},auth=(os.environ['oauthkey'], os.environ['oauthsecret']))
        if 'error' in r.json().keys():
            logger.error('Could not get OAuth token. %s: %s' % (r.json()['error'],r.json()['error_description']))
            raise Exception('Failed to get OAuth token')
        headers['Authorization'] = 'Bearer ' + r.json()['access_token']
    s3_archive_file = "%s/%s/%s_%s.zip" % (owner,name,owner,name)
    # download the code archive via archive url
    logger.info('Downloading archive from %s' % archive_url)
    r = requests.get(archive_url,verify=verify,headers=headers)
    with open(temp_archive, "wb") as codearchive:
        codearchive.write(r.content)
    # Adding logic to rezip the archive by skipping the root folder
    with zipfile.ZipFile(temp_archive, "r") as z:
        z.extractall(tmp_folder)
    fileList = os.listdir(tmp_folder)
    for f in fileList:
        if owner+'-'+name in f:
            zf = zipfile.ZipFile(tmp_folder+name, "w")
            for dirname, subdirs, files in os.walk(tmp_folder+f):
                for filename in files:
                    abs_filename=os.path.join(dirname, filename)
                    zf.write(abs_filename,abs_filename[len(tmp_folder+f+os.sep):])
            zf.close()
    # upload the archive to s3 bucket
    logger.info("Uploading zip to S3://%s/%s" % (OutputBucket,s3_archive_file))
    #s3_client.upload_file(temp_archive,OutputBucket, s3_archive_file)
    s3_client.upload_file(tmp_folder+name,OutputBucket, s3_archive_file)
    logger.info('Upload Complete')
