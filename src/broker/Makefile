BUILD_DIR=../../build
DEPS_DIR=../../deps

all:
	g++ -I $(DEPS_DIR)/zmqpp/src/ -L $(DEPS_DIR)/zmqpp/build/max-g++ -I $(BUILD_DIR)/messages/cpp $(BUILD_DIR)/messages/cpp/*.cc main.cpp -o $(BUILD_DIR)/broker -lzmq -lzmqpp -lprotobuf -lpthread -std=c++17 

build-deps:
	git clone https://github.com/zeromq/zmqpp.git $(DEPS_DIR)/zmqpp
	cd $(DEPS_DIR)/zmqpp && make

docker:
	cd .. && docker build -t broker -f broker/Dockerfile .

singularity:
	singularity build $(BUILD_DIR)/sif/broker.sif docker-daemon://broker:latest