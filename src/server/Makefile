BUILD_DIR = ../../build
RES_DIR = ../../res

docker:
	mkdir tempdir || (rm -rf tempdir && mkdir tempdir)
	cp -r $(RES_DIR) tempdir
	cp -r $(BUILD_DIR)/messages tempdir
	docker build -t qblade_server -f Dockerfile .
	rm -rf tempdir

singularity:
	singularity build $(BUILD_DIR)/sif/server.sif docker-daemon://qblade_server:latest

transfer-hlrn:
	scp $(BUILD_DIR)/sif/server.sif hlrn:/scratch/usr/bemwindl/images/server.sif