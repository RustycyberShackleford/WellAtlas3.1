import os, sqlite3
from flask import Flask,render_template
app=Flask(__name__)
DB=os.path.join(os.path.dirname(__file__),'wellatlas_demo.db')
@app.route('/')
def home(): return render_template('index.html')
if __name__=='__main__': app.run()