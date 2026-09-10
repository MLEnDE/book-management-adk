FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/book_management_adk

ENV PYTHONPATH=/app
ENV ADK_APP_DATA_DIR=/var/data/book_management

EXPOSE 8080

CMD ["python3", "book_management_adk/main.py"]
