FROM alpine AS builder

WORKDIR /opt
RUN apk add --no-cache protobuf zeromq-dev git g++ make protobuf-dev libzmq-static libsodium-static
RUN git clone https://github.com/zeromq/zmqpp.git
RUN cd zmqpp && make && make install

COPY broker/main.cpp /opt/broker/main.cpp
COPY messages/* /opt/broker/

WORKDIR /opt/broker
RUN protoc --cpp_out=. *.proto && g++ -O2 -flto *.cc main.cpp -o broker -static -lprotobuf -lzmqpp -lpthread -lzmq -lsodium -std=c++17 

CMD /opt/broker/broker

FROM alpine

COPY --from=builder /opt/broker/broker /opt/broker

ENTRYPOINT /opt/broker