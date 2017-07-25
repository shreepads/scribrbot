#!venv/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Shreepad Shukla

"""
deploy_scribrbot
~~~~~~~~~~~~~~~~~~
This module deploys ScribrBot on AWS and registers the corresponding webhook.
It uses a CloudFormation template (stored in resources/) and AWS credentials
of an IAM user with the appropriate permissions.
The CloudFormation template creates the API Gateway, Lambda Function and 
DynamoDB table for ScribrBot.
"""

import argparse
import subprocess
import platform

import boto3
import requests

def package_deploy(lambda_s3bucket, bot_name):
    """
    Package the ScribrBot lambda function and deploy to the given S3 bucket
    using the bot_name as the key. 
    """
    
    zip_tld_files = 'scribrbot.py'    # files from the top level directory
    zip_package_list = 'requests urllib3 certifi chardet idna jinja2 \
        markupsafe'    # folders from site-packages
    
    # Construct platform specific zip commands
    zip_command = None

    if (platform.system().lower() == 'linux'):
        zip_command = '/bin/zip -9 {}.zip {} && ' \
            'cd venv/lib/python2.7/site-packages/ && ' \
            '/bin/zip -9r ../../../../{}.zip {}'.format(
                bot_name, zip_tld_files, bot_name, zip_package_list
            )
        
        
    #TODO Windows specific zip command
    if (platform.system().lower() == 'windows'):
        pass
    
    if (not zip_command):
        raise Exception
        
    
    # Execute ZIP command to create package file
    zip_output = None

    try:
        zip_output = subprocess.Popen(zip_command, 
            stdout=subprocess.PIPE, shell=True).stdout.read().decode('utf-8')
    except subprocess.SubprocessError as e:
        print('SubprocessError: %s' % e)
        raise e

    print('zip_output: %s' % zip_output)
    
    # Upload created ZIP package to S3
    print('Uploading ZIP package to S3')
    
    s3 = boto3.resource('s3')
    s3bucket = s3.Bucket(lambda_s3bucket)
    
    zip_filename = '{}.zip'.format(bot_name)
    s3_key = 'code/{}'.format(zip_filename)
	
    s3bucket.put_object(Key=s3_key, Body=open(zip_filename, 'rb'))
    
    print('Uploaded ZIP package to S3 with key: %s' % s3_key)
        
    return s3_key
    

def createstack(stackname, bot_name, telegram_token, lambda_s3bucket,
         s3bucket_key, templatedata):
    """
    Creates a ScribrBot stack for the given bot_name using the
    CloudFormation templatedata. 
    Returns URL of the REST ApiGateway endpoint
    """
    
    print('Creating stack: %s' % stackname)
        
    # Get the low level client
    cfclient = boto3.client('cloudformation')
    
    cfresponse = cfclient.create_stack(
        StackName=stackname,
        TemplateBody=templatedata,
        Parameters=[
            {
                'ParameterKey': 'TelegramBotName',
                'ParameterValue': bot_name
            },
            {
                'ParameterKey': 'TelegramBotToken',
                'ParameterValue': telegram_token
            },
            {
                'ParameterKey': 'LambdaFunctionS3Bucket',
                'ParameterValue': lambda_s3bucket
            },
            {
                'ParameterKey': 'LambdaFunctionS3Key',
                'ParameterValue': s3bucket_key
            }
        ],
        Capabilities=['CAPABILITY_IAM'],
        Tags=[
            {
                'Key': 'BotName',
                'Value': bot_name
            },
        ]
    )
    
    print('cfresponse: %r' % cfresponse)
    
    # Wait for stack formation
    print('Waiting for stack creation...')
    cfcreatewaiter = cfclient.get_waiter('stack_create_complete')
    cfcreatewaiter.wait(StackName=stackname)
    print('Stack creation complete!')
    
    # Pick up the Response Values
    descstack = cfclient.describe_stacks(StackName=stackname)
    
    print('Stack creation outputs: %r' % (descstack['Stacks'][0]['Outputs']) )
    
    # Return ApiGateway URL
    apig_url = descstack['Stacks'][0]['Outputs'][0]['OutputValue']
    
    print('API Gateway URL: %r' % apig_url)
    
    return apig_url


def registerWebhook(telegram_token, url):
    """
    Register the Telegram webhook for the given token using the url given
    """
    
    register_webhook_url = \
        "https://api.telegram.org/bot{0}/setWebhook?url={1}".format(
            telegram_token,
            url
        )
    
    response = requests.get(register_webhook_url)
    
    if response.status_code == 200:
        print("Webhook registered succesfully!")
    else:
        print("Webhook registration failed")
        print("Response: %r" % response)
    


def main():
    """
    Parses command line arguments and environment variables and triggers the
    core agent function.
    """
    
    # Get environment variables - TODO
    
    # Parse command line variables
    parser = argparse.ArgumentParser()
    parser.add_argument('--bot_name',
        help='Name of the bot to be deployed (default TestScribrBotv2). Must be ' \
        'unique, 6 to 10 chars long and only contain numbers and uppercase/ ' \
        'lowercase letters',
        default='TestScribrBotv2')
    parser.add_argument('--telegram_token',
        help='Telegram API token for the bot. The webhook will be registered '\
        'and response messages sent using this. The API token for at least ' \
        'one messaging platform is required')
        
    parser.add_argument('--templatefile',
        help='Filename of the CloudFormation template file. Default is ' \
        './resources/CloudForm-ScribrBot.yaml',
        default='./resources/CloudForm-ScribrBot.yaml')
    parser.add_argument('--lambda_s3bucket',
        help='Name of the S3 bucket where the bot lamdba function must be ' \
        'uploaded after packaging (default testscribrbot)',
        default='testscribrbot')
    parser.add_argument('--s3bucket_key',
        help='S3 bucket key where the bot lamdba function has already been ' \
        'uploaded. If provided, will use this and not package and deploy')
    
    
    args = parser.parse_args()
    
    # Check for telegram token
    if (not args.telegram_token):
        print("Telegram bot token is required to proceed. See deploy_scribrbot.py --help for details")
        return
    
    # Load the template data
    f = open(args.templatefile)
    templatedata = f.read()
    f.close()
    
    s3bucket_key = None
    
    # Package the bot lamdba function and deploy to S3 if s3bucket_key not provided
    if (args.s3bucket_key):
        s3bucket_key = args.s3bucket_key
    else:
        s3bucket_key = package_deploy(args.lambda_s3bucket, args.bot_name)
    
    stackname = 'ScribrBotStack-' + args.bot_name
    
    # Create the stack
    apig_url = createstack(stackname, args.bot_name, args.telegram_token, args.lambda_s3bucket,
         s3bucket_key, templatedata)
    
    # Register the webhook
    registerWebhook(args.telegram_token, apig_url)
    
    return


if __name__ == '__main__':
    main()

