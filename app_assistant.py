import streamlit as st
import requests
import json
import boto3
from botocore.exceptions import ClientError
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# Константы
API_ENDPOINT = "url"
S3_BUCKET = "AWS bucket name"
S3_PREFIX = "prefix S3 bucket"

# Инициализация сессии boto3
s3 = boto3.client('s3')

# Функция для отправки запроса к чат-боту
def send_chat_request(user_id, query):
    """
    Отправляет запрос к API чат-бота и возвращает ответ.
    
    :param user_id: ID пользователя
    :param query: Текст запроса пользователя
    :return: Ответ от API в формате JSON или None в случае ошибки
    """
    payload = {
        "user_id": user_id,
        "query": query
    }
    response = requests.post(API_ENDPOINT, json=payload)
    return response.json() if response.status_code == 200 else None

# Функция для получения списка пользователей из S3
def get_users_from_s3():
    """
    Получает список уникальных пользователей из бакета S3.
    
    :return: Список уникальных ID пользователей
    """
    users = set()
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=S3_PREFIX, Delimiter='/')
        for prefix in response.get('CommonPrefixes', []):
            user = prefix.get('Prefix').split('/')[-2]
            if user != 'errors':
                users.add(user)
    except ClientError as e:
        st.error(f"Ошибка при получении списка пользователей: {e}")
    return list(users)

# Функция для получения данных пользователя из S3
def get_user_data_from_s3(user_id):
    """
    Получает все данные конкретного пользователя из бакета S3.
    
    :param user_id: ID пользователя
    :return: Список словарей с данными пользователя
    """
    data = []
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"{S3_PREFIX}{user_id}/")
        for obj in response.get('Contents', []):
            file_content = s3.get_object(Bucket=S3_BUCKET, Key=obj['Key'])['Body'].read().decode('utf-8')
            data.append(json.loads(file_content))
    except ClientError as e:
        st.error(f"Ошибка при получении данных пользователя: {e}")
    return data

# Функция для получения данных об ошибках из S3
def get_error_data_from_s3():
    """
    Получает все данные об ошибках из специальной папки в бакете S3.
    
    :return: Список словарей с данными об ошибках
    """
    data = []
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET, Prefix=f"{S3_PREFIX}errors/")
        for obj in response.get('Contents', []):
            file_content = s3.get_object(Bucket=S3_BUCKET, Key=obj['Key'])['Body'].read().decode('utf-8')
            data.append(json.loads(file_content))
    except ClientError as e:
        st.error(f"Ошибка при получении данных об ошибках: {e}")
    return data

# Функция для получения данных всех пользователей
def get_all_users_data():
    """
    Получает данные всех пользователей и объединяет их в один DataFrame.
    
    :return: pandas DataFrame с данными всех пользователей
    """
    all_data = []
    users = get_users_from_s3()
    for user in users:
        user_data = get_user_data_from_s3(user)
        for item in user_data:
            item['user_id'] = user  # Добавляем user_id к каждой записи
        all_data.extend(user_data)
    return pd.DataFrame(all_data)

# Настройка страницы Streamlit
st.set_page_config(page_title="HCB Assistant", page_icon="🏦", layout="wide")

# Пользовательский CSS для улучшения внешнего вида
st.markdown("""
<style>
    .main {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stTextInput, .stTextArea {
        background-color: white;
        border-radius: 5px;
        padding: 10px;
        border: 1px solid #ddd;
    }
    .stButton>button {
        background-color: #0066cc;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
    }
    .response-box {
        background-color: white;
        border-radius: 5px;
        padding: 15px;
        border: 1px solid #ddd;
        margin-top: 20px;
    }
    h1 {
        color: #0066cc;
    }
</style>
""", unsafe_allow_html=True)

# Сайдбар для выбора режима работы приложения
mode = st.sidebar.radio("Выберите режим", ["Чат", "Админ панель"])

