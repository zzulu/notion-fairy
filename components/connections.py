import boto3
from decouple import config


def get_fairy_ts(origin_ts: str) -> str:
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.get_item(TableName=config('AWS_DYNAMODB_TABLE_NAME'),
                                 Key={'OriginTs':{'S':origin_ts}})
    return response['Item']['FairyTs']['S'] if 'Item' in response else ''


def create(origin_ts: str, fairy_ts: str) -> None:
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.put_item(TableName=config('AWS_DYNAMODB_TABLE_NAME'),
                                 Item={'OriginTs':{'S':origin_ts},'FairyTs':{'S':fairy_ts}})


def delete(origin_ts: str) -> None:
    dynamodb = boto3.client('dynamodb')
    response = dynamodb.delete_item(TableName=config('AWS_DYNAMODB_TABLE_NAME'),
                                    Key={'OriginTs':{'S':origin_ts}})
