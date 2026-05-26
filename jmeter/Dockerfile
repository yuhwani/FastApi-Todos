# Dockerfile for JMeter (x86_64 / multi-arch)
# 가이드 원본은 arm64v8 베이스였으나, 서버가 Intel x86_64라 멀티아키 베이스로 교체.
# openjdk:11-jre-slim 은 Docker Hub에서 deprecation 후 제거되어 Eclipse Temurin 사용.
FROM eclipse-temurin:11-jre

ENV JMETER_VERSION=5.4.1
ENV JMETER_HOME=/opt/apache-jmeter-${JMETER_VERSION}
ENV PATH=${JMETER_HOME}/bin:$PATH

RUN apt-get update && \
    apt-get install -y wget unzip && \
    rm -rf /var/lib/apt/lists/*

RUN wget https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-${JMETER_VERSION}.tgz && \
    tar -xzf apache-jmeter-${JMETER_VERSION}.tgz -C /opt/ && \
    rm apache-jmeter-${JMETER_VERSION}.tgz

WORKDIR ${JMETER_HOME}

CMD ["jmeter", "-n"]
