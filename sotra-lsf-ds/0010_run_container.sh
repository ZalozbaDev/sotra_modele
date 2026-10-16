#!/bin/bash

pushd Docker

docker run -v ./models1:/app/models1 -p 3000:3000 -it sotra-lsf
