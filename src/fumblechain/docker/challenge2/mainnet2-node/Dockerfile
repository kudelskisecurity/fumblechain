FROM python:3.7-alpine
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev bash git
COPY src/fumblechain/requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /opt/fumblechain
COPY . .
RUN git checkout -f challenge2
RUN git clean -fdx
WORKDIR src/fumblechain
RUN pip install -r requirements.txt
COPY src/fumblechain/gen/wallets ./wallets
CMD ./ch2_wrapper.sh
