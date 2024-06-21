import csv
from datetime import datetime
from dateutil.relativedelta import relativedelta
import json
import os
from so4t_api import StackClient


def main():

    try:
        url = os.environ['SO_URL']
        token = os.environ['SO_TOKEN']
        proxy_url = os.getenv('SO_PROXY_URL')  # proxy is optional (as needed)
    except KeyError:
        print('Environment variables not found. Please enter the API configuration manually.')
        url = input('Enter the URL for your Stack Overflow instance: ')
        token = input('Enter your API token: ')
        proxy_url = input('Enter the proxy URL (leave blank if not needed): ')

    client = StackClient(url, token, proxy_url)

    questions = client.get_all_questions_and_answers()
    articles = client.get_articles()
    client.export_to_json("questions", questions)
    client.export_to_json("articles.json", articles)

    date_filters = create_date_filters()
    csv_data = []
    for filter_name, filter in date_filters.items():

        filtered_questions = filter_content_by_date(questions, filter)
        filtered_articles = filter_content_by_date(articles, filter)

        total_page_views = 0
        deleted_page_views = 0
        for question in filtered_questions:
            total_page_views += question['viewCount']
            if not question['owner']:
                deleted_page_views += question['viewCount']
                continue  # don't count page views of answers if question is already counted
            for answer in question['answers']:
                if not answer['owner'].get('accountId'):
                    deleted_page_views += question['viewCount']
                    break  # don't count page views of subsequent answers (i.e. avoid duplication)

        for article in filtered_articles:
            total_page_views += article['viewCount']
            if not article['owner']:
                deleted_page_views += article['viewCount']
        try:
            page_view_percentage = "{:.2f}".format((deleted_page_views / total_page_views) * 100)
        except ZeroDivisionError:
            page_view_percentage = 0
        filter_data = {
            "Time Frame": filter_name,
            "Page Views of Content Created During Time Frame": total_page_views,
            "Page Views of Content Created by Users Now Deleted": deleted_page_views,
            "Percent of Knowledge Reuse Attributed to Deleted Users": page_view_percentage
        }
        csv_data.append(filter_data)

    fieldnames = [k for k in filter_data.keys()]
    file_name = 'deleted_kr.csv'
    directory = 'reports'
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, file_name)
    with open(file_path, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_data)

    print(f'CSV report has been written to: `{file_path}`')


def create_date_filters():

    now = datetime.now()
    date_filters = {
        'Past Month': now - relativedelta(months=1),
        'Past Quarter': now - relativedelta(months=3),
        'Past Six Months': now - relativedelta(months=6),
        'Past Year': now - relativedelta(years=1),
        'Past Two Years': now - relativedelta(years=2),
        'All Time': now - relativedelta(years=100)
    }
    return date_filters


def convert_timestamp_format(timestamp):
    date = timestamp.split('T')[0]
    return datetime.strptime(date, "%Y-%m-%d")


def filter_content_by_date(content_pieces, date_filter):
    filtered_content = []
    for content in content_pieces:
        content_ts = convert_timestamp_format(content['creationDate'])
        if content_ts > date_filter:
            filtered_content.append(content)

    return filtered_content


def read_json(file_name):
    directory = 'data'
    file_path = os.path.join(directory, file_name)
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        raise FileNotFoundError

    return data


if __name__ == '__main__':

    main()
