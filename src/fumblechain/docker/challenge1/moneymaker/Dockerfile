FROM python:3.7-alpine
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev bash git
COPY src/fumblechain/requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /opt/fumblechain
COPY . .
RUN git checkout -f challenge1
RUN git clean -fdx
WORKDIR src/fumblechain
RUN pip install -r requirements.txt
COPY src/fumblechain/gen/wallets ./wallets

RUN pip install gunicorn

CMD /usr/local/bin/gunicorn -w 4 -b 0.0.0.0:${CH1_MONEYMAKER_PORT} moneymaker:app
