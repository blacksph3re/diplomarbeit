FROM ubuntu:groovy AS builder

RUN apt-get update && apt-get install -y subversion qt5-qmake qt5-default wget git build-essential clang vim libomp5
RUN mkdir -p /opt/qblade && mkdir -p /out
WORKDIR /opt/qblade

# ENV CC=/usr/bin/clang
# ENV CXX=/usr/bin/clang++
ENV ARCH=skylake

# # Replace MKL with working headers
# RUN wget -O key https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS-2019.PUB && apt-key add key && rm key && \
#   echo deb https://apt.repos.intel.com/mkl all main > /etc/apt/sources.list.d/intel-mkl.list && \
#   apt-get update && \
#   apt-get install -y intel-mkl-64bit-2020.1-102 libiomp5

# # Install libeigen
# # The ubuntu default version segfaults 3.3.2
# # https://github.com/PointCloudLibrary/pcl/issues/1684
# # 3.3.2, 3.3.4, 3.3.5 segfault, 3.3.6+7 don't compile
RUN apt-get install -y cmake && \
  cd /opt && \
  git clone --branch 3.4 https://gitlab.com/libeigen/eigen.git && \
  mkdir eigen/build && \
  cd eigen/build && \
  cmake -DCMAKE_CXX_FLAGS="-O3 -march=${ARCH}" .. && make && make install

# # Replace chrono with the newest version
# # CXX Flags are necessary to get it to compile the latest eigen version - interestingly it segfaults without -O2 ???
RUN cd /opt && \
  git clone --branch 6.0.0 https://github.com/projectchrono/chrono.git && \
  #rm chrono/cmake/FindAVX.cmake chrono/cmake/FindSSE.cmake chrono/cmake/FindFMA.cmake chrono/cmake/FindTBB.cmake && \
  mkdir chrono/build && \
  cd chrono/build && \
  cmake -DCMAKE_CXX_FLAGS="-std=c++11 -O3 -march=${ARCH}" .. && \
  make -j4 && \
  make install

# RUN cd /opt && \
#   mkdir chrono_bin && \
#   wget https://anaconda.org/conda-forge/chrono/5.0.1/download/linux-64/chrono-5.0.1-he1b5a44_0.tar.bz2 -O chrono.tar.bz2 && \
#   tar -xvf chrono.tar.bz2 -C chrono_bin

# ENV CC=/usr/bin/gcc
# ENV CXX=/usr/bin/g++


RUN cd /opt && \ 
  git clone --branch v3.0.0 https://github.com/OpenFAST/openfast.git && \
  mkdir -p openfast/build && cd openfast/build && \
  apt-get install -y gfortran libopenblas-dev && \
  FFLAGS="-march=${ARCH} -O3" cmake -DOPENMP=ON .. && make -j4 turbsim

# # # QT
# git clone https://code.qt.io/qt/qt5.git
# cd qt5
# git checkout v5.15.0
# perl init-repository
# cd ..
# mkdir qt5_build
# cd qt5_build
# ../qt5/configure -opensource -nomake examples -nomake tests -confirm-license
# make -j8

RUN svn checkout http://svn.code.sf.net/p/qblade/code/trunk/ . && svn up -r2299

COPY qblade_v09.pro /opt/qblade/qblade_v09.pro
COPY LicenseCheck.cpp /opt/qblade/src/LicenseCheck.cpp
#cp /opt/chrono_bin/lib/libChronoEngine.so /opt/qblade/libraries/libs_unix_64bit && \
# RUN cp /opt/intel/lib/intel64/libiomp5.so /opt/qblade/libraries/libs_unix_64bit/ && \
  # cp /usr/lib/x86_64-linux-gnu/libomp.so* /opt/qblade/libraries/libs_unix_64bit/ && \
  # cp -r /opt/intel/mkl/include/* /opt/qblade/include_headers/MKL && \
  # cp /opt/chrono_bin/lib/libChronoEngine.so /opt/qblade/libraries/libs_unix_64bit && \
  # cp /usr/local/lib/libChronoEngine_mkl.so /opt/qblade/libraries/libs_unix_64bit && \

RUN qmake && \
   sed -i 's/-O2 -Wall -Wextra/-O3 -w -march=${ARCH}/g' /opt/qblade/Makefile && \
   cp /usr/local/lib/libChronoEngine.so /opt/qblade/libraries/libs_unix_64bit

RUN make clean && make copyTarget && make -j4

# RUN git clone https://gitlab.windenergy.dtu.dk/OpenLAC/BasicDTUController.git && \
#   cd BasicDTUController/src && \
#   apt-get install -y gfortran
#COPY libBasicTUBController.so /opt/qblade/libraries/libs_unix_64bit/


RUN mkdir -p /out/libraries && cp -rv /opt/qblade/libraries/libs_unix_64bit /out/libraries/ && cp -v /opt/qblade/libQBlade* /out && cp -rv /opt/qblade/Binaries /out && cp -rv /opt/qblade/ControllerFiles /out && cp -v /opt/openfast/build/modules/turbsim/turbsim /out/Binaries/TurbSim64
# RUN rm -v /out/libraries/libs_unix_64bit/libblas* && rm -v /out/libraries/libs_unix_64bit/liblapack*

# Stage 1
FROM ubuntu:groovy AS deploy

# at some point try to get qblade/eigen running with libopenblas-dev liblapacke-dev
RUN apt-get update && \
    apt-get install -y libomp5 python3-pip xvfb qt5-default libopenblas-dev && \ 
    pip --no-cache install zmq protobuf numpy psutil gym toml && \
    mkdir -p /opt/qblade_build && \
    mkdir /opt/res && \
    mkdir /opt/scripts && \
    strip --remove-section=.note.ABI-tag /lib/x86_64-linux-gnu/libQt5Core.so.5

WORKDIR /opt/scripts

COPY --from=builder /out /opt/qblade_build/
RUN echo "/opt/qblade_build/libraries/libs_unix_64bit" > /etc/ld.so.conf.d/qblade.conf && \
    ldconfig
COPY *.py *.toml /opt/scripts/
COPY tempdir/messages/python /opt/scripts/messages/python
COPY tempdir/res /opt/res

ENTRYPOINT xvfb-run -a python3 /opt/scripts/server.py /opt/scripts/config_docker.toml