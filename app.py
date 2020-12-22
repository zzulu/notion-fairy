import os
import re
import requests
from decouple import config
from slack_bolt import App


app = App(
    token=config('SLACK_BOT_TOKEN'),
    signing_secret=config('SLACK_SIGNING_SECRET')
)


@app.message(re.compile('(<https://www.notion.so/.+>)'))
def message_notion_url(client, message, context):
    channel_id = message["channel"]
    # target_message_ts = message.get('ts')
    context_matches = context
    print(context_matches)
    res = client.chat_postEphemeral(
        channel=channel_id,
        user=message['user'],
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Notion Web URL(`https://`)을 입력하셨군요! Notion App URL(`notion://`)로 변경할까요?"
                }
            },
            {
                "type": "actions",
                "block_id": "notion_fairy_dialog",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "emoji": True,
                            "text": "네"
                        },
                        "style": "primary",
                        "action_id": "notion_fairy_true",
                        "value": f"{target_message_ts}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "emoji": True,
                            "text": "아니요"
                        },
                        "style": "danger",
                        "action_id": "notion_fairy_false",
                    }
                ]
            }
        ]
    )

@app.event('message')
def do_nothing():
    pass


@app.action(re.compile('notion_fairy_(true|false)'))
def notion_fairy_button(client, body, ack, say, payload):
    # Acknowledge the action
    ack()

    # Delete Container Message (Ephemeral)
    response_url = body['response_url']
    requests.post(response_url, json={
        'delete_original': 'true',
    })    

    # say(str(body))
    # say(str(payload))

    container_channel_id = body['container']['channel_id']

    if payload['action_id'] == 'notion_fairy_true':
        target_message_ts = payload['value']

        slack_response = client.conversations_history(
            channel=container_channel_id,
            latest=target_message_ts,
            limit=1,
            inclusive=True,
        )

        # print(str(slack_response))
        text = slack_response['messages'][0]['text']
        edited_text = text.replace('https://www.notion.so', 'notion://www.notion.so')
        say(edited_text)
        # client.chat_update(
        #     token=config('SLACK_USER_TOKEN'),
        #     channel=container_channel_id,
        #     ts=target_message_ts,
        #     text=edited_text,
        # )



# Start your app
if __name__ == '__main__':
    app.start(port=int(os.environ.get('PORT', 3000)))