if mode == "Чат":
    st.title("Assistant")

    # Создаем два столбца для ввода данных
    col1, col2 = st.columns([1, 2])

    with col1:
        user_id = st.text_input("Введите ваш ID пользователя:")
    
    with col2:
        query = st.text_area("Введите ваш вопрос:")

    # Обработка запроса пользователя
    if st.button("Получить ответ"):
        if user_id and query:
            with st.spinner('Обработка запроса...'):
                result = send_chat_request(user_id, query)
                if result:
                    st.markdown("<div class='response-box'>", unsafe_allow_html=True)
                    st.markdown(f"**Ответ:**\n\n{result['response']}")
                    st.markdown(f"**Время обработки:** {result['processing_time']:.2f} секунд")
                    st.markdown("</div>", unsafe_allow_html=True)
                else:
                    st.error("Произошла ошибка при обработке запроса.")
        else:
            st.warning("Пожалуйста, введите ID пользователя и вопрос.")

elif mode == "Админ панель":
    st.title("Админ панель Assistant")

    # Выбор типа анализа в админ панели
    analysis_type = st.selectbox("Выберите тип анализа", ["Общая аналитика", "Данные пользователя", "Ошибки"])

    if analysis_type == "Общая аналитика":
        st.subheader("Общая аналитика по всем пользователям")
        
        # Загрузка и обработка данных всех пользователей
        with st.spinner("Загрузка данных..."):
            df_all = get_all_users_data()
            df_all['timestamp'] = pd.to_datetime(df_all['timestamp'], unit='s')

        # Отображение основной статистики
        st.subheader("Основная статистика")
        col1, col2, col3 = st.columns(3)
        col1.metric("Всего пользователей", df_all['user_id'].nunique())
        col2.metric("Всего запросов", len(df_all))
        col3.metric("Среднее время обработки", f"{df_all['processing_time'].mean():.2f} сек")

        # График активности пользователей по дням
        st.subheader("Активность пользователей по дням")
        daily_activity = df_all.groupby(df_all['timestamp'].dt.date).size().reset_index(name='count')
        fig_daily = px.line(daily_activity, x='timestamp', y='count', title='Количество запросов по дням')
        st.plotly_chart(fig_daily)

        # Топ пользователей по количеству запросов
        st.subheader("Топ пользователей по количеству запросов")
        top_users = df_all['user_id'].value_counts().head(10)
        fig_top_users = px.bar(top_users, x=top_users.index, y=top_users.values, title='Топ-10 пользователей')
        st.plotly_chart(fig_top_users)

        # Распределение времени обработки запросов
        st.subheader("Распределение времени обработки запросов")
        fig_proc_time = px.histogram(df_all, x='processing_time', nbins=50, title='Распределение времени обработки')
        st.plotly_chart(fig_proc_time)

        # Анализ популярных слов в запросах
        st.subheader("Популярные слова в запросах")
        all_words = ' '.join(df_all['query']).lower().split()
        word_freq = Counter(all_words)
        common_words = pd.DataFrame(word_freq.most_common(20), columns=['Слово', 'Частота'])
        fig_words = px.bar(common_words, x='Слово', y='Частота', title='Топ-20 слов в запросах')
        st.plotly_chart(fig_words)

    elif analysis_type == "Данные пользователя":
        # Получение и отображение данных конкретного пользователя
        users = get_users_from_s3()
        selected_user = st.selectbox("Выберите пользователя", users)

        if selected_user:
            user_data = get_user_data_from_s3(selected_user)
            if user_data:
                df = pd.DataFrame(user_data)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                
                st.subheader(f"Данные пользователя {selected_user}")
                st.dataframe(df.style.highlight_max(axis=0))

                col1, col2 = st.columns(2)
                with col1:
                    st.subheader("Статистика")
                    st.info(f"Всего запросов: {len(df)}")
                    st.info(f"Среднее время обработки: {df['processing_time'].mean():.2f} секунд")
                
                with col2:
                    st.subheader("График времени обработки")
                    st.line_chart(df.set_index('timestamp')['processing_time'])

    else:  # Просмотр ошибок
        # Получение и отображение данных об ошибках
        error_data = get_error_data_from_s3()
        if error_data:
            df_errors = pd.DataFrame(error_data)
            df_errors['timestamp'] = pd.to_datetime(df_errors['timestamp'], unit='s')
            
            st.subheader("Данные об ошибках")
            st.dataframe(df_errors.style.highlight_max(axis=0))

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Статистика ошибок")
                st.info(f"Всего ошибок: {len(df_errors)}")
            
            with col2:
                error_counts = df_errors['error'].value_counts()
                st.subheader("Наиболее частые ошибки")
                st.bar_chart(error_counts.head())

# Футер
st.sidebar.markdown("---")
st.sidebar.info("© 2024 Assistant")
