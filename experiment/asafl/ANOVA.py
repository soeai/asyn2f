import scipy.stats as stats
import pandas as pd


df = pd.read_excel('./ANOVA/SVHN-Resnet-box.xlsx', header=0)

Group = [[] for _ in range(6)]

column_names = df.columns.tolist()
data_by_column = {column: df[column].tolist() for column in column_names}

group1 = data_by_column['ASAFL']
print(group1)
group2 = data_by_column['ASAFL1']
print(group2)
group3 = data_by_column['FedAvg']
print(group3)
group4 = data_by_column['FedAsyn']
print(group4)
group5 = data_by_column['SimiAsyn']
print(group5)
group6 = data_by_column['SimiSyn']
print(group6)

f_value, p_value = stats.f_oneway(group1,group2, group3, group4, group5, group6)

print("F-value:", f_value)
print("P-value:", p_value)