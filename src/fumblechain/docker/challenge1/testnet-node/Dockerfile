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
# run testnet chain (with a different magic)
CMD ./daemon.py -vvv --port ${CH1_TESTNET_NODE_PORT} --magic ${CH1_TESTNET_MAGIC} start
