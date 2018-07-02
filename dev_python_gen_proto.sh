#!/usr/bin/env bash
SRC_DIR=protobuf/
DST_DIR=src/
echo $SRC_DIR

protoc $SRC_DIR/innovapos/shared/protocols/messaging.proto $SRC_DIR/innovapos/shared/protocols/common.proto --proto_path=$SRC_DIR --python_out=$DST_DIR