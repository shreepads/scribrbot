# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Shreepad Shukla

"""
scribrbot
~~~~~~~~
ScribrBot main module. Handles the webhook events from Telegram.
"""


from __future__ import print_function
import os, json

import boto3

# Setup outside main event handler

token = os.environ['TelegramBotToken']
print('Token: %s' % token) 
    
msg_table_name =  os.environ['MessageTableName']
print('Msg table name: %s' % msg_table_name) 

dynamodb_res = boto3.resource('dynamodb')    
message_table = dynamodb_res.Table(msg_table_name)

def lambda_handler(event, context):
    """
    Main webhook handler. Figures out what to do, farms out and responds
    """
    # Log event, context details
    print('Event type:%s' % type(event))
    print('Event:%s' % repr(event))
    
    print('Context type:%s' % type(context))
    print('Context:%s' % repr(context))
   
    
    # Parse mesage content
    first_name = event['message']['from']['first_name']
    text = event['message']['text'].lstrip('/')
    chat_id = event['message']['chat']['id']
    unix_timestamp = event['message']['date']
    
    print('Received message %s from %s on chat_id %s' % (text, first_name, chat_id))
    
    # Store message in DB
    in_message = {
        'ChatId' : chat_id,
        'UnixTimestamp' : unix_timestamp,
        'Direction' : 'In',
        'Text' : text,
        'UserFirstName' : first_name,
        'Raw' : event
    }
    
    print('Putting in_message to table: %s' % in_message)
    
    message_table.put_item(Item=in_message)
    
    return 'Hello from Lambda'


