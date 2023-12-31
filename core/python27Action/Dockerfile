#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

# build go proxy from source
FROM golang:1.18 AS builder_source
ARG GO_PROXY_GITHUB_USER=apache
ARG GO_PROXY_GITHUB_BRANCH=master
RUN git clone --branch ${GO_PROXY_GITHUB_BRANCH} \
   https://github.com/${GO_PROXY_GITHUB_USER}/openwhisk-runtime-go /src ;\
   cd /src ; env GO111MODULE=on CGO_ENABLED=0 go build main/proxy.go && \
   mv proxy /bin/proxy

# or build it from a release
FROM golang:1.18 AS builder_release
ARG GO_PROXY_RELEASE_VERSION=1.18@1.20.0
RUN export https_proxy=http://222.20.68.152:7890  \
    && curl -sL https://github.com/apache/openwhisk-runtime-go/archive/{$GO_PROXY_RELEASE_VERSION}.tar.gz | tar xzf -\
    && cd openwhisk-runtime-go-*/main\
    && GO111MODULE=on CGO_ENABLED=0 go build -o /bin/proxy \
    && unset https_proxy

FROM ubuntu:22.04

# select the builder to use
ARG GO_PROXY_BUILD_FROM=release

# install zip && python2.7
RUN apt-get update && apt-get install -y python2.7 python2.7-dev python-pip zip libjpeg8-dev zlib1g-dev libcurl4-openssl-dev\
    && rm -rf /var/lib/apt/lists/*

# Install common modules for python
COPY requirements_common.txt requirements_common.txt
COPY requirements.txt requirements.txt
RUN pip2 install --upgrade pip six wheel &&\
    pip2 install --no-cache-dir -r requirements.txt

COPY ./statefunction-2.0.0-cp27-cp27mu-linux_x86_64.whl /statefunction-2.0.0-cp27-cp27mu-linux_x86_64.whl
RUN pip2 install /statefunction-2.0.0-cp27-cp27mu-linux_x86_64.whl

RUN mkdir -p /action
WORKDIR /

COPY --from=builder_source /bin/proxy /bin/proxy_source
COPY --from=builder_release /bin/proxy /bin/proxy_release
RUN mv /bin/proxy_${GO_PROXY_BUILD_FROM} /bin/proxy

ADD bin/compile /bin/compile
ADD lib/launcher.py /lib/launcher.py

# log initialization errors
ENV OW_LOG_INIT_ERROR=1
# the launcher must wait for an ack
ENV OW_WAIT_FOR_ACK=1
# execution environment
ENV OW_EXECUTION_ENV=openwhisk/action-python-v2.7
# compiler script
ENV OW_COMPILER=/bin/compile

ENTRYPOINT ["/bin/proxy"]
