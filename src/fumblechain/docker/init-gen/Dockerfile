FROM python:3.7-alpine
RUN apk add --no-cache gcc musl-dev python3-dev libffi-dev openssl-dev bash git
COPY requirements.txt .
RUN pip install -r requirements.txt

WORKDIR /opt/fumblechain
RUN mkdir volume

COPY . .

CMD ["./gen.sh"]
