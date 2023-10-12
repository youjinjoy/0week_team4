from pymongo import MongoClient
from flask import Flask, render_template, jsonify, request, redirect
from bson.json_util import dumps
from bson import ObjectId
import json
import jwt
from datetime import datetime,timedelta
import hashlib
import urllib.request
import urllib.error
import time
import requests
import cgi

app = Flask(__name__)

client = MongoClient('localhost', 27017)
db = client.dbjungle

SECRET_KEY = 'secret_key'

@app.route('/')
def home():
   return render_template('login.html')

@app.route('/join')
def joinpage():
   return render_template('join.html')


@app.route('/mainpage')
def mainapge():
    token_receive = request.cookies.get('mytoken')
    
    rest_list = list(db.review.find({}, {'_id':False}))

    #받은 토큰을 복호화 한 다음 시간이나 증명에 문제가 있다면 예외처리합니다.
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        return render_template('card.html', rest_list = rest_list, random_rest = json.dumps(rest_list))
    except jwt.ExpiredSignatureError:
        return redirect("http://localhost:5000/")
    except jwt.exceptions.DecodeError:
        return redirect("http://localhost:5000/")

@app.route('/login', methods=['POST'])
def login():
   
    # 아이디 비밀번호를 받는다
    targetId = request.form['targetId']
    targetPwd = request.form['targetPwd']

    pw_hash = hashlib.sha256(targetPwd.encode('utf-8')).hexdigest()

    # DB 안에서 맞는 유저 정보를 찾는다
    targetUser = db.users.find_one({'Id':targetId,'Pwd':pw_hash})
    print(targetUser)
    # 있으면 로그인 성공 없다면 실패처리
    if targetUser == None:
        return jsonify({'result': 'fail'})
    else :
        #payload는 토큰에 담을 정보를 뜻한다.
        payload={
        'id' : targetId,
        'exp' : datetime.utcnow() + timedelta(seconds=60*60*24)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        return jsonify({'result': 'success', 'token': token})

    
@app.route('/join/signup', methods=['POST'])
def signup():
   
    #아이디 비밀번호 이메일을 받는다
    targetId = request.form['targetId']
    targetPwd = request.form['targetPwd']
    targetEmail = request.form['targetEmail']

    #받은 비밀번호를 해쉬화 한다.
    pw_hash = hashlib.sha256(targetPwd.encode('utf-8')).hexdigest()

    #DB 안에 저장한다.
    doc = {
            'Id': targetId,
            'Pwd': pw_hash,
            'Email': targetEmail,
        }
    db.users.insert_one(doc)

    return jsonify({'result': 'success'}) 

@app.route('/join/idcheck', methods=['POST'])
def idcheck():
   
    #아이디를 받는다 
    targetId = request.form['targetId']

    #공백이면 취소처리
    if targetId == "" :
        return jsonify({'result': 'black'})
    #해당 아이디의 컬럼이 있는지 확인한다.
    targetUser = db.users.find_one({'Id':targetId})

    print(targetUser)
    if targetUser == None:
        return jsonify({'result': 'success'})
    else :
        return jsonify({'result': 'fail'})   
##########################################################


#학식 메뉴 관련
# @app.route('/mealmenu', methods=['POST'])
# def menuScraping():



#     return menu
##########################################################


# 메인페이지 전체 리스트 관련
@app.route('/api/list', methods=['GET'])
def show_rests():
    sortMode = request.args.get('sortMode', 'like')

    if sortMode == 'like':
        restslist = list(db.review.find({}).sort('like', -1))
    elif sortMode == 'restaurant':
        restslist = list(db.review.find({}).sort('restaurant', 1))
    else:
        return jsonify({'result': 'failure'})

    return jsonify({'result': 'success', 'rest_list': dumps(restslist)})
##########################################################


# 글 작성 상세보기 관련
##########################################################
# @app.route('/contents')
# def contents():
#     return render_template('index.html')

category={'한식', '중식', '일식', '양식'}

@app.route('/post')
def post():
    cookie_receive = request.cookies.get('myid')
    review2=db.review.find_one({'user_id':cookie_receive})
    return render_template('post.html', category=category, review=review2)

@app.route('/mydetail/<idnum>')
def my_detail(idnum):
    a = int(idnum)
    review2=db.review.find_one({'num':a})
    print(review2)
    return render_template('mydetail.html', review=review2)

@app.route('/mydetail_modifying/<idnum>')
def modifying_detail(idnum):
    a = int(idnum)
    review2=db.review.find_one({'num':a})
    return render_template('mydetail_modifying.html',num=idnum, review=review2, category=category)

@app.route('/otherdetail')
def other_detail():
    review=db.review.find_one({'user_id': 'test'})
    likes=review['like']
    
    return render_template('otherdetail.html',likes=likes, review=review)


# 맛집 리뷰 POST
@app.route('/post/mydetail', methods=['POST'])
def post_my_detail():
    #고유 번호 생성
    idnum = db.review.find_one(sort=[("num", -1)])["num"] + 1

   # 1. 클라이언트로부터 데이터를 받기
    restaurant_receive=request.form['restaurant_give']
    category_receive=request.form['category_give']
    comment_receive=request.form['comment_give']
    location_receive=request.form['location_give']
    user_receive=request.form['user_give']
    file = request.files["file_give"]
    
    # static 폴더에 저장될 파일 이름 생성하기
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    filename = f'file-{mytime}'
    # 확장자 나누기
    extension = file.filename.split('.')[-1]
    # static 폴더에 저장
    save_to = f'static/{filename}.{extension}'
    file.save(save_to)

    # 예외 처리
    if restaurant_receive=="" or comment_receive=="" or category_receive=="선택하기":
       return jsonify({'result':'empty'})

    # 2. document 만들기
    review = {
        'num' : idnum,
        'restaurant': restaurant_receive,
        'category': category_receive,
        'comment': comment_receive,
        'like':0,
        'locate':location_receive,
        'user_id':user_receive,
        'favorite':0 ,
        'image': f'{filename}.{extension}'
    }
    # 3. mongoDB에 데이터 넣기
    db.review.insert_one(review)

    # print(idnum)
    # print(user_receive)

    return jsonify({'result':'success','idnum':idnum})

@app.route('/modify/mydetail',methods=['POST'])
def modify_my_detail():
    # 1. 클라이언트로부터 데이터를 받기 이미지 받기
    num_receive=request.form['num_give']
    restaurant_receive=request.form['restaurant_give']
    category_receive=request.form['category_give']
    comment_receive=request.form['comment_give']
    location_receive=request.form['location_give']
    file2 = request.files["file_give"]
    # 이미지 받기

    # static 폴더에 저장될 파일 이름 생성하기
    today = datetime.now()
    mytime = today.strftime('%Y-%m-%d-%H-%M-%S')
    filename = f'file-{mytime}'
    # 확장자 나누기
    extension = file2.filename.split('.')[-1]
    # static 폴더에 저장
    save_to = f'static/{filename}.{extension}'
    file2.save(save_to)

    # 예외 처리1: 빈칸으로 수정할 때
    if restaurant_receive=="" or comment_receive=="" or category_receive=="선택하기":
       return jsonify({'result':'empty'})

    a = int(num_receive)
    # 예외 처리2: 아무것도 수정하지 않았을 때 
    flag = True # 무엇인가 최소 하나 수정한 상태를 전제로
    changed_or_not = db.review.find_one({'num': a})
    if changed_or_not['restaurant']==restaurant_receive and changed_or_not['comment']==comment_receive and changed_or_not['category']==category_receive and changed_or_not['locate']==location_receive:
       flag = False # 아무것도 수정하지 않았다.

    result = db.review.update_one({'num': a},{'$set': {'restaurant': restaurant_receive, 'category':category_receive, 'comment': comment_receive, 'image': f'{filename}.{extension}', 'locate':location_receive}})
    # DB 아이디 쓰는 경우: '_id': ObjectId(id_receive)
    # 이미지 추가 필요
    print(type(num_receive))
    print(result.modified_count)
    print(flag)
    if result.modified_count == 1 and flag: # 수정한 document가 1개이고, 무엇인가 최소 하나 수정한 상태라면 성공
      return jsonify({'result': 'success','idnum': a})
    else: # 수정한 document가 1이 아니거나, 아무것도 수정되지 않은 경우 실패
      return jsonify({'result': 'failure'})

@app.route('/like',methods=['POST'])
def like_review():
    # id_receive = request.form['id']
    # review = db.review.find_one({'_id': ObjectId(id_receive)})
    print("test")
    review=db.review.find_one({'user_id':'test'})
    new_likes = review['like'] + 1
    result = db.review.update_one({'user_id':'test'}, {'$set': {'like': new_likes}})
    print(review['like'])
    # 4. 하나의 메모만 영향을 받아야 하므로 result.updated_count 가 1이면  result = success 를 보냄
    if result.modified_count == 1:
       return jsonify({'result': 'success'})
    else:
       return jsonify({'result': 'failure'})

@app.route('/favorite',methods=['POST'])
def favorite_review():
    # id_receive = request.form['id']
    review=db.review.find_one({'user_id':'test'})
    print(review)
   
    # 이미 즐겨찾기 되어있을 때
    if review['favorite']==0:
       result = db.review.update_one({'user_id':'test'}, {'$set': {'favorite':1 }})
    elif review['favorite']==1:
       return jsonify({'result':'existed'})

    if result.modified_count == 1:
      return jsonify({'result': 'success'})
    else:
      return jsonify({'result': 'failure'})
    
@app.route('/delete',methods=['POST'])
def delete_review():
    num_receive = request.form['num']
    num_int = int(num_receive)
    # result = db.review.delete_one({'_id': ObjectId(id_receive)})

    result = db.review.delete_one({'num':num_int})
    # 3. 하나의 영화만 영향을 받아야 하므로 result.updated_count 가 1이면  result = success 를 보냄
    if result.deleted_count == 1:
        return jsonify({'result': 'success'})
    else:
        return jsonify({'result': 'failure'})
    
##########################################################

if __name__ == '__main__':  
   app.run('0.0.0.0',port=5000,debug=True)