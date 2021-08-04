

def create_fairy_dialog(channel: str, target_message_ts: str, target_message_thread_ts: str, user: str) -> dict:
    options = {
        "channel": channel,
        "user": user,
        "text": "Web URL(https://)을 사용하셨네요! App URL(notion://)도 필요하신가요?",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "Web URL(*https://*)을 사용하셨네요! App URL(*notion://*)도 필요하신가요?",
                },
            },
            {
                "type": "actions",
                "block_id": "notion_fairy_dialog",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "네"
                        },
                        "style": "primary",
                        "action_id": "notion_fairy_true",
                        "value": f"{target_message_ts};{target_message_thread_ts}",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "아니요",
                        },
                        "style": "danger",
                        "action_id": "notion_fairy_false",
                    },
                ]
            },
        ],
    }
    if target_message_thread_ts:
        options['thread_ts'] = target_message_thread_ts
    return options


def meeting_schedule_block(channel: str, user: str, data: dict = {}) -> dict:
    options = {
        "channel": channel,
        "user": user,
        "text": f"Notion 데이터베이스 '#{data.get('database_name')}'에 회의를 등록합니다.",
        "blocks": [
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Notion 데이터베이스 `#{data.get('database_name')}`에 회의를 등록합니다.",
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                        "text": f"[{data.get('meeting_title','')}]\n{data.get('meeting_date', '')}",
                },
            },
            {
                "type": "actions",
                "block_id": "create_meeting_schedule_block",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "등록"
                        },
                        "style": "primary",
                        "action_id": "meeting_schedule_block_create",
                        "value": f"#{data.get('database_name')};{data.get('meeting_title','')};{data.get('meeting_date', '')};{data.get('target_message_ts', '')};{data.get('target_message_thread_ts', '')}",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "취소",
                        },
                        "style": "danger",
                        "action_id": "meeting_schedule_block_close",
                    },
                ]
            },
        ],
    }
    if data.get('target_message_thread_ts'):
        options['thread_ts'] = data.get('target_message_thread_ts')
    return options
