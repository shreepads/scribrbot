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
   
   
    # Figure out if the event needs to be handled
    if 'message' not in event:
        print('No message element in event')
        return 'Nothing for me to do here'
        
    if 'text' not in event['message']:
        print('No text element in message')
        return 'Nothing for me to do here'
        
    if 'entities' not in event['message']:
        print('No entities element in message')
        return 'Nothing for me to do here'
    
    
    # Get set of hashtags from message and return if none
    hashtags = getHashtagsFromMessage(event['message'])
    
    if not hashtags:
        print('No hashtags in message text: %s' % event['message']['text'])
        return 'Nothing for me to do here'
    
    
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
        'Raw' : event,
        'Hashtags' : hashtags
    }
    
    print('Putting in_message to table: %s' % in_message)
    
    message_table.put_item(Item=in_message)
    
    return 'ScribrBot, out'


def getHashtagsFromMessage(message):
    """
    Returns a set of hashtags contained in the Telegram message.
    """
    
    hashtags = set()
    text = message['text']
    
    for entity in message['entities']:
        if entity['type'] == 'hashtag':
            offset = int(entity['offset'])
            length = int(entity['length'])
            hashtag = text[offset + 1 : offset + length]
            hashtags.add(hashtag)
            
    print('Returning hashtags: %s' % hashtags)
    
    return hashtags
        
