import time
from error import Error
from flask import Flask, Response, request, jsonify
from mongoengine.queryset import DoesNotExist
from functools import wraps
from models import db, Attendee

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)

def str2timestamp(str):
        return datetime.strptime(str, "%Y/%m/%d %H:%M").timestamp()

def returns_json(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        r = f(*args, **kwargs)
        return Response(r, content_type='application/json; charset=utf-8')
    return decorated_function

def get_attendee(request):
    token = request.args.get('token')

    if token is None:
        raise Error("token require")

    try:
        attendee = Attendee.objects(token=token).get()
    except DoesNotExist:
        raise Error("invalid token")

    return attendee


@app.errorhandler(Error)
def handle_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/status')
@returns_json
def status():
    return get_attendee(request).to_json()


@app.route('/use/<scenario_id>')
@returns_json
def use(scenario_id):
    attendee = get_attendee(request)

    try:
        scenario = attendee.scenario[scenario_id]
    except KeyError:
        raise Error("invalid scenario_id")

    if scenario.available_time <= time.time() and scenario.expire_time > time.time():
        if scenario.used is not None:
            raise Error("has been used")

        if scenario.disabled is not None:
            raise Error("disabled scenario")

        if scenario_id in ("day1checkin", "day2checkin"):
            if time.time() > scenario.available_time + 5400:
                attendee.scenario[{'day1checkin': 'day1lunch', 'day2checkin': 'day2lunch'}.get(scenario_id)].disabled = "too late"

        scenario.used = time.time()
        attendee.save()

        return attendee.to_json()
    else:
        raise Error("link expired/not available now")

@app.route('/dashboard')
def dashboard():
    res = {}
    res['total'] = Attendee.objects().count()
    res['day1checkin_used'] = Attendee.objects(scenario__day1checkin__used__ne=None).count()
    res['kit_used'] = Attendee.objects(scenario__kit__used__ne=None).count()
    res['day1lunch_used'] = Attendee.objects(scenario__day1lunch__used__ne=None).count()
    res['day2checkin_used'] = Attendee.objects(scenario__day2checkin__used__ne=None).count()
    res['day2lunch_used'] = Attendee.objects(scenario__day2lunch__used__ne=None).count()

    return jsonify(res)
