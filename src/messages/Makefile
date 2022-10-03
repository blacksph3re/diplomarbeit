BUILD_DIR = ../../build/messages
all:
	mkdir -p $(BUILD_DIR)/cpp
	mkdir -p $(BUILD_DIR)/python
	protoc --cpp_out=$(BUILD_DIR)/cpp *.proto
	protoc --python_out=$(BUILD_DIR)/python *.proto
	touch $(BUILD_DIR)/python/__init__.py
