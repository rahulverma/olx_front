import sqlite3, sys, ast, re
from datetime import datetime
from flask import Flask, render_template, request
app = Flask(__name__)



@app.route('/')
def main_page():
    items = get_all()
    return render_template('index.html', items=items)

@app.route('/phone/<phone>')
def phone_number(phone):
    items = get_phone(phone)
    return render_template('index.html', items=items)

@app.route('/search')
def search():
    key = request.args.get('key', None)
    regex = request.args.get('regex', None)
    items = None
    if key:
        if regex:
            items = get_with_regex(key)
        else:
            items = get_with_keyword(key)
    else:
        items = get_all()

    return render_template('index.html', items=items, key=key)


database_connection = None
database_path = None

def sqlite_re_fn(expr, item):
    reg = re.compile(expr, re.I)
    return reg.search(item) is not None

def get_conn():
    global database_connection, database_path
    if not database_connection:
        database_connection = sqlite3.connect(database_path, check_same_thread=False)
        database_connection.create_function("REGEXP", 2, sqlite_re_fn)
    return database_connection

def close_connection():
    global database_connection
    if database_connection:
        database_connection.close()
        database_connection = None

class R:
    url = 0
    title = 1
    phone = 2
    name = 3
    price = 4
    time = 5
    types = 6
    desc = 7
    image = 8
    chart = 9

def get_phone(phone):
    c = get_conn()
    cur = c.cursor()

    cur.execute("""SELECT i.url, i.title, i.phone, i.name, i.price, i.time, i.types, i.desc, i.image, p.chart from items i
                    LEFT JOIN phonedetails p
                    on i.phone = p.phone
                    WHERE i.phone=?
                    ORDER BY i.time DESC, i.phone """, (phone,))

    while True:
        row = cur.fetchone()
        if not row:
            break

        yield parse(row)

def get_all():
    c = get_conn()
    cur = c.cursor()
    cur.execute("""SELECT i.url, i.title, i.phone, i.name, i.price, i.time, i.types, i.desc, i.image, p.chart from items i
                    LEFT JOIN phonedetails p
                    on i.phone = p.phone
                    ORDER BY i.time DESC, i.phone
                    LIMIT 200""")

    while True:
        row = cur.fetchone()
        if not row:
            break

        yield parse(row)

def get_with_keyword(key):
    c = get_conn()
    cur = c.cursor()
    key = key.split()
    where = "(i.title like ? or i.types like ? or i.desc like ?) AND " * (len(key)-1) + "(i.title like ? or i.types like ? or i.desc like ?)"
    val = tuple(sum([['%'+ x + '%']*3 for x in key], []))

    cur.execute("""SELECT i.url, i.title, i.phone, i.name, i.price, i.time, i.types, i.desc, i.image, p.chart from items i
                    LEFT JOIN phonedetails p
                    on i.phone = p.phone WHERE """ + where + " COLLATE NOCASE ORDER BY i.time DESC, i.phone", val)

    while True:
        row = cur.fetchone()
        if not row:
            break

        yield parse(row)

def get_with_regex(key):
    c = get_conn()
    cur = c.cursor()
    cur.execute("""SELECT i.url, i.title, i.phone, i.name, i.price, i.time, i.types, i.desc, i.image, p.chart from items i
                    LEFT JOIN phonedetails p
                    on i.phone = p.phone WHERE (i.title REGEXP ? or i.types REGEXP ? or i.desc REGEXP ?)
                    ORDER BY i.time DESC, i.phone""", (key, key, key))

    while True:
        row = cur.fetchone()
        if not row:
            break

        yield parse(row)


def parse(row):
    item = {}
    item['url'] = row[R.url]
    item['title'] = row[R.title]
    item['phone'] = row[R.phone]
    item['name'] = row[R.name]
    item['price'] = row[R.price]
    item['time'] = datetime.fromtimestamp(int(row[R.time])).date().strftime("%a, %d %b")
    item['types'] = row[R.types]
    item['desc'] = row[R.desc]
    if row[R.image]:
        item['image'] = generate_image_data(row[R.image])
    else:
        item['image'] = []

    item['chart'], item['max'] = generate_chart(row[R.chart])

    return item

def generate_image_data(image):
    links = image.strip().split(',')
    if not links:
        return []
    if len(links) == 1:
        return {'lnk': links[0]}
    result = []
    length = len(links)
    for idx, img in enumerate(links):
        data = {}
        left = idx
        if left == 0:
            left = length
        right = idx + 2
        if right == (length + 1):
            right = 1
        data['lnk'] = img
        data['left'] = left
        data['right'] = right
        result.append(data)
    return result




def generate_chart(data):
    if not data:
        return ([],0)
    d = ast.literal_eval(data)
    chart = [0] * 30
    m = max([x[1] for x in d])
    percentage = [(x[0], x[1]*100/m) for x in d]
    for position,length in percentage:
        if position < 30:
            chart[position]=length
    return (chart, m)


def main():
    if len(sys.argv) == 1:
        print("olx database path is needed.")
        exit(-1)

    global database_path
    database_path = sys.argv[1]

    app.run(host='0.0.0.0')

if __name__ == "__main__":
    main()
