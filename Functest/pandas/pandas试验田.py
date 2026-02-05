import pandas as pd

df = pd.read_excel('', engine="openpyxl")

df.to_excel('人证.xlsx', index=False, engine="openpyxl")

