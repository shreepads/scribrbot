# scribrbot

## Introduction

ScribrBot acts as a Scribe for Telegram groups. Once it is added to a 
group, it can keep track of discussion topics by hashtag and present the
threads of discussion when requested.

ScribrBot runs on AWS, using Lambda, API Gateway, DynamoDB and S3. All of
these resources are setup using a standard CloudFormation template that
requires IAM access.


## Branches

### sprint0 branch
* CloudFormation template to setup all required resources
* Deployment script that sets up all the resources and registers ScribrBot
with Telegram
* Basic handler that stores the message data in a table

### sprint1 branch
* Validate Telegram token and derive botname using it instead of from
command line input
* Discard all messages other than those with hashtags
* Provide 'summarise' command to summarise messages by hashtag


## How to Deploy

* Install Python 2.7 (or above), virtualenv, pip and git
* Setup AWS credentials of an IAM user that has access to the necessary
AWS services as described [here]
(http://boto3.readthedocs.io/en/latest/guide/configuration.html#aws-config-file)
* Clone this repository: 
`$ git clone https://github.com/shreepads/scribrbot.git`
* In the repo directory create a Python 2.7 virtual environment:
`$ virtualenv --verbose --python=python2.7 venv`
* Activate the virtual environment:
`$ source venv/bin/activate`
* Install the necessary Python packages:
`(venv)$ pip install -r requirements.txt`
* Deploy the bot, providing a valid Telegram bot token:
`(venv)$ deploy_scribrbot.py --telegram_token <insert token here>`


## How to Use (under development)

* At the time ScribrBot is deployed, a Telegram user must be identified as the
 Bot Owner.
* The Bot Owner can add ScribrBot to Telegram Groups and in each Group specify
which Telegram users in the Group will act as Group Owners
* Group Owners can control certain features on the Group, other Group users
can post messages to the group as usual with Hashtags
* ScribrBot will track each message posted with Hashtags (multiple tags can be
associated with a message)
* ScribrBot will present the conversation around each Hashtag

