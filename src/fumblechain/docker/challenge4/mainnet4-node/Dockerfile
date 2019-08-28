FROM python:3.7-alpine
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev bash git
COPY src/fumblechain/requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /opt/fumblechain
COPY . .
RUN git checkout -f challenge4
RUN git clean -fdx
WORKDIR src/fumblechain
RUN pip install -r requirements.txt
COPY src/fumblechain/gen/wallets ./wallets
CMD ./daemon.py -vvv --port ${CH4_MAINNET_NODE_PORT} --magic ${CH4_MAINNET_MAGIC} start
