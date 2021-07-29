import re
from decouple import config
import requests
import logging
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
import boto3

from components import blocks, notion

app = App(
    process_before_response=config('AWS_LAMBDA', default=False, cast=bool),
    signing_secret=config('SLACK_SIGNING_SECRET'),
    token=config('SLACK_BOT_TOKEN'),
)


@app.message(re.compile(r'(<https://www\.notion\.so/\S+>)'))
def catch_notion_web_url(client, message):
    channel = message['channel']
    target_message_ts = message['ts']
    target_message_thread_ts = message.get('thread_ts', '')
    user = message['user']

    options = blocks.create_fairy_dialog(channel, target_message_ts, target_message_thread_ts, user)
    res = client.chat_postEphemeral(**options)


@app.event({'type': 'message', 'subtype': 'message_changed'})
def catch_edited_notion_web_url(client, message):
    pattern = re.compile(r'(<https://www\.notion\.so/\S+>)')
    matches = pattern.findall(message['message']['text'])
    if message['previous_message'] and matches != pattern.findall(message['previous_message']['text']):
        channel = message['channel']
        target_message_ts = message['message']['ts']
        target_message_thread_ts = message['message'].get('thread_ts', '')
        user = message['message']['user']

        fairy_ts = fetch_fairy_ts(target_message_ts)
        if fairy_ts:
            if matches:
                edited_text = '\n'.join(matches).replace('https', 'notion')
                client.chat_update(channel=channel, ts=fairy_ts, text=edited_text)
            else:
                client.chat_delete(channel=channel, ts=fairy_ts)
                delete_connection(target_message_ts)
        else:
            options = blocks.create_fairy_dialog(channel, target_message_ts, target_message_thread_ts, user)
            res = client.chat_postEphemeral(**options)


@app.event({'type': 'message', 'subtype': 'message_deleted'})
def catch_deleted_notion_web_url(client, message):
    fairy_ts = fetch_fairy_ts(message['deleted_ts'])
    if fairy_ts:
        client.chat_delete(channel=message['channel'], ts=fairy_ts)
        delete_connection(message['deleted_ts'])


def fetch_fairy_ts(origin_ts: str) -> str:
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.get_item(TableName=config('AWS_DYNAMODB_TABLE_NAME'),
                                 Key={'OriginTs':{'S':origin_ts}})
    return response['Item']['FairyTs']['S'] if 'Item' in response else ''


def create_connection(origin_ts: str, fairy_ts: str) -> None:
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.put_item(TableName=config('AWS_DYNAMODB_TABLE_NAME'),
                                 Item={'OriginTs':{'S':origin_ts},'FairyTs':{'S':fairy_ts}})


def delete_connection(origin_ts: str) -> None:
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.delete_item(TableName=config('AWS_DYNAMODB_TABLE_NAME'),
                                    Key={'OriginTs':{'S':origin_ts}})


@app.action(re.compile('notion_fairy_(true|false)'))
def notion_fairy_button(client, ack, say, body, payload):
    # Acknowledge the action
    ack()

    # Delete Container Message (Ephemeral)
    response_url = body['response_url']
    requests.post(response_url, json={
        'delete_original': 'true',
    })    

    if payload['action_id'] == 'notion_fairy_true':
        container_channel_id = body['container']['channel_id']
        target_message_ts, target_message_thread_ts = payload['value'].split(',')

        # Fetch Message with ts (and thread ts)
        if target_message_thread_ts:
            slack_response = client.conversations_replies(
                channel=container_channel_id,
                ts=target_message_ts,
                latest=target_message_thread_ts,
                limit=1,
                inclusive=True,
            )
        else:
            slack_response = client.conversations_history(
                channel=container_channel_id,
                latest=target_message_ts,
                limit=1,
                inclusive=True,
            )
        text = slack_response['messages'][0]['text']

        # Replace https to notion
        pattern = re.compile(r'(<https://www\.notion\.so/\S+>)')
        matches_with_newline = '\n'.join(pattern.findall(text))
        edited_text = matches_with_newline.replace('https', 'notion')

        # Post message
        options = {
            'channel': container_channel_id,
            'text': edited_text,
        }
        if target_message_thread_ts:
            options['thread_ts'] = target_message_thread_ts
        else:
            options['thread_ts'] = target_message_ts
        slack_response = client.chat_postMessage(**options)

        # Create connection between origin and fairy messages
        create_connection(target_message_ts, slack_response['message']['ts'])


# Create Meeting Schedule on Notion Database
@app.message(re.compile(r'\[.*회의.*\]'))
def add_meeting_to_notion(client, context, message):
    channel = message['channel']
    user = message['user']
    target_message_ts = message['ts']
    target_message_thread_ts = message.get('thread_ts', '')
    message_text = message['text']

    # Parse datetime
    pattern = re.compile(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
    match = pattern.search(message_text)
    meeting_date = match.group() if match else ''

    if meeting_date:
        # Parse title
        pattern = re.compile(r'\[.*회의.*\]')
        meeting_title = pattern.search(message_text).group()[1:-1]

        # Get channel name
        channel_name = client.conversations_info(channel=channel).get('channel', {}).get('name', '')

        data = {
            'database_name': channel_name,
            'meeting_title': meeting_title,
            'meeting_date': meeting_date,
            'target_message_ts': target_message_ts,
            'target_message_thread_ts': target_message_thread_ts,
        }

        options = blocks.meeting_schedule_block(channel, user, data=data)
        res = client.chat_postEphemeral(**options)


@app.action(re.compile('meeting_schedule_block_(create|close)'))
def notion_meeting_button(client, ack, say, body, payload):
    ack()

    # Delete Container Message (Ephemeral)
    response_url = body['response_url']
    requests.post(response_url, json={
        'delete_original': 'true',
    })

    if payload['action_id'] == 'meeting_schedule_block_create':
        database_name, meeting_title, meeting_date, target_message_ts, target_message_thread_ts = payload['value'].split(';')
        created_page_url = notion.api.create_page(database_name, meeting_title, meeting_date)
        edited_page_url = created_page_url.replace('https', 'notion')

        text = f"*[{meeting_title}]*\n*{meeting_date}*\n\n{created_page_url}\n{edited_page_url}"

        # Post message
        options = {
            'text': text,
            'thread_ts': target_message_thread_ts or target_message_ts,
        }
        slack_response = say(**options)


@app.event('message')
def do_nothing():
    pass


if config('AWS_LAMBDA', default=False, cast=bool):
    SlackRequestHandler.clear_all_log_handlers()
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)


# Start Dev Server
if __name__ == '__main__':
    app.start(port=3000)
