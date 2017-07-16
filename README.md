# scribrbot

## Introduction

ScribrBot acts as a Scribe for Telegram groups. Once it is added to a group, it
can keep track of discussion topics by hashtag and present the threads of
discussion when requested.

ScribrBot runs on AWS, using Lambda, API Gateway, DynamoDB and S3. All of
these resources are setup using a standard CloudFormation template.

## Branches

### sprint0 branch
* CloudFormation template to setup all required resources
* Deployment script that sets up all the resources and registers ScribrBot
with Telegram
* Basic handler that stores the message data in a table

## How to Use

* At the time ScribrBot is deployed, a Telegram user must be identified as the
 Bot Owner.
* The Bot Owner can add ScribrBot to Telegram Groups and in each Group specify
which Telegram users in the Group will act as Group Owners
* Group Owners can control certain features on the Group, other Group users
can post messages to the group as usual with Hashtags
* ScribrBot will track each message posted with Hashtags (multiple tags can be
associated with a message)
* ScribrBot will present the conversation around each Hashtag

