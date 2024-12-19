from flask import Flask, request
from flask_cors import CORS, cross_origin

from inference_new2 import FairseqCTranslateRunner

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

runner = FairseqCTranslateRunner()

@app.route('/translate', methods=['POST'])
def translate():
    if request.json is None:
        return {'error': 'No JSON given'}, 400
    
    fields = ['q', 'source', 'target']
    for field in fields:
        if field not in request.json:
            return {'error': f'Missing field {field}'}, 400

    if 'format' in request.json and request.json['format'] != 'text':
            return {'error': f'Requested source format not supported'}, 500

    text = request.json.get('q')
    src_lng = request.json.get('source')
    trg_lng = request.json.get('target')

    if src_lng == 'auto':
        return {'error': f'Automatic language detection is not supported'}, 500

    model_env = 'prod'

    translation, marked_in, marked_out, c2_in, c2_out, model, error = \
        runner.translate(text, src_lng, trg_lng, model_env)

    if error:
        return {
            'error': error
        }, 500
    else:
        return {
            'translatedText': translation,
            'alternatives': [],
        }, 200

    app.run('0.0.0.0', 3000)
