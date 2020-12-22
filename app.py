import os
import re
import requests
from decouple import config
from slack_bolt import App


app = App(
    token=config('SLACK_BOT_TOKEN'),
    signing_secret=config('SLACK_SIGNING_SECRET')
)


@app.message(re.compile(r'(<https://www\.notion\.so/.+>)'))
def message_notion_url(client, message, body):
    channel_id = message['channel']
    target_message_ts = message['ts']
    target_message_thread_ts = message.get('thread_ts', '')
    options = {
        'channel': channel_id,
        'user': message['user'],
        'blocks': [
            {
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': 'Notion Web URL(*https://*)을 사용하셨네요! Notion App URL(*notion://*)도 필요하신가요?',
                },
            },
            {
                'type': 'actions',
                'block_id': 'notion_fairy_dialog',
                'elements': [
                    {
                        'type': 'button',
                        'text': {
                            'type': 'plain_text',
                            'text': '네!'
                        },
                        'style': 'primary',
                        'action_id': 'notion_fairy_true',
                        'value': f'{target_message_ts},{target_message_thread_ts}',
                    },
                    {
                        'type': 'button',
                        'text': {
                            'type': 'plain_text',
                            'text': '아니요..',
                        },
                        'style': 'danger',
                        'action_id': 'notion_fairy_false',
                    },
                ]
            },
        ],
    }
    if target_message_thread_ts:
        options['thread_ts'] = target_message_thread_ts

    res =  client.chat_postEphemeral(**options)


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
        pattern = re.compile(r'(<https://www\.notion\.so/.+>)')
        matches_with_newline = '\n'.join(pattern.findall(text))
        edited_text = matches_with_newline.replace('https', 'notion')

        # Post Message
        options = {
            'channel': container_channel_id,
            'text': edited_text,
        }
        if target_message_thread_ts:
            options['thread_ts'] = target_message_thread_ts
        slack_response = client.chat_postMessage(**options)


@app.event('message')
def do_nothing():
    pass


# Start your app
if __name__ == '__main__':
    app.start(port=int(os.environ.get('PORT', 3000)))
