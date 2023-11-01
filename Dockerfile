FROM python:3.9
ENV APP_DIR /app
WORKDIR $APP_DIR
# Requirements change less often than code - install before copying code for better caching
COPY requirements.txt $APP_DIR/
RUN ["pip", "install", "--upgrade", "--root-user-action",  "ignore", "pip"]
RUN ["pip", "install", "--root-user-action",  "ignore", "-r", "requirements.txt"]
COPY . $APP_DIR
ENTRYPOINT ["python", "bot.py"]