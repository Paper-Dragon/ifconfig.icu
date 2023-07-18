FROM python:3.10.12-alpine3.17
MAINTAINER <PaperDragon&&2678885646@qq.com>

WORKDIR /app
COPY . /app

RUN pip install -r requirments.txt

EXPOSE 8000
CMD ["sh", "-c", "python main.py"]