FROM python:3.12.3-alpine3.18
LABEL org.opencontainers.image.authors="<PaperDragon&&2678885646@qq.com>"

WORKDIR /app
COPY . /app
RUN chmod +x entrypoint.sh
RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["sh", "/app/entrypoint.sh"]