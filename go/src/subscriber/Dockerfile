FROM ubuntu

# Install the C lib for kafka
RUN apt-get update
RUN apt-get install -y --no-install-recommends apt-utils wget gnupg software-properties-common
RUN apt-get install -y apt-transport-https ca-certificates
RUN wget -qO - https://packages.confluent.io/deb/5.2/archive.key | apt-key add -
RUN add-apt-repository "deb [arch=amd64] https://packages.confluent.io/deb/5.2 stable main"
RUN apt-get update
RUN apt-get install -y librdkafka-dev

# Install Go
RUN add-apt-repository ppa:longsleep/golang-backports
RUN apt-get update
RUN apt-get install -y golang-go
RUN apt-get install -y git

# build the library
WORKDIR /go/src
ADD . .
RUN GOPATH=/go/src
RUN go get gopkg.in/confluentinc/confluent-kafka-go.v1/kafka
RUN  GOOS=linux go build  -o main .
ENTRYPOINT ["./main"]
