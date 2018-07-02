from flask import Flask,jsonify,abort,make_response,request

app = Flask(__name__)



tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol',
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web',
        'done': False
    }
]

@app.route('/api/GetStock',methods=['GET'])

def Api_GetStock():
    return jsonify({'Mensaje': tasks})



class API:
    def __init__(self):
       pass
    def Run(self):
        app.run(debug=False,threaded=True)