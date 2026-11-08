FROM ubuntu:22.04 AS build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake curl ca-certificates python3 libboost-date-time-dev libboost-system-dev libboost-filesystem-dev libboost-thread-dev libgmp-dev zlib1g-dev libbz2-dev default-libmysqlclient-dev
WORKDIR /src
RUN curl --fail --location --retry 3 https://codeload.github.com/uakfdotb/ghostpp/tar.gz/cf397544d08d05f8536272e3ab1b22cf03309d9f -o /src/upstream.tar.gz && echo 'a3e74eb55b9c38de460f5d69ee4cf1f4f8fd3ed815306d4bc822fc1b434f33da  /src/upstream.tar.gz' | sha256sum -c - && tar -xzf upstream.tar.gz --strip-components=1
COPY check_manual_autohost.py patch_manual_autohost.py /checks/
RUN python3 /checks/check_manual_autohost.py /src/ghost/ghost.cpp; test "$?" -eq 42
RUN python3 /checks/patch_manual_autohost.py /src && python3 /checks/check_manual_autohost.py /src/ghost/ghost.cpp
RUN cmake -S bncsutil -B build-bncs -DCMAKE_BUILD_TYPE=Release && cmake --build build-bncs --target bncsutil -j1 && cmake --install build-bncs
RUN cmake -S StormLib -B build-storm -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON && cmake --build build-storm -j1 && cmake --install build-storm
RUN cmake -S CascLib -B build-casc -DCMAKE_BUILD_TYPE=Release && cmake --build build-casc -j1 && cmake --install build-casc
RUN ldconfig && make -C ghost -j1 DFLAGS= OFLAGS='-O2 -std=c++11' && mkdir -p /bundle/lib && cp ghost/ghost++ /bundle/ && cp /usr/local/lib/libbncsutil.so* /usr/local/lib/libstorm.so* /usr/local/lib/libcasc.so* /bundle/lib/ && cp default.cfg language.cfg license.txt /bundle/
COPY patch_readonly_map.py /checks/
RUN python3 /checks/patch_readonly_map.py /src && make -C ghost -j1 DFLAGS= OFLAGS='-O2 -std=c++11' && cp ghost/ghost++ /bundle/

FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates python3 libboost-date-time1.74.0 libboost-system1.74.0 libboost-filesystem1.74.0 libboost-thread1.74.0 libgmp10 libmariadb3 libbz2-1.0 zlib1g && rm -rf /var/lib/apt/lists/*
COPY --from=build /bundle/ /opt/ghost/
ENV LD_LIBRARY_PATH=/opt/ghost/lib
USER 10002:10002
WORKDIR /state
ENTRYPOINT ["/opt/ghost/ghost++", "/state/ghost.cfg"]

FROM build AS hostmap-build
COPY patch_worker.py ready.hpp test_ready.cpp /hostmap/
RUN g++ -std=c++11 /hostmap/test_ready.cpp -o /hostmap/test-ready && /hostmap/test-ready
RUN python3 /hostmap/patch_worker.py /src && make -C /src/ghost clean && make -C /src/ghost -j1 DFLAGS= OFLAGS='-O2 -std=c++11'
FROM warcraft-iii-hostbot:local AS hostmap
COPY --from=hostmap-build /src/ghost/ghost++ /opt/ghost/ghost++
COPY *.py /app/
WORKDIR /app
