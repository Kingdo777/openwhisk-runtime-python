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
from __future__ import print_function

import multiprocessing
from sys import stdin
from sys import stdout
from sys import stderr
from os import fdopen
import sys, os, json, traceback, warnings

try:
    # if the directory 'virtualenv' is extracted out of a zip file
    path_to_virtualenv = os.path.abspath('./virtualenv')
    if os.path.isdir(path_to_virtualenv):
        # activate the virtualenv using activate_this.py contained in the virtualenv
        activate_this_file = path_to_virtualenv + '/bin/activate_this.py'
        if not os.path.exists(activate_this_file):  # try windows path
            activate_this_file = path_to_virtualenv + '/Scripts/activate_this.py'
        if os.path.exists(activate_this_file):
            with open(activate_this_file) as f:
                code = compile(f.read(), activate_this_file, 'exec')
                exec(code, dict(__file__=activate_this_file))
        else:
            sys.stderr.write("Invalid virtualenv. Zip file does not include 'activate_this.py'.\n")
            sys.exit(1)
except Exception:
    traceback.print_exc(file=sys.stderr, limit=0)
    sys.exit(1)

# now import the action as process input/output
from main__ import main as main

out = fdopen(3, "wb")
if os.getenv("__OW_WAIT_FOR_ACK", "") != "":
    out.write(json.dumps({"ok": True}, ensure_ascii=False).encode('utf-8'))
    out.write(b'\n')
    out.flush()
env = os.environ

import ipc


class BucketKey:
    def __init__(self):
        self.key = 0
        self.bucket_name_2_key_map = dict()

    def gen(self, name):
        if name in self.bucket_name_2_key_map:
            return None
        else:
            self.key = (self.key + 1) % 0x10000
            self.bucket_name_2_key_map[name] = self.key + 0x10000
            return self.bucket_name_2_key_map[name]

    def get(self, name):
        if name in self.bucket_name_2_key_map:
            return self.bucket_name_2_key_map[name]
        else:
            return None

    def destroy(self, name):
        if name in self.bucket_name_2_key_map:
            del self.bucket_name_2_key_map[name]


def run_state_function():
    msg = ipc.create_msg(0x7777)
    bucket_key = BucketKey()
    lock = multiprocessing.Lock()
    if os.fork() != 0:
        # for handling the request from the state-function-manager
        while True:
            line = stdin.readline()
            if not line: break
            args = json.loads(line)
            payload = {}
            for key in args:
                if key == "value":
                    payload = args["value"]
                else:
                    env["__OW_%s" % key.upper()] = args[key]
            res = {}
            with lock:
                try:
                    res = main(payload)
                except Exception as ex:
                    print(traceback.format_exc(), file=stderr)
                    res = {"error": str(ex)}
                out.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
                out.write(b'\n')
                stdout.flush()
                stderr.flush()
                out.flush()
        msg.send("exit")
    else:
        # for handling the request from the pipe
        while True:
            print("Waiting for message!!!!!")
            data = msg.receive()
            print("Received message: %s" % data)
            if data == "exit": break
            payload = json.loads(data)
            action_pipe_key = payload["action_pipe_key"]
            action_msg = ipc.get_msg(action_pipe_key)
            if payload["op"] == "get":
                key = bucket_key.get(payload["name"])
                if key is None:
                    action_msg.send(json.dumps({
                        "statusCode": "400",
                        "body": "bucket not exist"
                    }))
                else:
                    action_msg.send(json.dumps({
                        "statusCode": "200",
                        "body": "OK",
                        "key": key
                    }))
                continue
            if payload["op"] == "create":
                payload["key"] = bucket_key.gen(payload["name"])
                if payload["key"] is None:
                    action_msg.send(json.dumps({
                        "statusCode": "400",
                        "body": "bucket `{}` already exist".format(payload["name"])
                    }))
                    continue
            else:
                payload["key"] = bucket_key.get(payload["name"])
                if payload["key"] is None:
                    action_msg.send(json.dumps({
                        "statusCode": "400",
                        "body": "bucket `{}` not exist".format(payload["name"])
                    }))
                    continue
            res = {}
            with lock:
                try:
                    res = main(payload)
                except Exception as ex:
                    print(traceback.format_exc(), file=stderr)
                    res = {"error": str(ex)}
                print("Sending message: %s" % json.dumps(res))
                if payload["op"] == "destroy" and res["statusCode"] == "200":
                    bucket_key.destroy(payload["name"])
                action_msg.send(json.dumps(res))


def run_application_function():
    action_pipe_key = 0x1000 + int(env["__OW_ACTION_PIPE_KEY"]) % 0x1000
    msg = ipc.create_msg(action_pipe_key)
    while True:
        line = stdin.readline()
        if not line: break
        args = json.loads(line)
        payload = {}
        for key in args:
            if key == "value":
                payload = args["value"]
            else:
                env["__OW_%s" % key.upper()] = args[key]
        payload["action_pipe_key"] = action_pipe_key
        res = {}
        try:
            res = main(payload)
        except Exception as ex:
            print(traceback.format_exc(), file=stderr)
            res = {"error": str(ex)}
        out.write(json.dumps(res, ensure_ascii=False).encode('utf-8'))
        out.write(b'\n')
        stdout.flush()
        stderr.flush()
        out.flush()
    msg.destroy()


function_type = env["__OW_FUNCTION_TYPE"]
if function_type == "state-function":
    run_state_function()
else:
    run_application_function()
