import re
import logging
from decouple import config
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler
from components import connections


app = App(
    process_before_response=config('AWS_LAMBDA', default=False, cast=bool),
    signing_secret=config('SLACK_SIGNING_SECRET'),
    token=config('SLACK_BOT_TOKEN'),
)


NOTION_LINK_REGEX = r'<https://www\.notion\.so/\S+\|?.*>'


def replace_https_to_notion(text):
    """
    Replace https to notion
    """
    pattern = re.compile(NOTION_LINK_REGEX)
    matches_with_newline = '\n'.join(pattern.findall(text))
    return matches_with_newline.replace('https', 'notion')


@app.message(re.compile(NOTION_LINK_REGEX))
def catch_notion_web_url(message, say):
    target_message_ts = message['ts']
    target_message_thread_ts = message.get('thread_ts', '')
    text = message['text']

    edited_text = replace_https_to_notion(text)

    # Post message
    options = {
        'text': edited_text,
        'thread_ts': target_message_thread_ts or target_message_ts,
    }
    fairy_message = say(**options)

    # Create connection between origin and fairy messages
    connections.create(target_message_ts, fairy_message['message']['ts'])


@app.event({'type': 'message', 'subtype': 'thread_broadcast'})
def notion_web_url_thread_broadcast(message, say):
    pattern = re.compile(NOTION_LINK_REGEX)
    matches = pattern.findall(message['text'])
    if matches:
        target_message_ts = message['ts']
        target_message_thread_ts = message.get('thread_ts', '')
        text = message['text']

        edited_text = replace_https_to_notion(text)

        # Post message
        options = {
            'text': edited_text,
            'thread_ts': target_message_thread_ts or target_message_ts,
        }
        fairy_message = say(**options)

        # Create connection between origin and fairy messages
        connections.create(target_message_ts, fairy_message['message']['ts'])


@app.event({'type': 'message', 'subtype': 'message_changed'})
def message_changed(client, message, say):
    channel = message['channel']
    target_message_ts = message['message']['ts']
    target_message_thread_ts = message['message'].get('thread_ts', '')
    text = message['message']['text']

    if message['message'].get('subtype') == 'tombstone':
        fairy_ts = connections.get_fairy_ts(target_message_ts)
        if fairy_ts:
            client.chat_delete(channel=channel, ts=fairy_ts)
            connections.delete(target_message_ts)
            return

    pattern = re.compile(NOTION_LINK_REGEX)
    matches = pattern.findall(text)
    if message['previous_message'] and matches != pattern.findall(message['previous_message']['text']):
        fairy_ts = connections.get_fairy_ts(target_message_ts)
        if fairy_ts:
            if matches:
                edited_text = '\n'.join(matches).replace('https', 'notion')
                client.chat_update(channel=channel, ts=fairy_ts, text=edited_text)
            else:
                client.chat_delete(channel=channel, ts=fairy_ts)
                connections.delete(target_message_ts)
        else:
            edited_text = replace_https_to_notion(text)

            # Post message
            options = {
                'text': edited_text,
                'thread_ts': target_message_thread_ts or target_message_ts,
            }
            fairy_message = say(**options)

            # Create connection between origin and fairy messages
            connections.create(target_message_ts, fairy_message['message']['ts'])


@app.event({'type': 'message', 'subtype': 'message_deleted'})
def message_deleted(client, message):
    fairy_ts = connections.get_fairy_ts(message['deleted_ts'])
    if fairy_ts:
        client.chat_delete(channel=message['channel'], ts=fairy_ts)
        connections.delete(message['deleted_ts'])


@app.event('message')
def do_nothing(message):
    # print(message)
    pass


if config('AWS_LAMBDA', default=False, cast=bool):
    SlackRequestHandler.clear_all_log_handlers()
    logging.basicConfig(format="%(asctime)s %(message)s", level=logging.DEBUG)


def lambda_handler(event, context):
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)


# Start Dev Server
if __name__ == '__main__':
    try:
        app.start(port=3000)
    except KeyboardInterrupt:
        pass
