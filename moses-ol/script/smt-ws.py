import flask
from flask import request, jsonify, send_file
#from flask_cors import CORS
import os
import subprocess
import json

import uuid
import threading
import time
import subprocess


import logging
import sys
from logging.handlers import RotatingFileHandler

logger = None


def init_logging(logdir):
    global logger
    # create logger
    logger = logging.getLogger("log_smt")

    # set logging level
    logger.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stream_handler = logging.StreamHandler(stream=sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)
    # create rotating file handler and set level to debug

    rot_handler = RotatingFileHandler(
        logdir + "/smt.log", maxBytes=20000000, backupCount=10,
    )
    rot_handler.setLevel(logging.DEBUG)
    rot_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(rot_handler)

    logger.debug("logging initialized")



app = flask.Flask(__name__)


# CORS
def init_app():
    #CORS(app)
    logger.debug("app initialized")




def delete_temp_files(files):
    print ("Files:", files)
    print ("length is ",len(files))
    for file in files:
        print("File: "+file)
        exec(f"rm {file}")
    

def exec(cmd):
    logger.debug(f">>> exec {cmd}")
    subprocess.run(cmd, shell=True, check=True)
    logger.debug(f"<<< exec")


def writeStringToFile(str, filename):
    print("writing to ", filename)
    with open(filename, "w",  encoding='utf-8') as text_file:
        print(str, file=text_file)    

def readFileIntoString(filename):
    print("reading from ", filename)
    with open(filename, 'r', encoding='utf-8') as file:
        data = file.read()
    return data


@app.route("/info", methods=["GET"])
def info():
    logger.debug(str(request))
    tmp_outfile = f"./tmp/{uuid.uuid4().hex}.txt"

    exec (f"./script/info_moses.sh {tmp_outfile}")
    data = readFileIntoString(tmp_outfile)
    string_array = data.split("\n")
    string_array1 = list(filter(lambda x: len(x) > 0, string_array))
    res = {"webservice_version": "0.0.1", "moses_info": string_array1}
    files=[]
    files.append(tmp_outfile)
    delete_temp_files(files)

    return res


def err_msg(msg):
    logger.debug("errmsg " + str(msg))
    return {"errormsg": msg}


@app.route("/translate", methods=["POST"])
def translate():
    logger.debug(str(request))
    logger.debug("request json payload: " + str(request.json))

    try:
        if request.json != None:
            print("\nrequest", request.json, "\n")

        if request.json is None or 'text' not in request.json:
            return err_msg('"text" field in JSON payload is required')

        text = request.json.get('text')
        src_lng = request.json.get('source_language', '')
        trg_lng = request.json.get('target_language', '')
        if src_lng == '' or trg_lng == '':
             return err_msg('"source_language" or "targetlanguage" field in JSON payload is required')

        if not ((src_lng == 'de' and trg_lng == 'hsb') or (src_lng == 'hsb' and trg_lng == 'de')):
             return err_msg('only \'de\' and \'hsb\' as translation language supported!')


        temp_file_in = f"./tmp/temp_file_in_{uuid.uuid4().hex}.txt"
        temp_file_src_sentence_output = f"./tmp/temp_file_src_sentence_output_{uuid.uuid4().hex}.txt"
        temp_file_src_moses = f"./tmp/temp_file_src_moses_{uuid.uuid4().hex}.txt"
        temp_file_dst_translation_raw = f"./tmp/temp_file_dst_translation_raw_{uuid.uuid4().hex}.txt"
        temp_file_dst_sentence_result = f"./tmp/temp_file_dst_sentence_result_{uuid.uuid4().hex}.txt"
       

        writeStringToFile(text, temp_file_in)


        # sm_translate.sh de hsb ./tmp/in.txt ./tmp/src_sentence_output.txt ./tmp/src_moses.txt ./tmp/dst_translation_raw.txt ./tmp/dst_sentence_result.txt
        exec (f"./script/sm_translate.sh {src_lng} {trg_lng} {temp_file_in} {temp_file_src_sentence_output} {temp_file_src_moses} {temp_file_dst_translation_raw} {temp_file_dst_sentence_result}")

        src_sentence_output = readFileIntoString(temp_file_src_sentence_output)
        src_moses = readFileIntoString(temp_file_src_moses)
        dst_translation_raw = readFileIntoString(temp_file_dst_translation_raw)
        dst_sentence_result = readFileIntoString(temp_file_dst_sentence_result)


        files=[]
        files.append(temp_file_in)
        files.append(temp_file_src_sentence_output)
        files.append(temp_file_src_moses)
        files.append(temp_file_dst_translation_raw)
        files.append(temp_file_dst_sentence_result)
        delete_temp_files(files)

        return {"src_sentence_output": src_sentence_output, "src_moses": src_moses,  "dst_translation_raw": dst_translation_raw, "dst_sentence_result": dst_sentence_result}

    except Exception as ex:
        trace = []
        tb = ex.__traceback__
        while tb is not None:
            trace.append(
                {
                    "filename": tb.tb_frame.f_code.co_filename,
                    "name": tb.tb_frame.f_code.co_name,
                    "lineno": tb.tb_lineno,
                }
            )
            tb = tb.tb_next
        ret = {
            "errormsg": "Exception",
            "exception": {
                "type": type(ex).__name__,
                "message": str(ex),
                "trace": trace,
            },
        }
        logger.debug("Exception: " + str(ret))
        return ret


if __name__ == "__main__":
    logdir = "."
    if len(sys.argv) == 2:
        logdir = sys.argv[1]
    elif len(sys.argv) > 2:
        print("invalid arguments: " + str(sys.argv))
        exit(1)

    print("logdir is " + logdir)

    init_logging(logdir)
    init_app()
    logger.debug("starting webserver ...")
    app.run(port=int(os.environ.get("PORT", 8080)), host="0.0.0.0", debug=False)
    logger.debug("exiting ...")
