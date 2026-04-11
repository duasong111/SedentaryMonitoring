from flask_socketio import emit
from Common.Response import create_response
from flask import Flask, request
from functions.user import LoginFunction, RegisterFunction
from database.operateFunction import execuFunction
from flask_cors import CORS
from http import HTTPStatus

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

checkLogin = LoginFunction()
registerFunc = RegisterFunction()
db_function = execuFunction()

@app.route("/api/register/", methods=["POST"], strict_slashes=False)
def register():
    try:
        data = request.get_json()
        user = data.get('username')
        pwd = data.get('password')
        return registerFunc.register(user, pwd)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)

@app.route("/api/login/", methods=["POST"], strict_slashes=False)
def login():
    try:
        data = request.get_json()
        user = data.get('username')
        pwd = data.get('password')
        return checkLogin.checklogin(user, pwd)
    except Exception as e:
        return create_response(HTTPStatus.INTERNAL_SERVER_ERROR, f"服务器错误: {str(e)}", False)




if __name__ == '__main__':

    app.run(host='0.0.0.0', port=5001, debug=False)