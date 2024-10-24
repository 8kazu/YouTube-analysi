from googleapiclient.discovery import build
import json
import pandas as pd
import streamlit as st
import os


# 環境変数からAPIキーを取得
DEVELOPER_KEY = os.getenv('YOUTUBE_API_KEY')
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, developerKey=DEVELOPER_KEY)

# 関数準備
def video_search(youtube, q='自動化', max_results=50):
    response = youtube.search().list(
        q=q,
        part="snippet",
        order='viewCount',
        type='video',
        maxResults=max_results
    ).execute()

    # st.write(response)  # ここでAPIのレスポンス内容を確認

    items_id = []
    items = response.get('items', [])
    for item in items:
        # 'videoId' が存在するかを確認
        if 'videoId' in item['id']:
            item_id = {
                'video_id': item['id']['videoId'],
                'channel_id': item['snippet']['channelId']
            }
            items_id.append(item_id)
        else:
            st.error(f"Error: 'videoId' not found in item: {item}")

    return pd.DataFrame(items_id)


def get_results(df_video, threshold=50000):
    if df_video.empty:
        st.error("動画が見つかりませんでした。")
        return pd.DataFrame()

    channel_ids = df_video['channel_id'].unique().tolist()
    subscriber_list = youtube.channels().list(
        id=','.join(channel_ids),
        part='statistics'
    ).execute()

    subscribers = [
        {'channel_id': item['id'], 'subscriber_count': int(item['statistics'].get('subscriberCount', 0))}
        for item in subscriber_list['items']
    ]

    df_subscribers = pd.DataFrame(subscribers)
    df = pd.merge(left=df_video, right=df_subscribers, on='channel_id')
    df_extracted = df[df['subscriber_count'] < threshold]

    if df_extracted.empty:
        st.error("登録者数が閾値を下回るチャンネルがありませんでした。")
        return pd.DataFrame()

    video_ids = df_extracted['video_id'].tolist()
    if not video_ids:
        st.error("有効な動画IDが見つかりませんでした。")
        return pd.DataFrame()

    videos_list = youtube.videos().list(
        id=','.join(video_ids),
        part='snippet,contentDetails,statistics'
    ).execute()

    videos_info = [
        {'video_id': item['id'], 'title': item['snippet']['title'], 'view_count': item['statistics']['viewCount']}
        for item in videos_list['items']
    ]
    
    df_videos_info = pd.DataFrame(videos_info)
    
    if df_videos_info.empty:
        st.error("動画情報が見つかりませんでした。")
        return pd.DataFrame()

    return pd.merge(left=df_extracted, right=df_videos_info, on='video_id')


# Streamlit UI
st.title('YouTube分析アプリ')

st.sidebar.write("## 検索トピックと登録者数の設定")
query = st.sidebar.text_input('検索したいトピックを入力', 'Excel')
threshold = st.sidebar.slider("登録者数", 100, 100000, 10000)

st.markdown(f"### 検索動画: 「{query}」")
st.markdown(f"### 登録者数: {threshold}以下")

# API実行
df_video = video_search(youtube, q=query, max_results=50)
results = get_results(df_video, threshold=threshold)

st.write("### 分析結果", results)

# 動画再生
video_id = st.text_input('動画IDを入力してください')
if st.button('ビデオ表示'):
    if video_id:
        video_url = f"https://youtu.be/{video_id}"
        st.video(video_url)
    else:
        st.error("動画IDを入力してください")
