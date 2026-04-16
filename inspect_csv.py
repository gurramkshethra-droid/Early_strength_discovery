import os
import pandas as pd

path = "students.csv"
print("exists", os.path.exists(path))
df = pd.read_csv(path)
print("shape", df.shape)
print("nulls", df.isnull().sum().to_dict())
print(df.head().to_string())
print("---")
print(df.tail(10).to_string())
