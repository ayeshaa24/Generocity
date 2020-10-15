from flask import url_for
import random
# import string
import pandas as pd

def generate_idea():
    # df = pd.read_csv("{{ url_for('static', filename='kind_acts.csv') }}")
    df = pd.read_csv("../../static/kind_acts.csv")
    list = df['Kind Acts'].tolist()
    index = random.randint(0, len(list)-1)
    idea = list[index]
    print("hi")
    return idea

# call function
# print(generate_idea())
