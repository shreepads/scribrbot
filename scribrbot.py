# -*- coding: utf-8 -*-
#
# Copyright (c) 2017 Shreepad Shukla

"""
scribrbot
~~~~~~~~
ScribrBot main module. Handles the webhook events from Telegram.
"""


from __future__ import print_function
import os, json, urllib
from datetime import datetime

import boto3, requests

from boto3.dynamodb.conditions import Key, Attr
from jinja2 import Template


# Setup outside main event handler

# Get environ variables
telegram_token = os.environ['TelegramBotToken']
print('Token: %s' % telegram_token) 
msg_table_name =  os.environ['MessageTableName']
print('Msg table name: %s' % msg_table_name) 
s3_bucket_name = os.environ['S3BucketName']
print('S3 bucket name: %s' % s3_bucket_name) 

# Get Dyname DB table and S3 Bucket resources
dynamodb_res = boto3.resource('dynamodb')    
message_table = dynamodb_res.Table(msg_table_name)
s3 = boto3.resource('s3')
s3bucket = s3.Bucket(s3_bucket_name)


# Setup Jinja2 template
summary_j2template_s3key = 'resources/jinja2templates/summary.html'
summary_j2template_objresp = s3bucket.Object(summary_j2template_s3key).get()
summary_j2templatestr = summary_j2template_objresp['Body'].read()
print("Got summary jinja2 template: %s" % summary_j2templatestr)

summary_j2template = Template(summary_j2templatestr)



def lambda_handler(event, context):
    """
    Main webhook handler. Figure out what to do, farm out and return
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
        
    if 'text' not in event['message']  and  'new_chat_members' not in event['message']:
        print('No text or new chat members element in message')
        return 'Nothing for me to do here'
        
    if 'entities' not in event['message']  and  'new_chat_members' not in event['message']:
        print('No entities or new chat members element in message')
        return 'Nothing for me to do here'
    
    
    # Figure out if a command has been issued, execute the first one and return
    if 'entities' in event['message']:
        for entity in event['message']['entities']:
            if entity['type'] == 'bot_command':
                executecommand(event['message'], entity)
                return 'Jawohl mein fuhrer!'
    
    # Figure out if new members have joined the group and if so greet them
    if 'new_chat_members' in event['message']:
        greetNewMembers(event['message'])
        return 'Welcome!'
    
    # Check if message text too long and ignore if so
    if len(event['message']['text']) > 500:
        print('Message text too long, not storing')
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
    Return a set of hashtags contained in the Telegram message.
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


def executecommand(message, bot_command_entity):
    """
    Execute the bot command contained in the Telegram message.
    """
    
    responsemsg = ''
    chat_id = message['chat']['id']
    text = message['text']
    offset = int(bot_command_entity['offset'])
    length = int(bot_command_entity['length'])
    
    bot_command = text[offset + 1 : offset + length]  
    
    print('Handling command %s for message text %s' % (bot_command, text))
    
    if bot_command == 'summ':
        hashtags = getHashtagsFromMessage(message)

        if not hashtags:
            print('No hashtags in summ message text: %s' % text)
            responsemsg = 'Sorry I need a #hashtag to summarise'
        else:
            summ_s3_url = generatesummary(chat_id, hashtags)
            if summ_s3_url:
                responsemsg = 'Summary URL: {}'.format(summ_s3_url)
            else:
                responsemsg = 'Sorry there are no messages with that hashtag.\n' \
                'This may be because messages with the hashtag were posted '     \
                'before I joined the group, were posted long ago or the '        \
                'group\'s id has changed since, for example because it was '     \
                'converted from a group to a supergroup.'
    
    if not responsemsg:
        responsemsg = 'Sorry I cannot handle that command'
        
    sendresponse(chat_id, responsemsg)
    return



def generatesummary(chat_id, hashtags):
    """
    Generate a summary for hashtags on the chat_id, store on S3 and return
    S3 url
    """
    
    # There will be at least one hashtag when called from executecommand()
    hashtag = hashtags.pop()
    
    # Scan the table for all messages that contain the given hashtag
    scanresponse = message_table.scan(
        FilterExpression=Attr('Hashtags').contains(hashtag) & Attr('ChatId').eq(chat_id)
    )
    
    if not scanresponse['Count']:
        return ''
    
    
    # Generate the HTML summary of the messages
    htmlsummary = summary_j2template.render(
        items=scanresponse['Items'], 
        datetime=datetime, int=int
    )
    
    # Store the summary on S3
    s3_key = 'summaries/{0}/{1}.html'.format(chat_id, hashtag)
    s3_object = s3bucket.put_object(
        Key=s3_key, 
        Body=htmlsummary.encode('utf8'),
        ACL='public-read',
        ContentType='text/html'
    )
    
    s3_url = 'https://{0}.s3.amazonaws.com/{1}'.format(s3_bucket_name, s3_key)
    
    return s3_url


def greetNewMembers(message):
    """
    Greet new members to the group.
    """
    
    newchatmembers = message['new_chat_members']
    
    if not newchatmembers:
        print('No chat members to greet!')
        return
    
    newmemberfirstnames = (newchatmember['first_name'] for newchatmember in newchatmembers)
    
    newmemberfirstnamesstr = ', '.join(newmemberfirstnames)
    
    greetingmsg = 'Hi {0}! I\'m the scribe for this group. I record all posted ' \
    'messages with #hashtags and can generate a summary of the conversation by ' \
    '#hashtag when requested.'.format(newmemberfirstnamesstr)
    
    chat_id = message['chat']['id']
    
    sendresponse(chat_id, greetingmsg)
    return


def sendresponse(chat_id, responsemsg):
    """
    Send the responsemsg on the chat_id.
    """
    
    sendresponse_url = \
        "https://api.telegram.org/bot{0}/sendMessage?chat_id={1}&text={2}".format(
            telegram_token,
            chat_id,
            urllib.quote(responsemsg.encode('utf8'))
        )
        
    response = requests.get(sendresponse_url)
    
    if response.status_code == 200:
        print("Message %s sent on chat_id %s" % (responsemsg, chat_id) )
    else:
        print("Message %s NOT sent on chat_id %s" % (responsemsg, chat_id) )
        print("Response: %r" % response)
        
    return
    
    
