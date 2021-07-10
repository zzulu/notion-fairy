from datetime import datetime
from decouple import config
import requests


class NotionAPI:
    NOTION_VERSION = config('NOTION_VERSION')
    NOTION_KEY = config('NOTION_KEY')
    BASE_URL = 'https://api.notion.com/v1'

    def __init__(self):
        self.headers = {
            'Authorization': f'Bearer {self.NOTION_KEY}',
            'Content-Type': 'application/json',
            'Notion-Version': f'{self.NOTION_VERSION}',
        }

    def __search(self, query: str) -> dict:
        url = f'{self.BASE_URL}/search'
        data = {
            'query': query,
        }
        return requests.post(url, json=data, headers=self.headers).json()

    def __get_database_id_by_name(self, database_name: str) -> str:
        response = self.__search(database_name)
        return response.get('results', [])[0].get('id', '')

    def create_page(self, database_name: str, title: str, date: str) -> str:
        database_id = self.__get_database_id_by_name(database_name)
        date, time = date.split() # '2021-07-10 14:00'
        iso_date = f'{date}T{time}:00+09'

        data = {
            'parent': {
                'database_id': f'{database_id}',
            },
            'properties': {
                'Name': {
                    'title': [
                        {
                            'text': {
                                'content': title,
                            },
                        },
                    ],
                },
                'Date Time': {
                    'date': {
                        'start': iso_date,
                    },
                },
            },
        }

        url = f'{self.BASE_URL}/pages'
        response = requests.post(url, json=data, headers=self.headers).json()
        return response.get('url', '')


api = NotionAPI()
