FROM python:3.7-alpine as targz
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev bash git

# prepare client download
WORKDIR /tmp/fumblechain
COPY . .
RUN git checkout -f master
RUN git clean -fdx
WORKDIR src
# add wrapper for CTF_WALLET_ADDRESSES environment variable and daemon.py
COPY src/fumblechain/daemon.sh fumblechain/
COPY src/fumblechain/fc-docker.sh fumblechain/
COPY src/fumblechain/gen/ctf_wallet_addresses.bash fumblechain/
COPY src/fumblechain/Dockerfile fumblechain/

# create .tar.gz client for challenge 1
RUN tar czvf fumblechain.tar.gz fumblechain
RUN cp fumblechain.tar.gz /tmp/fumblechain/fumblechain.tar.gz

FROM python:3.7-alpine as targz-ch4
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev bash git

# prepare client download
WORKDIR /tmp/fumblechain
COPY . .
RUN git checkout -f challenge4
RUN git clean -fdx
WORKDIR src
# add wrapper for CTF_WALLET_ADDRESSES environment variable and daemon.py
COPY src/fumblechain/daemon.sh fumblechain/
COPY src/fumblechain/fc-docker.sh fumblechain/
COPY src/fumblechain/gen/ctf_wallet_addresses.bash fumblechain/
COPY src/fumblechain/Dockerfile fumblechain/

# create .tar.gz client for challenge 4
RUN tar czvf fumblechain.tar.gz fumblechain
RUN cp fumblechain.tar.gz /tmp/fumblechain/fumblechain-ch4.tar.gz

FROM python:3.7-alpine as fumblestore
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev bash git
COPY src/fumblechain/requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /opt/fumblechain
COPY . .
WORKDIR src/fumblechain
RUN mkdir volume
RUN mkdir -p static/downloads
COPY --from=targz /tmp/fumblechain/fumblechain.tar.gz static/downloads/
COPY --from=targz-ch4 /tmp/fumblechain/fumblechain-ch4.tar.gz static/downloads/

RUN pip install gunicorn

CMD /usr/local/bin/gunicorn -w 4 -b 0.0.0.0:${FUMBLESTORE_PORT} fumblestore:app

# for development
#CMD ["./fumblestore.py"]
