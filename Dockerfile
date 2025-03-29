FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=run.py
ENV FLASK_ENV=production
ENV SECRET_KEY=your-production-secret-key

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"] 